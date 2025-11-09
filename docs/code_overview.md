# KaraokeProject Code Overview

KaraokeProject generates multilingual karaoke videos by combining web-driven orchestration, Celery workers, GPU-aware media pipelines, and AI-backed transcription services. This document describes how the Python codebase fits together so you can extend, debug, or operate the system confidently.

---

## Architecture at a Glance

- **Web UI & API (`app.py`)** – A Flask application exposes upload forms, progress pages, and download endpoints. It stores task state in the user session and delegates heavy lifting to Celery tasks.
- **Asynchronous processing (`celery_app.py`, `celery_tasks.py`)** – Celery workers run inside Docker containers, picking jobs from Redis. They stream progress updates back to Flask and support cancellation/cleanup semantics.
- **Media & AI toolchain** – `karaoke_generator.py` coordinates Demucs stem separation, faster-whisper transcription, WhisperX alignment, MoviePy rendering, and optional pyannote speaker diarization. Supporting modules in `audio_processing.py`, `video_processing.py`, and `karaoke_rendering.py` encapsulate the low-level work.
- **Persistence (`database.py`, `metadata_utils.py`)** – A SQLite database tracks processed songs, derived assets, and metadata such as durations, file sizes, and diarization flags.
- **Utility services** – GPU detection (`gpu_utils.py`), filename sanitisation (`utils.py`, `security_config.py`), and a standalone WhisperX Flask microservice (`whisperx_service_api.py`) round out the platform.

The default Docker Compose stack launches four containers: Flask, Celery worker, Demucs/processing runtime, and a WhisperX alignment service (plus Redis). Local folders such as `input/`, `output/`, `db/`, and `/data` (inside containers) hold transient and final artefacts.

---

## Request Flow

### Automatic karaoke (default form)
1. **Flask intake** – `/generate` accepts an uploaded MP4 or a YouTube URL (downloaded via `yt_dlp`) and queues `process_automatic_karaoke`.
2. **Celery task** – `celery_tasks.process_automatic_karaoke` wraps `karaoke_generator.create`, relaying progress states ("Normalizando vídeo…", etc.) and checking for cancellation.
3. **Pipeline execution (`create`)**
   - Normalize the video with `video_processing.normalize_video` so captions align across sources.
   - Extract audio (`audio_processing.video_to_mp3`) and split vocals/instrumental with Demucs (`separate_stems_cli`), using GPU hints from `gpu_utils`.
   - Transcribe vocals with `transcribe_with_faster_whisper` and perform forced alignment against the normalized lyrics through the WhisperX HTTP service (`call_whisperx_endpoint_manual`).
   - Parse SRT word timings (`srt_processing.parse_word_srt`), group phrases for display (`group_word_segments_automatic`), and render animated captions (`karaoke_rendering.create_karaoke_text_clip`).
   - Composite the darkened video background with highlighted audio mix, emit MP4 and companion assets, then persist metadata via `database.save_song_to_database`.
4. **Delivery** – Once Celery marks success, Flask redirects users to `/player/<filename>` for playback or `/download/<filename>` for direct download.

### Manual lyrics workflow
- `/process_manual_lyrics` feeds uploaded lyrics into `create_with_manual_lyrics`, which reuses most of the pipeline but aligns against user-supplied text (`text_processing.normalize_manual_lyrics`, `srt_processing.group_word_segments`).

### Instrumental extraction
- `/generate_instrumental` triggers `generate_instrumental`, which normalizes (if MP4), extracts audio, runs Demucs, and saves a WAV instrumental. Metadata is stored with `processing_type='instrumental'`.

---

## Module Reference

### Web & security layer
- **`app.py`** – Flask routes for landing pages, progress polling (`/api/task_status/<id>`), download/stream endpoints, and the media library UI. It initializes hardware logs (`gpu_utils.print_system_summary`), the SQLite DB, and Celery sessions.
- **`security_config.py`** – Centralizes rate limiting with `flask-limiter`, applies security headers, and supplies file-size/filename helpers for uploads.
- **`main.py`** – CLI shortcut that wraps `karaoke_generator.create` for single-file processing outside the web context.

### Task orchestration
- **`celery_app.py`** – Instantiates the Celery application with Redis broker/back-end, registers lifecycle hooks to trace task status, and handles forced termination when users cancel jobs.
- **`celery_tasks.py`** – Defines Celery task entry points for automatic, manual, and instrumental pipelines. Each task updates progress percentages, checks cancellation via Redis, and cleans partial files when aborted.

### Core processing (`karaoke_generator.py`)
Three public functions share the heavy lifting:
- `create(...)` – Automatic mode driven by AI transcription.
- `create_with_manual_lyrics(...)` – Forced alignment against user-supplied lyrics.
- `generate_instrumental(...)` – Exports instrumental-only audio.

