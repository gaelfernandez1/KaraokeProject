"""Text normalization for scoring lyrics, Galician first.

Scores compare words, not formatting: case, punctuation and section labels must not count as
errors, but accents do (in Galician "é" and "e" are different words). Bump
NORMALIZATION_VERSION whenever a rule changes, because it changes every score.
"""

import re
import unicodedata

NORMALIZATION_VERSION = 1

_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "´": "'", "`": "'"})
_LABEL = re.compile(r"\[[^\]]*\]")
# Repeat marks people add to pasted lyrics: "x2", "x3" with a multiplication sign, "(x2)",
# "(bis)", or "bis" ending a line.
_REPEAT = re.compile(
    r"\(\s*(?:[x\u00d7]\s*\d+|bis)\s*\)|(?<!\w)[x\u00d7]\s?\d+(?!\w)|(?<!\w)bis\s*$",
    re.IGNORECASE | re.MULTILINE,
)
# Hyphen-minus plus the Unicode hyphens and dashes (U+2010 to U+2015).
_DASHES = re.compile(r"[-\u2010-\u2015]")
_LOOSE_APOSTROPHE = re.compile(r"(?<!\w)'|'(?!\w)")
_SPACES = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Lowercase words separated by single spaces, ready for WER and CER."""
    text = unicodedata.normalize("NFC", text).lower().translate(_APOSTROPHES)
    text = _strip_marks(text)
    text = _DASHES.sub(" ", text)
    text = "".join(ch if ch.isalnum() or ch.isspace() or ch == "'" else " " for ch in text)
    text = _LOOSE_APOSTROPHE.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


def tokens(text: str) -> list[str]:
    return normalize(text).split()


def fold(token: str) -> str:
    """Drops diacritics, so "línea" and "linea" match when pairing words."""
    decomposed = unicodedata.normalize("NFD", token)
    return unicodedata.normalize(
        "NFC", "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    )


def match_key(word: str) -> str:
    """Key for pairing a displayed word with a reference word; empty for punctuation only."""
    return fold(normalize(word)).replace(" ", "")


def lyrics_lines(text: str) -> list[str]:
    """Sung lines of pasted lyrics, as displayed: no labels, repeat marks or blank lines."""
    lines = []
    for raw in text.lstrip("﻿").splitlines():
        line = _SPACES.sub(" ", _strip_marks(raw)).strip()
        if any(ch.isalnum() for ch in line):
            lines.append(line)
    return lines


def _strip_marks(text: str) -> str:
    return _REPEAT.sub(" ", _LABEL.sub(" ", text))
