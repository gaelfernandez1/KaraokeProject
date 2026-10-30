"""The stress set: public songs with exact timings, given the trouble real songs bring.

Real karaoke songs have long instrumental breaks, ad-libs and echoes that are not in the lyrics,
and lyrics pasted from the web with labels, repeat marks and lines that are missing or never
sung. Doing that to JamendoLyrics songs keeps their hand-made word timings exact: every edit
knows how far it moves the audio. The recipe (bench/sets/stress.toml) is versioned; the audio
is built locally into bench/data/stress/ and never leaves the machine.
"""

import itertools
import random
import subprocess
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from karaoke_bench.audio import AudioError, load_stereo
from karaoke_bench.paths import BenchPaths
from karaoke_bench.reference import Reference, RefWord, dump_reference, load_reference
from karaoke_bench.sets import read_meta, write_meta

Audio = npt.NDArray[np.float32]
GROUPS = ("gap", "adlib", "echo", "web", "missing-line", "extra-lines")
GAP_SECONDS = 30.0
# Silence around sung words that a cut or a pasted filler must keep clear of.
_MARGIN = 0.3
_FADE = 0.05
_RATE = 44100


def word_free_spans(ref: Reference, min_seconds: float) -> list[tuple[float, float]]:
    """Stretches of at least `min_seconds` with no sung word: intro, between words and outro."""
    words = sorted((w for line in ref.lines for w in line.words), key=lambda w: w.start)
    if not words:
        return [(0.0, ref.duration)] if ref.duration >= min_seconds else []
    spans = []
    edges = [(0.0, words[0].start)]
    edges += [(w.end, nxt.start) for w, nxt in itertools.pairwise(words)]
    edges.append((words[-1].end, ref.duration))
    for start, end in edges:
        if end - start >= min_seconds:
            spans.append((start, end))
    return spans


def insert_gap(
    audio: Audio,
    rate: int,
    ref: Reference,
    before_line: int,
    seconds: float,
    filler: tuple[float, float],
) -> tuple[Audio, Reference]:
    """Puts `seconds` of the filler stretch, looped, halfway into the pause before a line."""
    line = ref.lines[before_line]
    previous_end = max(
        (w.end for other in ref.lines for w in other.words if w.end <= line.start), default=0.0
    )
    at = (previous_end + line.start) / 2
    loop = audio[round(filler[0] * rate) : round(filler[1] * rate)]
    count = round(seconds * rate)
    block = np.resize(loop, (count, audio.shape[1])).astype(np.float32)
    _fade_edges(block, rate)
    cut = round(at * rate)
    out = np.concatenate([audio[:cut], block, audio[cut:]])
    return out, _shift_after(ref, at, seconds)


def overlay(
    audio: Audio, rate: int, source: tuple[float, float], at: float, gain_db: float
) -> Audio:
    """Adds a copy of the source stretch at `at`, scaled by `gain_db`; same length out."""
    piece = audio[round(source[0] * rate) : round(source[1] * rate)].copy()
    _fade_edges(piece, rate)
    start = round(at * rate)
    piece = piece[: max(0, len(audio) - start)]
    out = audio.copy()
    out[start : start + len(piece)] += piece * np.float32(10 ** (gain_db / 20))
    return out


def perturb_lyrics(
    lines: Sequence[str], ops: Sequence[str], rng: random.Random, foreign: Sequence[str]
) -> str:
    """The lyrics as a lyrics site might give them; the sung truth (the reference) is unchanged."""
    out = list(lines)
    for op in ops:
        if op == "x2":
            out = _collapse_repeats(out)
        elif op == "missing-line":
            del out[_middle_index(out, rng)]
        elif op == "extra-lines":
            at = _middle_index(out, rng)
            out[at:at] = list(foreign[:2])
        elif op == "parens":
            for i in rng.sample(range(len(out)), k=min(3, len(out))):
                out[i] = f"{out[i]} ({rng.choice(['yeah', 'oh'])})"
        elif op == "headers":
            out = _with_headers(out)
        else:
            raise ValueError(f"unknown lyrics change '{op}'")
    return "\n".join(out)


def build_stress(paths: BenchPaths, recipe: Path) -> list[str]:
    """Builds every song of the recipe into bench/data/stress/<id>/ (skips up-to-date ones)."""
    with recipe.open("rb") as handle:
        data = tomllib.load(handle)
    version = str(data["version"])
    ids = []
    for entry in data.get("songs", []):
        out_dir = paths.data / "stress" / entry["id"]
        meta_path = out_dir / "meta.toml"
        ids.append(entry["id"])
        if meta_path.is_file() and read_meta(meta_path).get("recipe") == version:
            continue
        _build_song(paths, entry, version, out_dir)
    return ids


