"""Galician references: an aligner drafts them, the user reviews them by ear, and the lines
they flag get realigned inside the window their good neighbours (or their anchors) leave.
"""

import hashlib
import json
from pathlib import Path

from karaoke_bench.audio import cut, duration, file_sha256
from karaoke_bench.paths import BenchPaths
from karaoke_bench.pipeline import Pipeline
from karaoke_bench.reference import Reference, RefLine, RefWord
from karaoke_bench.runner import run_lyrics_stages
from karaoke_bench.sets import Song
from karaoke_bench.stage import StageItem, run_stage
from karaoke_bench.textnorm import lyrics_lines
from karaoke_contracts import Line
from karaoke_engine.steps import Stems

# An anchor marks where the user heard the line start; leave a little room before it.
ANCHOR_MARGIN = 0.2
# Shorter windows cannot hold a sung line.
MIN_WINDOW = 0.3


class DraftError(RuntimeError):
    pass


def reference_path(song: Song, paths: BenchPaths) -> Path:
    """Where a song's reference lives: versioned next to a manifest, else in bench/data."""
    if song.reference is not None:
        return song.reference
    if (paths.sets / song.set_name / "manifest.toml").is_file():
        return paths.sets / song.set_name / song.song_id / "reference.json"
    return paths.data / song.set_name / song.song_id / "reference.json"


def draft_reference(song: Song, pipeline: Pipeline, paths: BenchPaths) -> Reference:
    texts = lyrics_lines(song.lyrics_text() or "")
    if not texts:
        raise DraftError(f"{song.song_id} has no lyrics to align")
    pipeline.check("lyrics")
    _, aligned, _ = run_lyrics_stages([song], pipeline, paths, lines={song.song_id: texts})
    outcome = aligned[song.song_id]
    if outcome.error or outcome.output is None:
        raise DraftError(f"{song.song_id}: {outcome.error}")
    lines: list[Line] = outcome.output
    if len(lines) != len(texts):
        raise DraftError(f"aligner returned {len(lines)} lines for {len(texts)}")
    return Reference(
        song_id=song.song_id,
        language=song.language,
        duration=duration(song.audio),
        timing="semiautomatic",
        approved=False,
        lines=[
            _ref_line(text, line, 0.0, "draft") for text, line in zip(texts, lines, strict=True)
        ],
    )


def realign_windows(ref: Reference) -> list[tuple[int, int, float, float]]:
    """(first, end, start, stop) of each run of lines flagged wrong, end exclusive.

    Every anchor starts a window of its own, so marking where several lines begin pins each of
    them; the previous window then ends at that anchor.
    """
    windows: list[tuple[int, int, float, float]] = []
    i, lines = 0, ref.lines
    while i < len(lines):
        if lines[i].status != "wrong":
            i += 1
            continue
        j = i + 1
        while j < len(lines) and lines[j].status == "wrong" and lines[j].anchor is None:
            j += 1
        anchor = lines[i].anchor
        if anchor is not None:
            start = max(0.0, anchor - ANCHOR_MARGIN)
        else:
            start = lines[i - 1].end if i > 0 else 0.0
        stop = ref.duration
        if j < len(lines):
            next_anchor = lines[j].anchor
            stop = next_anchor if next_anchor is not None else lines[j].start
        if stop - start < MIN_WINDOW:
            lines_named = f"line {i + 1}" if j == i + 1 else f"lines {i + 1}-{j}"
            raise DraftError(
                f"{lines_named}: nothing to realign between {start:.2f} s and {stop:.2f} s; "
                f"move the anchor or mark line {j + 1} wrong too"
            )
        windows.append((i, j, start, stop))
        i = j
    return windows


def realign_reference(
    song: Song, ref: Reference, pipeline: Pipeline, paths: BenchPaths
) -> Reference:
    windows = realign_windows(ref)
    if not windows:
        return ref
    vocals = separated_vocals(song, pipeline, paths)
    work = paths.data / "realign" / song.song_id
    items = []
    for n, (first, end, start, stop) in enumerate(windows):
        piece = cut(vocals, start, stop, work / f"window-{n}.wav")
        texts = [line.text for line in ref.lines[first:end]]
        digest = hashlib.sha256(
            json.dumps([file_sha256(piece), texts, song.language]).encode()
        ).hexdigest()
        items.append(
            StageItem(
                f"{song.song_id}-{n}",
                {"vocals": str(piece), "lines": texts, "language": song.language},
                digest,
            )
        )
    outcome = run_stage(pipeline.steps["aligner"], items, paths)
    fixed = list(ref.lines)
    for item, (first, end, start, _) in zip(items, windows, strict=True):
        result = outcome.items[item.key]
        if result.error or result.output is None or len(result.output) != end - first:
            raise DraftError(f"realigning lines {first + 1}-{end}: {result.error or 'bad output'}")
        for k, line in enumerate(result.output):
            old = ref.lines[first + k]
            new = _ref_line(old.text, line, start, "draft")
            fixed[first + k] = new.model_copy(update={"revised": True, "note": old.note})
    return ref.model_copy(update={"lines": fixed, "approved": False})


def separated_vocals(song: Song, pipeline: Pipeline, paths: BenchPaths) -> Path:
    """The separated vocals (from the cache when the draft already computed them)."""
    return separated_stems(song, pipeline, paths).vocals


def separated_stems(song: Song, pipeline: Pipeline, paths: BenchPaths) -> Stems:
    if "separator" not in pipeline.steps:
        return Stems(vocals=song.audio, instrumental=song.audio)
    item = StageItem(song.song_id, {"audio": str(song.audio)}, file_sha256(song.audio))
    result = run_stage(pipeline.steps["separator"], [item], paths).items[song.song_id]
    if result.error or result.output is None:
        raise DraftError(f"separating {song.song_id}: {result.error}")
    stems: Stems = result.output
    return stems


def _ref_line(text: str, line: Line, offset: float, status: str) -> RefLine:
    return RefLine.model_validate(
        {
            "text": text,
            "start": line.start + offset,
            "end": line.end + offset,
            "words": [
                RefWord(text=w.text, start=w.start + offset, end=w.end + offset) for w in line.words
            ],
            "status": status,
        }
    )
