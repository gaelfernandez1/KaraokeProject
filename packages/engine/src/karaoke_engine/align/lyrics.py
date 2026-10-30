"""Pasted lyrics into the lines that are actually sung, in order.

Lyrics sites write songs the way people read them, not the way they are sung: section labels
([Estribillo], [Verso 1: Ana]), repeat marks ("x2", "(bis)"), a chorus written once and then
only named, and backing vocals in parentheses. This expands all of it into a flat list of sung
lines and keeps each line's text exactly as written, for display.
"""

import re
import unicodedata
from dataclasses import dataclass

_HEADER = re.compile(r"^\[([^\]]*)\]$")
_REPEAT = r"(?:[x\u00d7]\s?(\d+)|\(\s*[x\u00d7]\s?(\d+)\s*\)|\(\s*bis\s*\))"
_TRAILING_REPEAT = re.compile(rf"\s+{_REPEAT}\s*$", re.IGNORECASE)
# A bare "bis" only counts alone on its line: at the end of a sung line it may be a word.
_ONLY_REPEAT = re.compile(rf"^(?:{_REPEAT}|bis)$", re.IGNORECASE)
# Zero-width characters and stray byte order marks that web pages leave in copied text.
_INVISIBLE = re.compile("[\u200b-\u200d\u2060\ufeff]")
_PARENS = re.compile(r"\(([^()]*)\)")
_INLINE_BRACKETS = re.compile(r"\[[^\]]*\]")
_SPACES = re.compile(r"\s+")


@dataclass(frozen=True)
class LyricLine:
    text: str  # as displayed, original spelling and punctuation
    words: tuple[str, ...]
    section: str | None  # "Estribillo", "Verso 1"
    singer: str | None  # "Ana", "Ana, Brais"
    backing: bool  # sung by the backing voices (written in parentheses)


@dataclass
class _Section:
    name: str | None
    singer: str | None
    repeat: int
    lines: list[LyricLine]


def parse_lyrics(text: str) -> list[LyricLine]:
    sections: list[_Section] = [_Section(None, None, 1, [])]
    stanza: list[LyricLine] = []
    # A repeat mark alone after a blank line repeats the stanza before the blank.
    previous: list[LyricLine] = []
    for raw in _INVISIBLE.sub("", text).splitlines():
        row = raw.strip()
        header = _HEADER.match(row)
        if header:
            sections.append(_header_section(header.group(1)))
            stanza, previous = [], []
            continue
        if not row:
            if stanza:
                previous = stanza
            stanza = []
            continue
        current = sections[-1]
        only = _ONLY_REPEAT.match(row)
        if only:
            source = stanza or previous
            extra = source * (_count(only) - 1)
            current.lines += extra
            stanza = source + extra
            continue
        count = 1
        trailing = _TRAILING_REPEAT.search(row)
        if trailing:
            count = _count(trailing)
            row = row[: trailing.start()]
        parts = _split_backing(row, current)
        current.lines += parts * count
        stanza += parts * count
    return _expand(sections)


def _header_section(label: str) -> _Section:
    repeat = 1
    trailing = _TRAILING_REPEAT.search(label)
    if trailing:
        repeat = _count(trailing)
        label = label[: trailing.start()]
    name, _, singer = label.partition(":")
    return _Section(name.strip() or None, singer.strip() or None, repeat, [])


def _split_backing(row: str, section: _Section) -> list[LyricLine]:
    """The lead part and each parenthesised backing part, in the order they are written."""
    row = _INLINE_BRACKETS.sub(" ", row)
    pieces: list[tuple[str, bool]] = []
    cursor = 0
    for match in _PARENS.finditer(row):
        pieces.append((row[cursor : match.start()], False))
        pieces.append((match.group(1), True))
        cursor = match.end()
    pieces.append((row[cursor:], False))
    lines = []
    for piece, backing in pieces:
        clean = _SPACES.sub(" ", piece).strip()
        if any(ch.isalnum() for ch in clean):
            lines.append(LyricLine(clean, tuple(clean.split()), section.name, section.singer,
                                   backing))  # fmt: skip
    return lines


def _expand(sections: list[_Section]) -> list[LyricLine]:
    """Repeats sections marked "x2" and fills sections only named (an empty [Estribillo])."""
    out: list[LyricLine] = []
    seen: dict[str, list[LyricLine]] = {}
    for section in sections:
        lines = section.lines
        key = (section.name or "").casefold()
        if not lines and key in seen:
            lines = seen[key]
        elif lines and key:
            seen[key] = lines
        out += lines * section.repeat
    return out


def _count(match: re.Match[str]) -> int:
    number = next((group for group in match.groups() if group), None)
    return int(number) if number else 2


def singer_id(name: str) -> str:
    """A stable singer id for a name from a section label ("Ana, Brais" → "ana-brais")."""
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-") or "singer"
