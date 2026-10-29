"""Approximate references from subtitle files someone timed by hand, word by word.

People time songs in subtitle editors: one entry per word, sometimes two words in one entry or one
word split into syllables, and the line breaks are lost. The lyrics give the words and the lines
back; the entries only give the times. Such timings are good to a few tenths of a second, so the
reference is marked approximate.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from karaoke_bench.reference import Reference, RefLine, RefWord
from karaoke_bench.textnorm import match_key

# Some editors write an extra hour field (00:00:01:32,340): only the last three fields count.
_STAMP = re.compile(
    r"(?:\d+:)?(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(?:\d+:)?(\d+):(\d+):(\d+)[,.](\d+)"
)


@dataclass(frozen=True)
class SrtEntry:
    start: float
    end: float
    text: str


def parse_srt(text: str) -> list[SrtEntry]:
    """Entries with text, in file order; blank entries (silences) are dropped."""
    entries = []
    for block in re.split(r"\n\s*\n", text.replace("\r", "").lstrip("﻿")):
        rows = [row.strip() for row in block.split("\n") if row.strip()]
        stamp_row = next((i for i, row in enumerate(rows) if "-->" in row), None)
        if stamp_row is None:
            continue
        match = _STAMP.search(rows[stamp_row])
        if match is None:
            raise ValueError(f"unreadable subtitle times: {rows[stamp_row]!r}")
        words = " ".join(rows[stamp_row + 1 :])
        if words:
            g = match.groups()
            entries.append(SrtEntry(_seconds(*g[:4]), _seconds(*g[4:]), words))
    return entries


def reference_from_srt(
    entries: Sequence[SrtEntry],
    lyrics_lines: Sequence[str],
    song_id: str,
    language: str,
    duration: float,
) -> Reference:
    """Pairs the timed words with the lyrics' words and takes the lines from the lyrics."""
    timed = _split_entries(entries)
    lines = []
    cursor = 0
    for text in lyrics_lines:
        words = []
        for word in text.split():
            start, end, cursor = _take_word(timed, cursor, word)
            words.append(RefWord(text=word, start=start, end=end))
        if words:
            lines.append(RefLine(text=text, start=words[0].start, end=words[-1].end, words=words))
    if cursor < len(timed):
        raise ValueError(f"subtitle word {timed[cursor][2]!r} comes after the lyrics end")
    return Reference(
        song_id=song_id,
        language=language,
        duration=duration,
        timing="approximate",
        approved=True,
        lines=lines,
    )


def _split_entries(entries: Sequence[SrtEntry]) -> list[tuple[float, float, str]]:
    """One item per word; an entry holding several words shares its span evenly."""
    words = []
    for entry in entries:
        parts = entry.text.split()
        step = (entry.end - entry.start) / len(parts)
        for i, part in enumerate(parts):
            words.append(
                (round(entry.start + i * step, 3), round(entry.start + (i + 1) * step, 3), part)
            )
    return words


def _take_word(
    timed: Sequence[tuple[float, float, str]], cursor: int, word: str
) -> tuple[float, float, int]:
    """Start, end and next cursor of a lyrics word, joining syllables split across entries."""
    target = match_key(word)
    joined = ""
    first = cursor
    while cursor < len(timed):
        joined += match_key(timed[cursor][2])
        cursor += 1
        if joined == target:
            return timed[first][0], timed[cursor - 1][1], cursor
        if not target.startswith(joined):
            break
    found = timed[first][2] if first < len(timed) else "nothing"
    raise ValueError(f"lyrics word {word!r} does not match subtitle word {found!r}")


def _seconds(hours: str, minutes: str, seconds: str, millis: str) -> float:
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis.ljust(3, "0")) / 1000
