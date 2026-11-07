"""Pasted lyrics into the lines that are actually sung, in order.

Lyrics sites write songs the way people read them, not the way they are sung: section labels
([Estribillo], [Verso 1: Ana]), repeat marks ("x2", "(bis)"), a chorus written once and then
only named, who sings a line ("Ela: …") and backing vocals in parentheses. This expands all of
it into a flat list of sung lines and keeps each line's text exactly as written, for display.
What the page itself adds (adverts, credits, labels without brackets…) goes first, in pasted.py.
"""

import itertools
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, replace

from karaoke_engine.align.pasted import strip_page_text

# Repeat marks: "x2", "\u00d73" and "2x" (as Portuguese and Galician sites write it), 2 to 9 times.
_N = r"([2-9])"
_MARK = rf"(?:[x\u00d7]\s?{_N}|{_N}\s?[x\u00d7])"
_ANY_CASE_MARK = rf"(?:[xX\u00d7]\s?{_N}|{_N}\s?[xX\u00d7])"
_PAREN_MARK = rf"\(\s*(?:{_ANY_CASE_MARK}|(?i:bis))\s*\)"
# After a sung word only a lowercase mark counts: "BMW X6" is a name, not "six times".
_TRAILING_REPEAT = re.compile(rf"\s+(?:{_MARK}|{_PAREN_MARK})\s*$")
# A mark before the line repeats that line: "(x3) Varre vasoira", "x2 Volta" (not "X6 …").
_LEADING_REPEAT = re.compile(rf"^(?:{_MARK}|{_PAREN_MARK})\s+(?=\S)")
# A bare "bis" only counts alone on its line: at the end of a sung line it may be a word.
_ONLY_REPEAT = re.compile(rf"^(?:{_ANY_CASE_MARK}|{_PAREN_MARK}|(?i:bis))$")
# A section label, with an optional repeat mark inside ("[Coro x2]") or after it ("[Coro] x2").
_HEADER = re.compile(rf"^\[([^\]]*)\]\s*(?:{_ANY_CASE_MARK}|{_PAREN_MARK})?$")
_LABEL_REPEAT = re.compile(rf"\s+(?:{_ANY_CASE_MARK}|{_PAREN_MARK})\s*$")
_PARENS = re.compile(r"\(([^()]*)\)")
_INLINE_BRACKETS = re.compile(r"\[[^\]]*\]")
_SPACES = re.compile(r"\s+")
# Who sings a line in a duet, as Spanish, Galician and Portuguese sites write it: "Ela: Vente".
_VOICES = (
    r"él|el|ella|ela|ellos|ellas|eles|elas|ambos|ambas|os dous|as dúas|os dois|as duas|los dos|"
    r"las dos|todos|todas|todes|juntos|juntas|xuntos|xuntas|he|she|him|her|both|together|"
    r"everyone|hombre|mujer|hombres|mujeres|home|muller|homes|mulleres|homem|mulher|chico|chica|"
    r"chicos|chicas|rapaz|rapaza|rapaces|rapazas"
)
_VOICE = re.compile(rf"^(?P<voice>{_VOICES})\s*:\s*(?P<rest>.*)$", re.IGNORECASE)
# Names of the chorus: "Repite el coro" brings back the one the site called [Estribillo].
_CHORUSES = frozenset({
    "coro", "estribillo", "chorus", "refrão", "refrao", "refrán", "refran", "retrouso",
    "refrain", "ritornello", "ritornelo", "refrany", "tornada", "hook",
})  # fmt: skip


@dataclass(frozen=True)
class LyricLine:
    text: str  # as displayed, original spelling and punctuation
    words: tuple[str, ...]
    section: str | None  # "Estribillo", "Verso 1"
    singer: str | None  # "Ana", "Ana, Brais", "Ela"
    backing: bool  # sung by the backing voices (written in parentheses)
    # Lines between blank lines or headers share it; each copy of a repeated section gets its
    # own. The aligner may sing a stanza's lines again when the site wrote them only once.
    stanza: int = 0


@dataclass
class _Section:
    name: str | None
    singer: str | None
    repeat: int
    lines: list[LyricLine]


def parse_lyrics(text: str, scopes: Mapping[int, int] | None = None) -> list[LyricLine]:
    """The sung lines. A repeat mark at the end of a line ("Fai moito tempo (x4)") repeats that
    line, or with `scopes` (mark number → lines) that many lines ending with it: sites write
    "(x4)" after a couplet sung four times as often as after a single line (see repeat_marks)."""
    return _parse(text, scopes or {})[0]


