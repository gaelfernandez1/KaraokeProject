"""Interfaces for the pipeline steps, so the bench can try any combination of implementations.

Each step is a Protocol: implementations don't inherit from anything, they just provide a
`name` (used in reports and provenance) and the method.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from karaoke_contracts import Line


@dataclass(frozen=True)
class Stems:
    vocals: Path
    instrumental: Path


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Transcript:
    language: str
    segments: tuple[TranscriptSegment, ...]


@runtime_checkable
class Separator(Protocol):
    name: str

    def separate(self, audio: Path, work_dir: Path) -> Stems: ...


@runtime_checkable
class Transcriber(Protocol):
    name: str

    def transcribe(self, vocals: Path, language: str) -> Transcript: ...


@runtime_checkable
class Segmenter(Protocol):
    """Turns a transcript into lyric lines when the user gave no lyrics."""

    name: str

    def segment(self, transcript: Transcript) -> list[str]: ...


@runtime_checkable
class Aligner(Protocol):
    name: str

    def align(self, vocals: Path, lyrics_lines: Sequence[str], language: str) -> list[Line]: ...


@runtime_checkable
class TextAligner(Protocol):
    """An aligner that reads the lyrics as pasted: section labels, repeat marks, backing parts.

    It may return a different number of lines than the text has (repeats it expands, lines it
    finds are not sung).
    """

    name: str

    def align_text(self, vocals: Path, lyrics: str, language: str) -> list[Line]: ...
