# Changelog

All notable changes to Proxecto Karaoke en Galego are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html): one version for the engine, the server
and the web app. How a release is made: [`docs/releasing.md`](docs/releasing.md).

## [Unreleased]

### Added

- **Descargar** in the player: the song's karaoke videos, made right there with their progress
  live and kept to download (or delete) any time, plus the music without vocals, the vocals, the
  synced lyrics and the offline copy. A video made before a correction of the lyrics says so.
- The guide vocals in a video can be set from none (a karaoke) to the song as sung; each level
  is a video of its own («… (karaoke, voz 30%).mp4»).
- Downloads are named after the song («Artist - Title (karaoke).mp4», «… (sen voz).m4a»).
- `GET /api/songs/{id}/exports`, `DELETE /api/songs/{id}/exports/{name}` and
  `GET /media/{id}/{file}?download=1&name=…`.
- Lyrics can be pasted exactly as they come from any lyrics site or video description: what the
  page adds is left out before aligning — Genius's song recommendations and ticket adverts, its
  title, contributors and «Embed», credits, copyright, links and hashtags, subtitle and LRC
  timings, stage directions like «(risas)» and the song's title above the lyrics. Labels
  without brackets («CORO:», «(Estribillo x2)», «Repetir estribillo») and who sings in a duet
  («Ela: …») are understood like `[Estribillo]` headers.

### Changed

- Better MP4 exports: songs keep their video as it came (`master.mp4`, up to 1080p, contract
  1.2.0) and the export draws on it instead of the player's 720p copy (36.9 → 43.3 dB XPSNR on a
  1080p clip, about the same time). Links now download at up to 1080p. Songs made before keep
  exporting as they did; making them again from their link adds the original.
- The «Son» panel keeps only the sound settings and the lyrics style.

### Fixed

- The download button of a finished video never showed on the create page with the real server:
  video jobs now carry their song from the start.
- Asking again for a video that was still waiting or being made queued another copy of it; it
  now gives the same job. A video waiting for the graphics card says so instead of «0 %».
- Several players following their jobs at once could get errors (500): request checks ran in
  worker threads and shared the database connection; they now run on the server's event loop.

## [3.0.0] - 2026-11-06

A rebuild from scratch, under a new name: Proxecto Karaoke en Galego. The goal stays the same — a
karaoke of any song, made for Galician first and working in any language, with lyrics that light up
exactly as they are sung — but every piece is new and every model was chosen with a benchmark.

### Added

- **Engine** (`karaoke make`): one command turns a song (file or link) into a karaoke package,
  with pasted lyrics, lyrics found on LRCLIB or none at all.
  - Vocal separation with Mel-Band RoFormer, loudness normalised to −14 LUFS.
  - Transcription with Whisper (HiTZ large-v3 for Galician, large-v3-turbo for other languages),
    voice activity detection and guards against hallucinated loops.
  - A new forced aligner with a CTC model per language (Proxecto Nós for Galician, Omnilingual
    as the fallback for some 1600 languages): word, syllable and character timings with a
    confidence per word.
  - Galician first: the language is always the one chosen, never switched silently; lyrics are
    normalised only to align (tags, repeats, numbers, apostrophes, reintegrationist spelling)
    and always shown as written; enclitic pronouns written apart are joined to their verb.
  - Backing vocals as their own lines and a colour per singer.
- **Lyrics on screen**: one layout engine in Python and TypeScript with shared test cases, pages
  and scrolling modes, a countdown after instrumental breaks and three themes with open fonts.
- **Video export** (`karaoke render`): 16:9 and 9:16 MP4 with the song's video, cover or a
  gradient behind the lyrics, title and credits, encoded with NVENC when available (a 4-minute
  song in under a minute on an RTX 3050).
- **Web app** for phone, laptop and TV: a poster library, a full-screen player (guide vocals,
  pitch, latency calibration, background video), creating a karaoke with live progress, a party
  mode where phones queue songs and act as remotes through a QR code, a lyrics and timing
  editor, offline songs and an installable app, in Galician, Spanish and English.
- **Home server** (`karaoke-server`): FastAPI with a typed OpenAPI, a job queue for one GPU with
  each job in its own process, streamed uploads, links through an always-current yt-dlp, live
  progress and time left, cancel and retry, device pairing, home and remote zones, backups,
  `doctor` and start with Windows.
- **Benchmark** (`karaoke-bench`): JamendoLyrics MultiLang (79 songs in four languages) and five
  freely licensed Galician songs, with word timing, WER, speed and memory per step and
  comparable reports in `bench/results/`.
- **Project**: one-command install (`make install`), contracts with JSON Schema and generated
  TypeScript types, a CI that runs the whole test suite with ffmpeg and a browser, licence
  checks for every dependency, `NOTICE.md`, release notes from this file and a security policy.

### Changed

- Python 3.12 with uv, SvelteKit instead of Flask templates, FastAPI instead of Flask, SQLite
  instead of Postgres, a single process instead of Celery and Redis.
- Lyrics are synchronised once in `karaoke.json` and drawn in two places (the web player and the
  MP4), instead of being burnt frame by frame into a video.

### Removed

- Demucs, the WhisperX service, MoviePy, PIL and ImageMagick rendering, Docker Compose, Celery,
  Redis, Postgres, Cloudflare R2, Fly.io, Sentry and email magic links. The previous system is
  kept at the `v2-final` tag.

### Measured

- With lyrics, JamendoLyrics MultiLang (79 songs): 98.8 % of words start within 0.3 s of the
  reference (mean error 0.093 s); Galician set: 99.8 %.
- Without lyrics: 23.2 % word error rate on JamendoLyrics (33.7 % for a Demucs + Whisper
  large-v3-turbo baseline) and 26.5 % on the Galician songs with published lyrics (35.9 %).
- No silent language switch in the whole benchmark.
- A 4:47 song with lyrics is ready in about 85 s on an RTX 3050 Laptop with 4 GB.

## [2.0.0] - 2026-06-03

The second system, kept at the `v2-final` tag: Flask web app with a Galician, Spanish and
English interface, Celery workers for Demucs and WhisperX, Postgres with Alembic, storage on
Cloudflare R2, email sign-in and a deployment to Fly.io that was never put live.

## [1.1.0] - 2026-05-29

Security fixes before making the repository public.

## [1.0.0] - 2025-10-31

The bachelor's thesis (TFG) at the Universidade da Coruña: Docker microservices with Demucs,
WhisperX and MoviePy, and a Flask web app. The thesis is in [`docs/tfg/`](docs/tfg/).

[Unreleased]: https://github.com/gaelfernandez1/KaraokeProject/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/gaelfernandez1/KaraokeProject/compare/v2-final...v3.0.0
[2.0.0]: https://github.com/gaelfernandez1/KaraokeProject/compare/v1.1-pre-restructure...v2-final
[1.1.0]: https://github.com/gaelfernandez1/KaraokeProject/compare/v1.0-tfg...v1.1-pre-restructure
[1.0.0]: https://github.com/gaelfernandez1/KaraokeProject/releases/tag/v1.0-tfg
