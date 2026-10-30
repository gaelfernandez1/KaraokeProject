"""Warnings that need no reference: they work on any song, also the ones nobody has timed."""

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from karaoke_contracts import Word


def outside_voice(words: Sequence[Word], active: npt.NDArray[np.bool_], hop: float) -> float:
    """Share of the words' total time that falls where the vocals are silent."""
    total = outside = 0
    for word in words:
        first, last = round(word.start / hop), round(word.end / hop)
        span = active[first:last]
        total += last - first
        outside += int(np.count_nonzero(~span)) + max(0, (last - first) - len(span))
    return outside / total if total else 0.0


def low_confidence(words: Sequence[Word], below: float = 0.3) -> float | None:
    """Share of the words with a confidence under `below`, among those that have one."""
    rated = [word.confidence for word in words if word.confidence is not None]
    if not rated:
        return None
    return sum(value < below for value in rated) / len(rated)
