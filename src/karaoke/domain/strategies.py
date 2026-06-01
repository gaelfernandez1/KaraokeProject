from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from karaoke.domain.errors import AlignmentError
from karaoke.domain.srt_processing import group_word_segments, group_word_segments_automatic
from karaoke.domain.text_processing import normalize_manual_lyrics

if TYPE_CHECKING:
    from karaoke.domain.pipeline import JobConfig

logger = logging.getLogger(__name__)


@runtime_checkable
class AlignmentStrategy(Protocol):
    is_manual_lyrics: bool

    def align(self, vocal_path: Path, work_dir: Path, config: JobConfig) -> str: ...
    def group_segments(self, segments: list) -> list: ...


class AutomaticAlignment:
    is_manual_lyrics: bool = False

    def align(self, vocal_path: Path, work_dir: Path, config: JobConfig) -> str:
        from karaoke.infra.audio_processing import transcribe_with_faster_whisper  # noqa: PLC0415
        from karaoke.infra.whisperx_client import call_whisperx_endpoint_manual  # noqa: PLC0415

        transcribed = transcribe_with_faster_whisper(str(vocal_path), config.whisper_model)
        if not transcribed:
            raise AlignmentError("faster-whisper returned empty transcription")
        normalized = normalize_manual_lyrics(transcribed)
        response = call_whisperx_endpoint_manual(
            str(vocal_path),
            normalized,
            None,
            config.enable_diarization,
            config.hf_token,
            config.whisper_model,
        )
        if not response or not response.get("srt_content"):
            raise AlignmentError("WhisperX returned no srt_content")
        return response["srt_content"]

    def group_segments(self, segments: list) -> list:
        return group_word_segments_automatic(segments, max_words_per_phrase=6, max_duration=3.5)


class ManualLyricsAlignment:
    is_manual_lyrics: bool = True

    def __init__(self, lyrics: str, language: str | None = None) -> None:
        self.normalized_lyrics = normalize_manual_lyrics(lyrics)
        self.language = language

    def align(self, vocal_path: Path, work_dir: Path, config: JobConfig) -> str:
        from karaoke.infra.whisperx_client import call_whisperx_endpoint_manual  # noqa: PLC0415

        response = call_whisperx_endpoint_manual(
            str(vocal_path),
            self.normalized_lyrics,
            self.language,
            config.enable_diarization,
            config.hf_token,
            config.whisper_model,
        )
        if not response or not response.get("srt_content"):
            raise AlignmentError("WhisperX returned no srt_content")
        return response["srt_content"]

    def group_segments(self, segments: list) -> list:
        return group_word_segments(self.normalized_lyrics, segments)
