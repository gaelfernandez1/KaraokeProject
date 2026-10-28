"""The karaoke document (karaoke.json): synced lyrics shared by the player and the export."""

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

SCHEMA_VERSION = "1.0.0"

Seconds = Annotated[float, Field(ge=0, description="Seconds from the start of the song audio.")]
NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]
HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")]
# Paths inside the package folder, e.g. "instrumental.m4a".
MediaRef = Annotated[str, StringConstraints(min_length=1)]


class _Model(BaseModel):
    # Unknown fields are kept, so an older reader can load and re-save a newer minor version
    # without losing data. Infinity and NaN are refused: they break every time rule and are not
    # valid JSON for browsers. Fields with defaults are always written, so the serialization
    # schema marks them required (handy for TS consumers).
    model_config = ConfigDict(
        extra="allow",
        allow_inf_nan=False,
        json_schema_serialization_defaults_required=True,
    )


class Part(_Model):
    """A sub-unit of a word (a syllable or a group of letters) with its own timing."""

    text: NonEmptyStr
    start: Seconds
    end: Seconds


class Word(_Model):
    text: NonEmptyStr = Field(description="Text as displayed, with its original spelling.")
    start: Seconds
    end: Seconds
    confidence: Annotated[float, Field(ge=0, le=1)] | None = None
    parts: list[Part] = Field(
        default_factory=list,
        description="Optional sub-units; when present their texts concatenate to the word text.",
    )


class Line(_Model):
    id: NonEmptyStr
    start: Seconds
    end: Seconds
    singer: str | None = None
    words: Annotated[list[Word], Field(min_length=1)]


class Singer(_Model):
    id: NonEmptyStr
    name: str | None = None
    color: HexColor | None = None


class AudioRefs(_Model):
    instrumental: MediaRef
    vocals: MediaRef | None = None
    loudness_lufs: float | None = None


class VideoRefs(_Model):
    background: MediaRef | None = None


class LanguageFallback(_Model):
    """Records that a step could not use a resource for the requested language."""

    step: NonEmptyStr
    requested: NonEmptyStr
    used: NonEmptyStr
    reason: str


class Provenance(_Model):
    lyrics_source: Literal["user", "asr", "lrclib"]
    separation_model: str | None = None
    asr_model: str | None = None
    align_model: str | None = None
    engine_version: NonEmptyStr
    language_fallbacks: list[LanguageFallback] = Field(default_factory=list)


class KaraokeDoc(_Model):
    schema_version: Annotated[str, StringConstraints(pattern=r"^1\.\d+\.\d+$")] = SCHEMA_VERSION
    id: NonEmptyStr
    title: NonEmptyStr
    artist: str | None = None
    language: Annotated[str, StringConstraints(pattern=r"^[a-z]{2,3}$")]
    duration: Annotated[float, Field(gt=0)]
    audio: AudioRefs
    video: VideoRefs | None = None
    cover: MediaRef | None = None
    singers: list[Singer] = Field(default_factory=list)
    lines: list[Line]
    provenance: Provenance
    edited: bool = False


def load_doc(path: Path) -> KaraokeDoc:
    return KaraokeDoc.model_validate_json(path.read_bytes())


def dump_doc(doc: KaraokeDoc, path: Path) -> None:
    text = json.dumps(doc.model_dump(mode="json"), ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")
