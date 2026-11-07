"""CTC forced alignment of lyric lines that copes with what real songs do around them.

Plain CTC alignment must explain every frame with the lyrics or a blank. In a song that breaks
easily: an ad-lib or a backing vocal that is not in the lyrics gets glued to the nearest word,
and a line that is never sung is squeezed in somewhere anyway. Here the path may also:

- stay in a filler state between lines, which explains any sound for a cost per frame;
- jump over a whole line for a cost (lines a lyrics site has but the singer does not sing);
- pay extra for letters where the voice is silent (the caller marks those frames). The blank
  between two letters of one word pays it too: otherwise it can wait through a whole break for
  free (the two e of "Meer" were found 57 s apart). Between words the path rests for free;
- if asked, sing again lines of the same stanza right after them, for a cost each time: lyrics
  sites write a couplet sung four times, or a stanza sung twice, only once. From the filler after
  a line the path may go back to the filler before an earlier line of its stanza: up to
  `_REPEAT_SPAN` lines back, or back to any line when the repeat runs to the stanza's end.

States, in order: filler F0, the CTC states of line 1 (blank, t1, blank, ..., tn, blank), F1,
line 2, ..., Fk. Back-pointers are one byte per frame and state, and emissions are gathered per
frame from the compact matrix, so a long song needs no frames-by-states matrix of floats.
"""

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

BLANK = 0  # column of the blank in the compact emission matrix
ANY = 1  # column holding the best non-blank log-probability of each frame

_STAY, _NEXT, _SKIP, _JUMP, _BACK = 0, 1, 2, 3, 4
# Longest run of lines sung again that does not end the stanza.
_REPEAT_SPAN = 4


@dataclass(frozen=True)
class Segment:
    """One lyric line as model tokens."""

    tokens: tuple[int, ...]  # column indices into the compact emission matrix
    owner: tuple[int, ...]  # word index inside the line per token, -1 for delimiters
    skip_penalty: float  # cost of leaving the whole line out (inf = never)
    # Cost of leaving it out when the path starts after it or ends before it: lyrics that run
    # past the audio (a radio edit, a clip) lose lines at the edges, not in the middle.
    edge_skip_penalty: float = math.inf
    # The stanza the line belongs to: lines of one stanza may be sung again (see the module).
    group: int | None = None


@dataclass(frozen=True)
class SegmentPath:
    spans: list[tuple[int, int]] | None  # first and last frame of each token; None if skipped
    repeats: tuple[list[tuple[int, int]], ...] = ()  # the same for each time it is sung again


@dataclass(frozen=True)
class BestPath:
    paths: list[SegmentPath]
    score: float  # log-probability of the path with its costs: higher fits the audio better


def align_segments(
    log_probs: npt.NDArray[np.float32],
    segments: Sequence[Segment],
    filler_penalty: float,
    token_penalty: npt.NDArray[np.float32] | None = None,
    repeat_penalty: float = math.inf,
) -> list[SegmentPath]:
    """Best path through the lines; each line gets its tokens' frames or None if skipped."""
    return best_path(log_probs, segments, filler_penalty, token_penalty, repeat_penalty).paths


def best_path(
    log_probs: npt.NDArray[np.float32],
    segments: Sequence[Segment],
    filler_penalty: float,
    token_penalty: npt.NDArray[np.float32] | None = None,
    repeat_penalty: float = math.inf,
) -> BestPath:
    """align_segments with the score of its path, to compare readings of the same lyrics."""
    for segment in segments:
        if any(token in (BLANK, ANY) for token in segment.tokens) or not segment.tokens:
            raise ValueError("a segment needs tokens and they cannot use the blank or any column")
    frames = log_probs.shape[0]
    if frames == 0:
        return BestPath([SegmentPath(None) for _ in segments], -math.inf)
    layout = _Layout(segments)
    lp = log_probs.astype(np.float64)
    penalty = (
        np.zeros(frames) if token_penalty is None else np.asarray(token_penalty, dtype=np.float64)
    )

    size = layout.size
    edges = np.array([s.edge_skip_penalty for s in segments], dtype=np.float64)
    leading = np.concatenate([[0.0], np.cumsum(edges)])  # start at filler k: drop lines 1..k
    trailing = np.concatenate([np.cumsum(edges[::-1])[::-1], [0.0]])  # end at k: drop k+1..
    back = np.zeros((frames, size), dtype=np.int8)
    score = np.full(size, -np.inf)
    first_emit = _emit(lp, penalty, layout, filler_penalty, 0)
    score[layout.fillers] = first_emit[layout.fillers] - leading
    candidates = np.full((5, size), -np.inf)
    columns = np.arange(size)
    jump_cost = np.array([s.skip_penalty for s in segments], dtype=np.float64)
    repeats = _Repeats(segments) if math.isfinite(repeat_penalty) else None
    # The line each repeat starts again from, per frame and filler (only when repeats are on).
    came_from = np.zeros((frames if repeats else 0, len(segments)), dtype=np.int16)
    for t in range(1, frames):
        candidates[_STAY] = score
        candidates[_NEXT, 1:] = score[:-1]
        candidates[_SKIP, 2:] = np.where(layout.can_skip[2:], score[:-2], -np.inf)
        candidates[_JUMP, layout.fillers[1:]] = score[layout.fillers[:-1]] - jump_cost
        if repeats is not None:
            best, source = repeats.best(score[layout.fillers[1:]])
            candidates[_BACK, layout.fillers[:-1]] = best - repeat_penalty
            came_from[t] = source
        choice = candidates.argmax(axis=0)
        score = candidates[choice, columns] + _emit(lp, penalty, layout, filler_penalty, t)
        back[t] = choice

    path = np.empty(frames, dtype=np.int64)
    ends = score[layout.fillers] - trailing
    state = int(layout.fillers[int(np.argmax(ends))])
    for t in range(frames - 1, -1, -1):
        path[t] = state
        move = back[t, state]
        if move == _JUMP:
            state = layout.previous_filler[state]
        elif move == _BACK:
            # From the filler after the last line sung again to the one before the first.
            state = int(layout.fillers[came_from[t, layout.filler_index[state]] + 1])
        else:
            state -= int(move)
    return BestPath(layout.spans(path), float(np.max(ends)))


