from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from karaoke.domain.errors import (
    AlignmentError,
    AudioSeparationError,
    PreparationError,
    RenderError,
)
from karaoke.domain.progress import NoopProgressReporter, ProgressReporter
from karaoke.domain.srt_processing import parse_word_srt
from karaoke.domain.strategies import AlignmentStrategy
from karaoke.infra.db import session_scope
from karaoke.infra.db.repository import save_song
from karaoke.infra.utils import sanitize_filename

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobConfig:
    video_path: Path
    task_id: str
    source_type: str = "upload"
    source_url: str | None = None
    enable_diarization: bool = False
    hf_token: str | None = None
    whisper_model: str = "small"
    save_to_db: bool = True
    output_dir: Path = field(default_factory=lambda: Path("./output"))
    work_dir: Path = field(default_factory=lambda: Path("/data"))


@dataclass
class JobArtifacts:
    original_video_path: Path | None = None
    video_path: Path | None = None
    audio_path: Path | None = None
    vocal_path: Path | None = None
    instrumental_path: Path | None = None
    srt_path: Path | None = None
    text_groups: list | None = None
    karaoke_filename: str | None = None


class KaraokeJob:
    def __init__(
        self,
        config: JobConfig,
        strategy: AlignmentStrategy,
        reporter: ProgressReporter | None = None,
    ) -> None:
        self.config = config
        self.strategy = strategy
        self.reporter = reporter or NoopProgressReporter()
        self.artifacts = JobArtifacts()
        self._job_work_dir = config.work_dir / config.task_id

    def run(self) -> str:
        self._job_work_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._prepare()
            self._separate()
            self._align()
            self._render()
            self._persist()
        finally:
            shutil.rmtree(self._job_work_dir, ignore_errors=True)
        assert self.artifacts.karaoke_filename is not None
        return self.artifacts.karaoke_filename

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    def _prepare(self) -> None:
        from karaoke.infra.audio_processing import video_to_mp3  # noqa: PLC0415
        from karaoke.infra.video_processing import normalize_video  # noqa: PLC0415

        self.reporter.report("Normalizando vídeo...", 10)
        self.artifacts.original_video_path = self.config.video_path
        video_path = self.config.video_path
        try:
            normalized = normalize_video(str(video_path))
            video_path = Path(normalized)
        except Exception as e:
            logger.warning(f"Video normalization failed, continuing with original: {e}")
        self.artifacts.video_path = video_path

        self.reporter.report("Extraendo audio...", 15)
        audio_path = video_to_mp3(str(video_path))
        if not audio_path:
            raise PreparationError(f"Failed to extract audio from {video_path}")
        self.artifacts.audio_path = Path(audio_path)

    def _separate(self) -> None:
        from karaoke.infra.audio_processing import separate_stems_cli  # noqa: PLC0415

        self.reporter.report("Separando voces e instrumental...", 25)
        vocal_str, instrumental_str = separate_stems_cli(str(self.artifacts.audio_path))
        if not vocal_str or not instrumental_str:
            raise AudioSeparationError("Demucs failed to separate stems")

        # Move stems into the per-job work directory for isolation
        vocal_dest = self._job_work_dir / "vocals.wav"
        instrumental_dest = self._job_work_dir / "instrumental.wav"
        shutil.move(vocal_str, vocal_dest)
        shutil.move(instrumental_str, instrumental_dest)

        self.artifacts.vocal_path = vocal_dest
        self.artifacts.instrumental_path = instrumental_dest

    def _align(self) -> None:
        self.reporter.check_cancelled()
        self.reporter.report("Sincronizando letra con audio...", 45)

        srt_content = self.strategy.align(
            self.artifacts.vocal_path,  # type: ignore[arg-type]
            self._job_work_dir,
            self.config,
        )
        if not srt_content.strip():
            raise AlignmentError("WhisperX returned empty SRT content")

        srt_path = self._job_work_dir / f"vocals_whisperx_{self.config.whisper_model}.srt"
        srt_path.write_text(srt_content, encoding="utf-8")
        self.artifacts.srt_path = srt_path

        self.reporter.report("Procesando subtítulos...", 60)
        segments = parse_word_srt(str(srt_path))
        groups = self.strategy.group_segments(segments)
        if not groups:
            raise AlignmentError("Word grouping produced no output")
        self.artifacts.text_groups = groups
        logger.debug(f"Created {len(groups)} phrase groups")

    def _render(self) -> None:
        from moviepy.editor import (  # noqa: PLC0415
            AudioFileClip,
            CompositeAudioClip,
            CompositeVideoClip,
            VideoFileClip,
        )

        from karaoke.domain.karaoke_rendering import create_karaoke_text_clip  # noqa: PLC0415
        from karaoke.domain.render_config import (  # noqa: PLC0415
            ALTO_VIDEO,
            MARXE_INFERIOR_SUBTITULO,
            VOLUME_VOCAL,
        )

        self.reporter.report("Creando vídeo final...", 75)
        assert self.artifacts.vocal_path is not None
        assert self.artifacts.instrumental_path is not None
        assert self.artifacts.video_path is not None
        assert self.artifacts.original_video_path is not None
        assert self.artifacts.text_groups is not None

        try:
            audio_music = AudioFileClip(str(self.artifacts.instrumental_path)).set_fps(44100)
            audio_vocals = (
                AudioFileClip(str(self.artifacts.vocal_path)).volumex(VOLUME_VOCAL).set_fps(44100)
            )
            audio_mixed = CompositeAudioClip([audio_music, audio_vocals])
        except Exception as e:
            raise RenderError(f"Failed to load audio: {e}") from e

        try:
            video_bg = (
                VideoFileClip(str(self.artifacts.video_path))
                .set_duration(audio_mixed.duration)
                .set_fps(30)
            )
        except Exception as e:
            # Manual lyrics mode: fall back to original (non-normalized) video
            if (
                self.strategy.is_manual_lyrics
                and self.artifacts.video_path != self.artifacts.original_video_path
            ):
                try:
                    video_bg = (
                        VideoFileClip(str(self.artifacts.original_video_path))
                        .set_duration(audio_mixed.duration)
                        .set_fps(30)
                    )
                    logger.warning("Normalized video failed to load; using original")
                except Exception as e2:
                    raise RenderError(f"Both normalized and original video failed: {e2}") from e2
            else:
                raise RenderError(f"Failed to load video: {e}") from e

        video_darkened = video_bg.fl_image(lambda img: (img * 0.3).astype("uint8"))

        clips = []
        for idx, group in enumerate(self.artifacts.text_groups):
            start = max(group["start"] - 0.5, 0)
            duration = group["end"] - group["start"] + 1.0
            next_line = (
                self.artifacts.text_groups[idx + 1]
                if idx + 1 < len(self.artifacts.text_groups)
                else None
            )
            clip = create_karaoke_text_clip(
                group, next_line_info=next_line, advance=0.5, duration_padding=0.5
            )
            clip = clip.set_start(start).set_duration(duration)
            clip = clip.set_position(("center", ALTO_VIDEO - MARXE_INFERIOR_SUBTITULO))
            clips.append(clip)

        video_final = CompositeVideoClip([video_darkened] + clips).set_audio(audio_mixed)

        # Output filename (preserving original naming conventions exactly)
        if self.strategy.is_manual_lyrics:
            base = os.path.basename(str(self.artifacts.video_path))
        else:
            base = os.path.basename(str(self.artifacts.video_path)).replace("_normalized", "")
        safe_name = sanitize_filename(base)
        prefix = "karaoke_manual" if self.strategy.is_manual_lyrics else "karaoke"
        output_filename = f"{prefix}_{self.config.whisper_model}_{safe_name}"

        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.config.output_dir / output_filename

        self.reporter.report("Renderizando vídeo final...", 90)
        try:
            video_final.write_videofile(str(output_path), fps=30, threads=4)
        except Exception as e:
            raise RenderError(f"write_videofile failed: {e}") from e

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RenderError(f"Output file missing or empty: {output_path}")

        logger.info(f"Video generated: {output_path}")

        # Secondary outputs (non-fatal if they fail)
        self._write_secondary_outputs(video_darkened, output_path, output_filename, safe_name)

        self.artifacts.karaoke_filename = output_filename

    def _write_secondary_outputs(
        self,
        video_darkened: object,
        output_path: Path,
        output_filename: str,
        safe_name: str,
    ) -> None:
        try:
            video_only_path = output_path.with_name(
                output_filename.replace(".mp4", "_video_only.mp4")
            )
            video_darkened.write_videofile(str(video_only_path), fps=30, threads=4, audio=False)  # type: ignore[union-attr]
        except Exception as e:
            logger.warning(f"Failed to write video-only file: {e}")

        name_no_ext = safe_name.replace(".mp4", "")
        try:
            shutil.copy2(
                str(self.artifacts.vocal_path),
                str(
                    self.config.output_dir / f"vocal_{self.config.whisper_model}_{name_no_ext}.wav"
                ),
            )
            shutil.copy2(
                str(self.artifacts.instrumental_path),
                str(
                    self.config.output_dir
                    / f"instrumental_{self.config.whisper_model}_{name_no_ext}.wav"
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to copy separated stems to output: {e}")

    def _persist(self) -> None:
        from karaoke.infra.metadata_utils import generate_song_metadata  # noqa: PLC0415

        if not self.config.save_to_db:
            return
        assert self.artifacts.karaoke_filename is not None
        assert self.artifacts.video_path is not None
        try:
            processing_type = "manual_lyrics" if self.strategy.is_manual_lyrics else "automatic"
            manual_lyrics = (
                getattr(self.strategy, "normalized_lyrics", None)
                if self.strategy.is_manual_lyrics
                else None
            )
            language = (
                getattr(self.strategy, "language", None) if self.strategy.is_manual_lyrics else None
            )
            metadata = generate_song_metadata(
                original_filename=os.path.basename(str(self.artifacts.video_path)),
                karaoke_filename=self.artifacts.karaoke_filename,
                source_type=self.config.source_type,
                source_url=self.config.source_url,
                processing_type=processing_type,
                manual_lyrics=manual_lyrics,
                language=language,
                enable_diarization=self.config.enable_diarization,
                whisper_model=self.config.whisper_model,
                output_dir=str(self.config.output_dir),
            )
            with session_scope() as session:
                song_id = save_song(session, metadata)
            logger.info(f"Song saved to database with ID: {song_id}")
        except Exception as e:
            logger.error(f"Failed to save to database (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Instrumental-only pipeline
# ---------------------------------------------------------------------------


class InstrumentalJob:
    def __init__(
        self,
        config: JobConfig,
        reporter: ProgressReporter | None = None,
    ) -> None:
        self.config = config
        self.reporter = reporter or NoopProgressReporter()
        self.artifacts = JobArtifacts()
        self._job_work_dir = config.work_dir / config.task_id

    def run(self) -> str:
        self._job_work_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._prepare()
            self._separate()
            self._persist()
        finally:
            shutil.rmtree(self._job_work_dir, ignore_errors=True)
        assert self.artifacts.karaoke_filename is not None
        return self.artifacts.karaoke_filename

    def _prepare(self) -> None:
        from karaoke.infra.audio_processing import video_to_mp3  # noqa: PLC0415
        from karaoke.infra.video_processing import normalize_video  # noqa: PLC0415

        self.artifacts.original_video_path = self.config.video_path
        video_path = self.config.video_path

        # Only normalize if it's a video, not audio-only
        if not str(video_path).lower().endswith(".mp3"):
            self.reporter.report("Normalizando vídeo...", 15)
            try:
                normalized = normalize_video(str(video_path))
                video_path = Path(normalized)
            except Exception as e:
                logger.warning(f"Video normalization failed, continuing with original: {e}")
        self.artifacts.video_path = video_path

        self.reporter.report("Extraendo audio...", 25)
        audio_path = video_to_mp3(str(video_path))
        if not audio_path:
            raise PreparationError(f"Failed to extract audio from {video_path}")
        self.artifacts.audio_path = Path(audio_path)

    def _separate(self) -> None:
        from karaoke.infra.audio_processing import separate_stems_cli  # noqa: PLC0415

        self.reporter.report("Separando instrumental...", 50)
        vocal_str, instrumental_str = separate_stems_cli(str(self.artifacts.audio_path))
        if not instrumental_str:
            raise AudioSeparationError("Demucs failed to produce instrumental track")

        instrumental_dest = self._job_work_dir / "instrumental.wav"
        shutil.move(instrumental_str, instrumental_dest)
        if vocal_str:
            vocal_dest = self._job_work_dir / "vocals.wav"
            shutil.move(vocal_str, vocal_dest)

        self.artifacts.instrumental_path = instrumental_dest

    def _persist(self) -> None:
        assert self.artifacts.instrumental_path is not None
        assert self.artifacts.video_path is not None

        self.reporter.report("Copiando arquivo final...", 85)

        base = os.path.basename(str(self.artifacts.video_path)).replace("_normalized", "")
        safe_name = sanitize_filename(base)

        if safe_name.lower().endswith(".mp4"):
            output_filename = f"instrumental_{safe_name.replace('.mp4', '.wav')}"
        elif safe_name.lower().endswith(".mp3"):
            output_filename = f"instrumental_{safe_name.replace('.mp3', '.wav')}"
        else:
            output_filename = f"instrumental_{safe_name}.wav"

        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.config.output_dir / output_filename

        try:
            shutil.copy2(str(self.artifacts.instrumental_path), str(output_path))
        except Exception as e:
            raise RenderError(f"Failed to copy instrumental to output: {e}") from e

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RenderError(f"Instrumental output missing or empty: {output_path}")

        logger.info(f"Instrumental generated: {output_path}")
        self.artifacts.karaoke_filename = output_filename

        if self.config.save_to_db:
            self._save_to_db(output_path, output_filename)

    def _save_to_db(self, output_path: Path, output_filename: str) -> None:
        assert self.artifacts.video_path is not None
        try:
            original_name = os.path.basename(str(self.artifacts.video_path))
            title = original_name.replace("_normalized", "")
            for ext in (".mp4", ".mp3"):
                if title.lower().endswith(ext):
                    title = title[: -len(ext)]
                    break
            title = f"[Instrumental] {title}"

            file_size = output_path.stat().st_size
            duration: float | None = None
            try:
                from moviepy.editor import AudioFileClip  # noqa: PLC0415

                clip = AudioFileClip(str(output_path))
                duration = clip.duration
                clip.close()
            except Exception:
                pass

            song_data = {
                "title": title,
                "original_filename": original_name,
                "karaoke_filename": output_filename,
                "video_only_filename": None,
                "vocal_filename": None,
                "instrumental_filename": output_filename,
                "source_type": self.config.source_type,
                "source_url": self.config.source_url,
                "processing_type": "instrumental",
                "manual_lyrics": None,
                "language": None,
                "enable_diarization": False,
                "file_size": file_size,
                "duration": duration,
            }
            with session_scope() as session:
                save_song(session, song_data)
        except Exception as e:
            logger.error(f"Failed to save instrumental to database (non-fatal): {e}")