def repeat_marks(text: str) -> list[int]:
    """For each repeat mark at the end of a line, in order, how many lines it could cover: the
    line and those before it in its stanza. The aligner lets the audio choose (parse_lyrics)."""
    return _parse(text, {})[1]


def _parse(text: str, scopes: Mapping[int, int]) -> tuple[list[LyricLine], list[int]]:
    sections: list[_Section] = [_Section(None, None, 1, [])]
    stanza: list[LyricLine] = []
    # The rows of the current stanza as written (each row: its lead and backing parts), what a
    # repeat mark at the end of a row may cover; and how many rows each mark could cover.
    written: list[list[LyricLine]] = []
    marks: list[int] = []
    number = 0  # of the current stanza
    # A repeat mark alone after a blank line repeats the stanza before the blank.
    previous: list[LyricLine] = []
    # "Ela: …" sings until someone else does or a new section starts.
    voice: str | None = None
    # What the page adds goes first; the text comes back with composed accents ("í" typed as "i"
    # plus a mark looks the same and is matched as one letter) and without invisible characters.
    text = strip_page_text(text)
    for raw in text.splitlines():
        row = raw.strip()
        header = _HEADER.match(row)
        if header:
            section = _header_section(header.group(1))
            if row[header.end(1) + 1 :].strip():  # "[Estribillo] x2"
                section.repeat *= _count(header, skip=1)
            sections.append(section)
            stanza, previous, voice, written = [], [], None, []
            number += 1
            continue
        named = _VOICE.match(row)
        if named:
            voice, row = named.group("voice"), named.group("rest").strip()
            if not row:
                continue
        if not row:
            if stanza:
                previous = stanza
                number += 1
            stanza, written = [], []
            continue
        current = sections[-1]
        only = _ONLY_REPEAT.match(row)
        if only:
            source = stanza or previous
            extra = source * (_count(only) - 1)
            current.lines += extra
            stanza = source + extra
            continue
        count, scope = 1, 1
        leading = _LEADING_REPEAT.match(row)
        trailing = None if leading else _TRAILING_REPEAT.search(row)
        if leading:
            count = _count(leading)
            row = row[leading.end() :]
        elif trailing:
            count = _count(trailing)
            row = row[: trailing.start()]
            marks.append(len(written) + 1)
            scope = max(1, min(scopes.get(len(marks) - 1, 1), len(written) + 1))
        parts = _split_backing(row, current, voice, number)
        block = [line for rows in written[len(written) - scope + 1 :] for line in rows] + parts
        current.lines += parts + block * (count - 1)
        stanza += parts + block * (count - 1)
        written.append(parts)
    return _expand(sections), marks


def _header_section(label: str) -> _Section:
    repeat = 1
    trailing = _LABEL_REPEAT.search(label)
    if trailing:
        repeat = _count(trailing)
        label = label[: trailing.start()]
    name, _, singer = label.partition(":")
    return _Section(name.strip() or None, singer.strip() or None, repeat, [])


def _split_backing(row: str, section: _Section, voice: str | None, stanza: int) -> list[LyricLine]:
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
            lines.append(LyricLine(clean, tuple(clean.split()), section.name,
                                   voice or section.singer, backing, stanza))  # fmt: skip
    return lines


def _expand(sections: list[_Section]) -> list[LyricLine]:
    """Repeats sections marked "x2" and fills sections only named (an empty [Estribillo])."""
    out: list[LyricLine] = []
    seen: dict[str, list[LyricLine]] = {}
    chorus: list[LyricLine] = []
    numbers = itertools.count()
    for section in sections:
        lines = section.lines
        key = (section.name or "").casefold()
        if not lines and (key in seen or (_is_chorus(key) and chorus)):
            lines = seen.get(key) or chorus
            # Named again, maybe by someone else: "[Estribillo: Uxía]".
            if section.singer:
                lines = [replace(line, singer=section.singer) for line in lines]
        elif lines and key:
            seen[key] = lines
            if _is_chorus(key):
                chorus = lines
        for _ in range(section.repeat):
            # Each copy is a stanza of its own (or stanzas, as the section was written).
            renumber: dict[int, int] = {}
            for line in lines:
                if line.stanza not in renumber:
                    renumber[line.stanza] = next(numbers)
                out.append(replace(line, stanza=renumber[line.stanza]))
    return out


def _is_chorus(key: str) -> bool:
    return bool(key) and key.split()[0] in _CHORUSES


def _count(match: re.Match[str], skip: int = 0) -> int:
    number = next((group for group in match.groups()[skip:] if group), None)
    return int(number) if number else 2


def singer_id(name: str) -> str:
    """A stable singer id for a name from a section label ("Ana, Brais" → "ana-brais")."""
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-") or "singer"
