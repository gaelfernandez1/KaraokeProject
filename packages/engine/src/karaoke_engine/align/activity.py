"""Where the separated vocals actually sound, from their loudness alone.

The separator leaves a little of the band in the vocals, so "voice" means loud compared with the
song's own singing, not merely not silent. Short dips inside a phrase (a stop consonant, a
breath) stay voice; short blips in a break are dropped.
"""

import numpy as np
import numpy.typing as npt

# Below this the vocals are silent whatever the song's level (dBFS).
_FLOOR_DB = -60.0
_FILL_GAPS = 0.15
_MIN_BURST = 0.1


def vocal_activity(
    samples: npt.NDArray[np.float32],
    rate: int = 16000,
    hop: float = 0.02,
    threshold_db: float = -35.0,
) -> npt.NDArray[np.bool_]:
    """One flag per `hop` seconds: True where the voice is within `threshold_db` of its peak."""
    size = round(hop * rate)
    count = -(-len(samples) // size)
    padded = np.zeros(count * size, dtype=np.float32)
    padded[: len(samples)] = samples
    rms = np.sqrt(np.mean(padded.reshape(count, size).astype(np.float64) ** 2, axis=1))
    level = 20 * np.log10(rms + 1e-10)
    peak = float(np.percentile(level, 95)) if count else _FLOOR_DB
    active = (level > max(peak + threshold_db, _FLOOR_DB)) & (peak > _FLOOR_DB)
    active = _fill_runs(active, value=False, shorter_than=round(_FILL_GAPS / hop), inner_only=True)
    return _fill_runs(active, value=True, shorter_than=round(_MIN_BURST / hop), inner_only=False)


def _fill_runs(
    flags: npt.NDArray[np.bool_], value: bool, shorter_than: int, inner_only: bool
) -> npt.NDArray[np.bool_]:
    """Flips runs of `value` shorter than `shorter_than` frames (only between others if inner)."""
    out = flags.copy()
    n = len(flags)
    i = 0
    while i < n:
        if flags[i] != value:
            i += 1
            continue
        j = i
        while j < n and flags[j] == value:
            j += 1
        inner = i > 0 and j < n
        if j - i < shorter_than and (inner or not inner_only):
            out[i:j] = not value
        i = j
    return out
