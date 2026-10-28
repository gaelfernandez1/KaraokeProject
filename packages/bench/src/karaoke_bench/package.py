"""Karaoke packages from public songs with manual timings, for the player and subtitle areas.

The displayed text comes from Jam-ALT (accents, punctuation) and the times from the manual
JamendoLyrics word annotations; words with no annotation get times between their neighbours.
"""

import re
import shutil
import unicodedata
from pathlib import Path

from karaoke_bench import __version__
from karaoke_bench.metrics import align_keys
from karaoke_bench.reference import Reference, RefLine
from karaoke_bench.sets import Song
from karaoke_bench.textnorm import match_key
from karaoke_contracts import (
    AudioRefs,
    KaraokeDoc,
    Line,
    Provenance,
    Singer,
    Word,
    dump_doc,
    validate_package,
)
from karaoke_engine.steps import Stems


class PackageError(RuntimeError):
    pass


def slug(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")


def display_words(line: RefLine) -> list[Word] | None:
    """The line's displayed words with the reference times; None if it has no timed words."""
    if not line.words:
        return None
    shown = line.text.split()
    times: list[tuple[float, float] | None] = [None] * len(shown)
    ref_keys = [match_key(w.text) for w in line.words]
    shown_keys = [match_key(t) for t in shown]
    ref_index = [i for i, k in enumerate(ref_keys) if k]
    shown_index = [i for i, k in enumerate(shown_keys) if k]
    for a, b in align_keys([ref_keys[i] for i in ref_index], [shown_keys[i] for i in shown_index]):
        word = line.words[ref_index[a]]
        times[shown_index[b]] = (word.start, word.end)
    if all(t is None for t in times):
        return None
    return [
        Word(text=text, start=s, end=e)
        for text, (s, e) in zip(shown, _fill(times, line), strict=True)
    ]


def build_package(
    song: Song, ref: Reference, stems: Stems, out_dir: Path, credits: str
) -> KaraokeDoc:
    lines: list[Line] = []
    for line in ref.lines:
        words = display_words(line)
        if words is None:
            continue
        lines.append(
            Line(
                id=f"l{len(lines) + 1}",
                start=words[0].start,
                end=max(w.end for w in words),
                singer="s1",
                words=words,
            )
        )
    separated = stems.vocals != song.audio
    doc = KaraokeDoc(
        id=slug(song.song_id),
        title=song.title,
        artist=song.artist,
        language=song.language,
        duration=ref.duration,
        audio=AudioRefs(instrumental="instrumental.wav", vocals="vocals.wav"),
        singers=[Singer(id="s1")],
        lines=lines,
        provenance=Provenance(
            lyrics_source="user",
            separation_model="htdemucs (bench baseline)" if separated else None,
            align_model="manual (JamendoLyrics MultiLang)" if ref.timing == "manual" else None,
            engine_version=f"karaoke-bench {__version__}",
        ),
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(stems.vocals, out_dir / "vocals.wav")
    shutil.copyfile(stems.instrumental, out_dir / "instrumental.wav")
    dump_doc(doc, out_dir / "karaoke.json")
    (out_dir / "LICENSE").write_text(credits, encoding="utf-8")
    issues = validate_package(out_dir)
    if issues:
        raise PackageError("; ".join(f"{i.path}: {i.message}" for i in issues[:5]))
    return doc


def _fill(times: list[tuple[float, float] | None], line: RefLine) -> list[tuple[float, float]]:
    """Spreads runs of untimed words evenly over the gap their timed neighbours leave."""
    filled: list[tuple[float, float]] = []
    i = 0
    while i < len(times):
        current = times[i]
        if current is not None:
            filled.append(current)
            i += 1
            continue
        j = i
        while j < len(times) and times[j] is None:
            j += 1
        start = filled[-1][1] if filled else line.start
        following = times[j] if j < len(times) else None
        stop = max(start, following[0] if following is not None else line.end)
        step = (stop - start) / (j - i)
        filled += [(start + k * step, start + (k + 1) * step) for k in range(j - i)]
        i = j
    return filled
