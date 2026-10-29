"""Validating a drafted reference where independent aligners agree, so nobody times it by ear.

Aligners built on different models fail in different places. Where several of them put every
word of a line within a tenth or two of each other, the line is very likely right: it is
validated automatically, with the median times. The lines they disagree on are the only ones
left for a person to listen to. The validation is only as independent as the aligners: scoring
one of them against such a reference flatters it a little.
"""

from collections.abc import Sequence
from statistics import median

from karaoke_bench.metrics import align_keys
from karaoke_bench.reference import Reference, RefLine, RefWord
from karaoke_bench.textnorm import match_key
from karaoke_contracts import Line

# A line passes when this share of its words agree; a song when this share of its words pass.
LINE_SHARE = 0.9
SONG_SHARE = 0.7


def triangulate(ref: Reference, runs: Sequence[list[Line]], tolerance: float) -> Reference:
    """Marks draft lines ok (median times) or unsure; lines a person reviewed stay as they are."""
    ref_keys = [match_key(word.text) for line in ref.lines for word in line.words]
    found: list[dict[int, tuple[float, float]]] = []
    for run in runs:
        hyp = [word for line in run for word in line.words]
        pairs = align_keys(ref_keys, [match_key(word.text) for word in hyp])
        found.append({r: (hyp[h].start, hyp[h].end) for r, h in pairs})

    lines = []
    flat = 0
    for line in ref.lines:
        indices = list(range(flat, flat + len(line.words)))
        flat += len(line.words)
        if line.status != "draft":
            lines.append(line)
            continue
        lines.append(_judge(line, indices, found, tolerance))
    total = sum(len(line.words) for line in lines)
    ok = sum(len(line.words) for line in lines if line.status == "ok")
    return ref.model_copy(
        update={"lines": lines, "approved": bool(total) and ok / total >= SONG_SHARE}
    )


def _judge(
    line: RefLine,
    indices: Sequence[int],
    found: Sequence[dict[int, tuple[float, float]]],
    tolerance: float,
) -> RefLine:
    agreeing = 0
    medians: list[tuple[float, float] | None] = []
    for index in indices:
        times = [run.get(index) for run in found]
        if any(t is None for t in times):
            medians.append(None)
            continue
        starts = [t[0] for t in times if t is not None]
        ends = [t[1] for t in times if t is not None]
        middle = median(starts)
        medians.append((middle, median(ends)))
        agreeing += all(abs(s - middle) <= tolerance for s in starts)
    if not indices or agreeing / len(indices) < LINE_SHARE or None in medians:
        return line.model_copy(update={"status": "unsure"})
    words = [
        RefWord(text=word.text, start=round(m[0], 3), end=round(max(m), 3))
        for word, m in zip(line.words, medians, strict=True)
        if m is not None
    ]
    return line.model_copy(
        update={
            "status": "ok",
            "words": words,
            "start": words[0].start,
            "end": max(w.end for w in words),
            "note": f"auto: coinciden {len(found)} alineadores",
        }
    )