def _build_song(paths: BenchPaths, entry: dict[str, Any], version: str, out_dir: Path) -> None:
    group = entry["group"]
    if group not in GROUPS:
        raise ValueError(f"{entry['id']}: unknown group '{group}' (use {', '.join(GROUPS)})")
    source_dir = paths.data / "jamendo" / entry["source"]
    ref = load_reference(source_dir / "reference.json")
    meta = read_meta(source_dir / "meta.toml")
    found = sorted(source_dir.glob("audio.*"))
    if not found:
        raise AudioError(source_dir, "no audio; run `karaoke-bench fetch --set jamendo` first")
    audio = load_stereo(found[0], _RATE)
    rng = random.Random(entry["seed"])
    lines = [line.text for line in ref.lines]
    lyrics = "\n".join(lines)

    if group == "gap":
        before = _middle_line_after_pause(ref)
        filler = max(word_free_spans(ref, 3.0), key=lambda span: span[1] - span[0])
        filler = (filler[0] + _MARGIN, filler[1] - _MARGIN)
        audio, ref = insert_gap(audio, _RATE, ref, before, GAP_SECONDS, filler)
    elif group == "adlib":
        inner = [s for s in word_free_spans(ref, 2.0) if s[0] > 0 and s[1] < ref.duration]
        if not inner:
            raise ValueError(f"{entry['source']}: no pause of 2 s between lines for an ad-lib")
        span = max(inner, key=lambda s: s[1] - s[0])
        longest = min(2.5, span[1] - span[0])
        phrase = rng.choice([line for line in ref.lines if 0.8 <= line.end - line.start <= longest])
        middle = (span[0] + span[1]) / 2
        at = middle - (phrase.end - phrase.start) / 2
        audio = overlay(audio, _RATE, (phrase.start, phrase.end), at, gain_db=-3.0)
    elif group == "echo":
        for line in rng.sample(ref.lines, k=min(4, len(ref.lines))):
            audio = overlay(audio, _RATE, (line.start, line.end), line.start + 0.8, gain_db=-8.0)
    elif group == "web":
        lyrics = perturb_lyrics(lines, ["headers", "x2", "parens"], rng, [])
    elif group == "missing-line":
        lyrics = perturb_lyrics(lines, ["missing-line"], rng, [])
    else:
        foreign_ref = load_reference(paths.data / "jamendo" / entry["foreign"] / "reference.json")
        foreign = [line.text for line in foreign_ref.lines]
        lyrics = perturb_lyrics(lines, ["extra-lines"], rng, foreign[len(foreign) // 2 :])

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_flac(out_dir / "audio.flac", audio, _RATE)
    dump_reference(ref.model_copy(update={"song_id": entry["id"]}), out_dir / "reference.json")
    (out_dir / "lyrics.txt").write_text(lyrics + "\n", encoding="utf-8")
    write_meta(
        out_dir / "meta.toml",
        {
            "title": f"{meta.get('title', entry['source'])} ({group})",
            "artist": meta.get("artist"),
            "language": ref.language,
            "group": group,
            "source": entry["source"],
            "license": meta.get("license"),
            "recipe": version,
        },
    )


def _middle_line_after_pause(ref: Reference) -> int:
    """The line nearest the middle of the song that follows a pause (cutting there is clean)."""
    candidates = []
    for i in range(1, len(ref.lines)):
        before = max(
            (w.end for line in ref.lines[:i] for w in line.words), default=ref.lines[i].start
        )
        if ref.lines[i].start - before >= _MARGIN:
            candidates.append(i)
    if not candidates:
        raise ValueError(f"{ref.song_id}: no pause between lines to insert a break into")
    middle = len(ref.lines) / 2
    return min(candidates, key=lambda i: abs(i - middle))


def _shift_after(ref: Reference, at: float, seconds: float) -> Reference:
    def move(t: float) -> float:
        return round(t + seconds, 3) if t >= at else t

    lines = [
        line.model_copy(
            update={
                "start": move(line.start),
                "end": move(line.end),
                "words": [
                    RefWord(text=w.text, start=move(w.start), end=move(w.end)) for w in line.words
                ],
            }
        )
        for line in ref.lines
    ]
    return ref.model_copy(update={"lines": lines, "duration": round(ref.duration + seconds, 3)})


def _fade_edges(block: Audio, rate: int) -> None:
    n = min(round(_FADE * rate), len(block) // 2)
    if n:
        ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)[:, None]
        block[:n] *= ramp
        block[-n:] *= ramp[::-1]


def _collapse_repeats(lines: list[str]) -> list[str]:
    out: list[str] = []
    count = 0
    for i, line in enumerate(lines):
        count += 1
        if i + 1 < len(lines) and lines[i + 1] == line:
            continue
        out.append(f"{line} x{count}" if count > 1 else line)
        count = 0
    return out


def _with_headers(lines: list[str]) -> list[str]:
    out: list[str] = []
    verse = 0
    for i, line in enumerate(lines):
        if i % 4 == 0:
            if (i // 4) % 2 == 0:
                verse += 1
                out.append(f"[Verso {verse}]")
            else:
                out.append("[Estribillo]")
        out.append(line)
    return out


def _middle_index(lines: Sequence[str], rng: random.Random) -> int:
    third = len(lines) // 3
    return rng.randrange(third, max(third + 1, len(lines) - third))


def _write_flac(path: Path, audio: Audio, rate: int) -> None:
    result = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "f32le", "-ar", str(rate), "-ac",
         str(audio.shape[1]), "-i", "pipe:0", "-c:a", "flac", str(path)],
        input=np.clip(audio, -1.0, 1.0).astype("<f4").tobytes(),
        capture_output=True,
        check=False,
    )  # fmt: skip
    if result.returncode != 0:
        raise AudioError(path, result.stderr.decode(errors="replace"))
