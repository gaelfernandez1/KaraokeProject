"""Shared data contracts for the karaoke generator."""

from karaoke_contracts.doc import (
    SCHEMA_VERSION,
    AudioRefs,
    KaraokeDoc,
    LanguageFallback,
    Line,
    Part,
    Provenance,
    Singer,
    VideoRefs,
    Word,
    dump_doc,
    load_doc,
)
from karaoke_contracts.validate import TIME_EPS, Issue, validate_doc, validate_package

__all__ = [
    "SCHEMA_VERSION",
    "TIME_EPS",
    "AudioRefs",
    "Issue",
    "KaraokeDoc",
    "LanguageFallback",
    "Line",
    "Part",
    "Provenance",
    "Singer",
    "VideoRefs",
    "Word",
    "dump_doc",
    "load_doc",
    "validate_doc",
    "validate_package",
]