class _Repeats:
    """Where the path may go back to sing lines of a stanza again, and from where."""

    def __init__(self, segments: Sequence[Segment]) -> None:
        groups = [s.group for s in segments]
        count = len(segments)
        # The last line of each line's stanza, and whether a line may be sung again at all.
        self.repeatable = np.array([g is not None for g in groups])
        last = list(range(count))
        for i in range(count - 2, -1, -1):
            if groups[i] is not None and groups[i] == groups[i + 1]:
                last[i] = last[i + 1]
        self.stanza_end = np.array(last)
        # Starting again from line j after line j + k, for each k under _REPEAT_SPAN.
        index = np.arange(count)
        self.after = [
            (k, self.repeatable & (index + k <= self.stanza_end))
            for k in range(min(_REPEAT_SPAN, count))
        ]
        self.index = index

    def best(
        self, after_line: npt.NDArray[np.float64]
    ) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.int16]]:
        """For each line j, the best score of a filler after a later line of its stanza (from
        which the path may sing again from j on), and that line."""
        count = len(after_line)
        best = np.where(self.repeatable, after_line[self.stanza_end], -np.inf)
        source = self.stanza_end.copy()
        for k, allowed in self.after:
            shifted = np.full(count, -np.inf)
            shifted[: count - k] = after_line[k:]
            better = allowed & (shifted > best)
            best = np.where(better, shifted, best)
            source = np.where(better, self.index + k, source)
        return best, source.astype(np.int16)


class _Layout:
    """Where each line's states sit in the flat state vector, and what each state emits."""

    def __init__(self, segments: Sequence[Segment]) -> None:
        columns: list[int] = [-1]  # F0; -1 marks a filler
        fillers = [0]
        token_states: list[list[int]] = []
        can_skip = [False]
        # States that pay the silence cost: letters, and blanks inside a word.
        silenced = [False]
        for segment in segments:
            states = []
            for i, token in enumerate(segment.tokens):
                columns.append(BLANK)
                can_skip.append(False)
                inside = (
                    i > 0 and segment.owner[i] >= 0 and segment.owner[i] == segment.owner[i - 1]
                )
                silenced.append(inside)
                states.append(len(columns))
                silenced.append(segment.owner[i] >= 0)
                columns.append(token)
                # From the previous token over a blank, unless both are the same letter; the
                # first token may skip its leading blank and come straight from the filler.
                can_skip.append(i == 0 or token != segment.tokens[i - 1])
            columns.append(BLANK)
            can_skip.append(False)
            silenced.append(False)
            fillers.append(len(columns))
            columns.append(-1)
            can_skip.append(True)  # the filler may follow the last token directly
            silenced.append(False)
            token_states.append(states)
        self.size = len(columns)
        self.columns = np.array(columns)
        self.is_filler = self.columns < 0
        self.silenced = np.array(silenced)
        self.gather = np.where(self.is_filler, BLANK, self.columns)
        self.fillers = np.array(fillers)
        self.can_skip = np.array(can_skip)
        self.token_states = token_states
        self.previous_filler = {int(b): int(a) for a, b in itertools.pairwise(fillers)}
        self.filler_index = {int(state): k for k, state in enumerate(fillers)}

    def spans(self, path: npt.NDArray[np.int64]) -> list[SegmentPath]:
        """Each line's token frames, once for each time the path goes through the line."""
        out = []
        for states in self.token_states:
            # From the blank before the first token to the blank after the last one.
            inside = (path >= states[0] - 1) & (path <= states[-1] + 1)
            visits = []
            for first, last in _runs(inside):
                stretch = path[first : last + 1]
                spans = []
                for state in states:
                    hits = np.flatnonzero(stretch == state)
                    spans.append((first + int(hits[0]), first + int(hits[-1])))
                visits.append(spans)
            out.append(SegmentPath(visits[0], tuple(visits[1:])) if visits else SegmentPath(None))
        return out


def _runs(mask: npt.NDArray[np.bool_]) -> list[tuple[int, int]]:
    """First and last index of each run of True."""
    edges = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1) - 1
    return list(zip(starts.tolist(), ends.tolist(), strict=True))


def _emit(
    lp: npt.NDArray[np.float64],
    penalty: npt.NDArray[np.float64],
    layout: _Layout,
    filler_penalty: float,
    t: int,
) -> npt.NDArray[np.float64]:
    row = lp[t]
    emit: npt.NDArray[np.float64] = row[layout.gather].copy()
    emit[layout.silenced] -= penalty[t]
    emit[layout.is_filler] = max(row[BLANK], row[ANY] - filler_penalty - penalty[t])
    return emit
