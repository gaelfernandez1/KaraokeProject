"""CTC forced alignment of lyric lines that copes with what real songs do around them.

Plain CTC alignment must explain every frame with the lyrics or a blank. In a song that breaks
easily: an ad-lib or a backing vocal that is not in the lyrics gets glued to the nearest word,
and a line that is never sung is squeezed in somewhere anyway. Here the path may also:

- stay in a filler state between lines, which explains any sound for a cost per frame;
- jump over a whole line for a cost (lines a lyrics site has but the singer does not sing);
- pay extra for letters where the voice is silent (the caller marks those frames).

States, in order: filler F0, the CTC states of line 1 (blank, t1, blank, ..., tn, blank), F1,
line 2, ..., Fk. Back-pointers are one byte per frame and state, and emissions are gathered per
frame from the compact matrix, so a long song needs no frames-by-states matrix of floats.
"""

import itertools
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

BLANK = 0  # column of the blank in the compact emission matrix
ANY = 1  # column holding the best non-blank log-probability of each frame

_STAY, _NEXT, _SKIP, _JUMP = 0, 1, 2, 3


@dataclass(frozen=True)
class Segment:
    """One lyric line as model tokens."""

    tokens: tuple[int, ...]  # column indices into the compact emission matrix
    owner: tuple[int, ...]  # word index inside the line per token, -1 for delimiters
    skip_penalty: float  # cost of leaving the whole line out (inf = never)


@dataclass(frozen=True)
class SegmentPath:
    spans: list[tuple[int, int]] | None  # first and last frame of each token; None if skipped


def align_segments(
    log_probs: npt.NDArray[np.float32],
    segments: Sequence[Segment],
    filler_penalty: float,
    token_penalty: npt.NDArray[np.float32] | None = None,
) -> list[SegmentPath]:
    """Best path through the lines; each line gets its tokens' frames or None if skipped."""
    for segment in segments:
        if any(token in (BLANK, ANY) for token in segment.tokens) or not segment.tokens:
            raise ValueError("a segment needs tokens and they cannot use the blank or any column")
    frames = log_probs.shape[0]
    if frames == 0:
        return [SegmentPath(None) for _ in segments]
    layout = _Layout(segments)
    lp = log_probs.astype(np.float64)
    penalty = (
        np.zeros(frames) if token_penalty is None else np.asarray(token_penalty, dtype=np.float64)
    )

    size = layout.size
    back = np.zeros((frames, size), dtype=np.int8)
    score = np.full(size, -np.inf)
    score[0] = _emit(lp, penalty, layout, filler_penalty, 0)[0]
    candidates = np.full((4, size), -np.inf)
    columns = np.arange(size)
    jump_cost = np.array([s.skip_penalty for s in segments], dtype=np.float64)
    for t in range(1, frames):
        candidates[_STAY] = score
        candidates[_NEXT, 1:] = score[:-1]
        candidates[_SKIP, 2:] = np.where(layout.can_skip[2:], score[:-2], -np.inf)
        candidates[_JUMP, layout.fillers[1:]] = score[layout.fillers[:-1]] - jump_cost
        choice = candidates.argmax(axis=0)
        score = candidates[choice, columns] + _emit(lp, penalty, layout, filler_penalty, t)
        back[t] = choice

    path = np.empty(frames, dtype=np.int64)
    state = layout.fillers[-1]
    for t in range(frames - 1, -1, -1):
        path[t] = state
        move = back[t, state]
        if move == _JUMP:
            state = layout.previous_filler[state]
        else:
            state -= int(move)
    return layout.spans(path)


class _Layout:
    """Where each line's states sit in the flat state vector, and what each state emits."""

    def __init__(self, segments: Sequence[Segment]) -> None:
        columns: list[int] = [-1]  # F0; -1 marks a filler
        fillers = [0]
        token_states: list[list[int]] = []
        can_skip = [False]
        for segment in segments:
            states = []
            for i, token in enumerate(segment.tokens):
                columns.append(BLANK)
                can_skip.append(False)
                states.append(len(columns))
                columns.append(token)
                # From the previous token over a blank, unless both are the same letter; the
                # first token may skip its leading blank and come straight from the filler.
                can_skip.append(i == 0 or token != segment.tokens[i - 1])
            columns.append(BLANK)
            can_skip.append(False)
            fillers.append(len(columns))
            columns.append(-1)
            can_skip.append(True)  # the filler may follow the last token directly
            token_states.append(states)
        self.size = len(columns)
        self.columns = np.array(columns)
        self.is_filler = self.columns < 0
        self.is_token = self.columns > ANY
        self.gather = np.where(self.is_filler, BLANK, self.columns)
        self.fillers = np.array(fillers)
        self.can_skip = np.array(can_skip)
        self.token_states = token_states
        self.previous_filler = {int(b): int(a) for a, b in itertools.pairwise(fillers)}

    def spans(self, path: npt.NDArray[np.int64]) -> list[SegmentPath]:
        frames = np.arange(len(path))
        out = []
        for states in self.token_states:
            if not np.isin(states[0], path):
                out.append(SegmentPath(None))
                continue
            spans = []
            for state in states:
                hits = frames[path == state]
                spans.append((int(hits[0]), int(hits[-1])))
            out.append(SegmentPath(spans))
        return out


def _emit(
    lp: npt.NDArray[np.float64],
    penalty: npt.NDArray[np.float64],
    layout: _Layout,
    filler_penalty: float,
    t: int,
) -> npt.NDArray[np.float64]:
    row = lp[t]
    emit: npt.NDArray[np.float64] = row[layout.gather].copy()
    emit[layout.is_token] -= penalty[t]
    emit[layout.is_filler] = max(row[BLANK], row[ANY] - filler_penalty - penalty[t])
    return emit