Pipeline features:
- **Video normalization** (`video_processing.normalize_video`) picks ffmpeg strategies for troublesome codecs (AV1, HEVC) and falls back to MoviePy when needed.
- **Audio preparation** (`audio_processing.video_to_mp3`, `separate_stems_cli`) writes temp files to `/data` so both Flask and WhisperX containers can access them.
- **Transcription & alignment** – Faster-Whisper provides raw text while WhisperX supplies word-level timing; manual mode skips transcription and aligns directly.
- **Caption rendering** – `karaoke_rendering.create_karaoke_text_clip` builds per-line MoviePy clips with syllable-level highlighting, speaker coloring (if diarization), and optional preview of the next line.
- **Export** – Final MP4, vocal/instrumental WAVs, and a muted video-only MP4 land in `output/`. Metadata is generated with `metadata_utils.generate_song_metadata` and written to SQLite.

### Media helpers
- **`audio_processing.py`** – wraps Demucs CLI execution with GPU-sensitive arguments (`gpu_utils.get_optimal_demucs_args`) and WhisperX API calls for alignment. Includes a CPU fallback path.
- **`video_processing.py`** – Normalizes dimensions/FPS via ffmpeg strategies, patching Pillow compatibility and providing codec/dimension probes.
- **`karaoke_rendering.py`** – Uses Pillow + MoviePy to render text overlays, syllable highlighting, next-line previews, and speaker coloration.
- **`config.py`** – Centralizes rendering constants (colors, fonts, dimensions) and configures ImageMagick for MoviePy text support.

### Subtitle & text handling
- **`srt_processing.py`** – Parses WhisperX-generated word-level SRTs, cleans anomalous timings, and groups segments either by manual lyric lines or automatic phrase heuristics.
- **`text_processing.py`** – Normalizes user-provided lyrics and exposes a Pyphen dictionary for syllabification.

### AI microservice & diarization
- **`whisperx_service_api.py`** – Flask microservice running inside Docker that offers `/align`. It loads WhisperX models, executes optional speaker diarization via `speaker_diarization.py`, and writes word-level SRT files accessible to the main container.
- **`speaker_diarization.py`** – Wraps pyannote pipelines, assigns speakers to word segments based on overlap, and maps speakers to color palettes for UI rendering.
- **`gpu_utils.py`** – Detects CUDA availability, GPU memory, and derives Demucs parameters; also prints system summaries at startup.

### Persistence & metadata
- **`database.py`** – SQLite schema management, CRUD helpers for the media library, and statistics for the `/library` page.
- **`metadata_utils.py`** – Title extraction, YouTube URL cleaning, duration/size computations, and shared formatting helpers.

### Utilities
- **`utils.py`** – Time conversions, filename sanitization, SRT cleanup, and other file housekeeping.
- **Static assets** – Templates in `templates/` and JS/CSS under `static/` drive the web front end (progress polling, player UI, etc.). These are outside Python scope but interact with Flask routes.

---

## Data & Storage Layout

| Path | Purpose |
| --- | --- |
| `input/` | Uploaded videos or downloaded YouTube MP4s awaiting processing. |
| `output/` | Final karaoke MP4s, muted video-only MP4s, vocal/instrumental WAVs. |
| `/data/` (container volume) | Shared scratch space for WhisperX audio/SRT artifacts. |
| `separated/` | Demucs outputs prior to being moved into `/data`. |
| `db/karaoke_songs.db` | SQLite database storing the media library. |

Temporary files are aggressively cleaned when tasks restart or users cancel jobs (`utils.remove_previous_srt`, `celery_tasks.cleanup_partial_files`).

---

## Configuration & Environment

- **Celery & Redis** – `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, and `REDIS_URL` environment variables default to the Docker Compose service names.
- **Flask** – `FLASK_SECRET_KEY` overrides the default session secret in `security_config.setup_security`.
- **Speaker diarization** – Requires a Hugging Face token accepted for `pyannote/speaker-diarization-3.1` and `pyannote/segmentation-3.0`.
- **ImageMagick** – Auto-detected in `config.configurar_imagemagick()` for text rendering support.
- **GPU/CPU selection** – `gpu_utils.detect_gpu_capability()` influences Demucs CLI parameters and logs GPU availability at app startup.

---

## Operational Tips

- **Start-up** – `docker-compose up -d` boots Flask (`app.py`), Celery worker, WhisperX service, Demucs runtime, and Redis. `main.py` offers a CLI alternative outside Docker for quick tests.
- **Progress monitoring** – The front-end polls `/api/task_status/<task_id>` to render progress bars based on `current/total` meta updates from Celery tasks.
- **Cancelling jobs** – `/api/cancel_task/<task_id>` revokes the Celery task, terminating spawned subprocesses (ffmpeg, Demucs) via `psutil`.
- **Extending the pipeline** – Add stages inside `karaoke_generator` and surface progress by calling the provided `progress_callback(step_label, percent)` function in new sections.
- **Testing ideas** – The code relies heavily on external binaries (ffmpeg, demucs, whisperx). For unit tests, mock subprocess calls and HTTP requests (`requests.post`) to avoid heavyweight dependencies.

---

## What to Explore Next

- Review `openapi.yml` for the documented HTTP interface that complements Flask templates.
- Inspect `static/js/player.js` and `static/js/custom.js` to understand how the UI consumes the progress and result endpoints.
- Check `requirementsA.txt` / `requirementsB.txt` for environment-specific dependencies when adding new libraries.

With this map of the Python modules and workflows, you can more easily trace bugs, add new features (e.g., alternate render styles or analytics), and operate the KaraokeProject stack in production.
