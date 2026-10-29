import math
import time
import tracemalloc

import numpy as np
import pytest

from karaoke_engine.align.ctc import Segment, align_segments

LOW = -8.0
HIGH = -0.01


def _emissions(frames: int, columns: int) -> np.ndarray:
    """Blank everywhere unless a test says otherwise; column 1 is the best non-blank."""
    lp = np.full((frames, columns), LOW, dtype=np.float32)
    lp[:, 0] = HIGH
    return lp


def _peak(lp: np.ndarray, frame: int, column: int) -> None:
    lp[frame, :] = LOW
    lp[frame, column] = HIGH


def _finish(lp: np.ndarray) -> np.ndarray:
    lp[:, 1] = np.maximum(lp[:, 1], lp[:, 2:].max(axis=1))
    return lp


def _segment(columns: list[int], skip: float = math.inf) -> Segment:
    return Segment(tokens=tuple(columns), owner=tuple(range(len(columns))), skip_penalty=skip)


def test_tokens_land_on_their_peaks() -> None:
    lp = _emissions(60, 6)
    for frame, column in [(10, 2), (12, 3), (40, 4), (42, 5)]:
        _peak(lp, frame, column)

    paths = align_segments(_finish(lp), [_segment([2, 3]), _segment([4, 5])], filler_penalty=3.0)

    assert [span[0] for span in paths[0].spans or []] == [10, 12]
    assert [span[0] for span in paths[1].spans or []] == [40, 42]


def test_filler_absorbs_sound_not_in_lyrics() -> None:
    lp = _emissions(70, 6)
    for frame, column in [(10, 2), (12, 3), (55, 4), (57, 5)]:
        _peak(lp, frame, column)
    lp[20:50, 0] = LOW  # something is sung there, but not these lyrics
    lp[20:50, 1] = -0.1

    paths = align_segments(_finish(lp), [_segment([2, 3]), _segment([4, 5])], filler_penalty=3.0)

    first, second = paths[0].spans or [], paths[1].spans or []
    assert first[-1][1] <= 14
    assert second[0][0] == 55


def test_unsung_line_is_skipped() -> None:
    lp = _emissions(60, 9)
    for frame, column in [(10, 2), (12, 3), (40, 7), (42, 8)]:
        _peak(lp, frame, column)
    segments = [_segment([2, 3], 5.0), _segment([4, 5, 6], 5.0), _segment([7, 8], 5.0)]

    paths = align_segments(_finish(lp), segments, filler_penalty=3.0)

    assert paths[1].spans is None
    assert [span[0] for span in paths[0].spans or []] == [10, 12]
    assert [span[0] for span in paths[2].spans or []] == [40, 42]


def test_lyrics_longer_than_audio_skips_lines() -> None:
    lp = _finish(_emissions(40, 62))
    segments = [_segment(list(range(2 + 6 * i, 8 + 6 * i)), 5.0) for i in range(10)]

    paths = align_segments(lp, segments, filler_penalty=3.0)

    assert sum(path.spans is None for path in paths) >= 4


def test_silence_penalty_keeps_tokens_out() -> None:
    lp = _emissions(40, 3)
    lp[:, 0] = -1.5
    lp[10:31, 2] = -1.0
    penalty = np.zeros(40, dtype=np.float32)
    penalty[:26] = 10.0

    paths = align_segments(_finish(lp), [_segment([2])], filler_penalty=3.0, token_penalty=penalty)

    assert (paths[0].spans or [])[0][0] >= 26


def test_repeated_tokens_keep_a_blank_between() -> None:
    lp = _emissions(30, 3)
    _peak(lp, 10, 2)
    _peak(lp, 14, 2)

    paths = align_segments(_finish(lp), [_segment([2, 2])], filler_penalty=3.0)

    assert [span[0] for span in paths[0].spans or []] == [10, 14]


def test_no_frames_skips_everything() -> None:
    lp = np.zeros((0, 3), dtype=np.float32)

    assert align_segments(lp, [_segment([2], 1.0)], filler_penalty=3.0)[0].spans is None


def test_long_song_uses_compact_backpointers() -> None:
    rng = np.random.default_rng(0)
    lp = rng.uniform(-6.0, -0.1, size=(30_000, 102)).astype(np.float32)
    segments = [_segment(list(rng.integers(2, 102, size=20)), 40.0) for _ in range(100)]

    tracemalloc.start()
    started = time.perf_counter()
    align_segments(_finish(lp), segments, filler_penalty=3.0)
    seconds = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert seconds < 60
    assert peak < 200 * 2**20


@pytest.mark.parametrize("bad", [0, 1])
def test_tokens_must_not_use_blank_or_any_columns(bad: int) -> None:
    with pytest.raises(ValueError, match="column"):
        align_segments(_finish(_emissions(10, 3)), [_segment([bad])], filler_penalty=3.0)


def test_blank_inside_a_word_does_not_wait_through_silence() -> None:
    # "ee": the blank between the two letters must not sit through a break to reach a later
    # sound; between words the path may rest for free.
    lp = _emissions(220, 3)
    _peak(lp, 10, 2)
    lp[12, 2] = -3.0
    _peak(lp, 200, 2)
    penalty = np.zeros(220, dtype=np.float32)
    penalty[15:195] = 4.0
    segment = Segment(tokens=(2, 2), owner=(0, 0), skip_penalty=math.inf)

    [path] = align_segments(_finish(lp), [segment], filler_penalty=3.0, token_penalty=penalty)

    assert (path.spans or [])[1][0] < 20


def test_pause_between_words_is_free() -> None:
    lp = _emissions(220, 4)
    _peak(lp, 10, 2)
    _peak(lp, 200, 3)
    penalty = np.zeros(220, dtype=np.float32)
    penalty[15:195] = 4.0
    segment = Segment(tokens=(2, 3), owner=(0, 1), skip_penalty=math.inf)

    [path] = align_segments(_finish(lp), [segment], filler_penalty=3.0, token_penalty=penalty)

    assert [span[0] for span in path.spans or []] == [10, 200]


def test_delimiters_pay_no_silence_cost() -> None:
    lp = _emissions(60, 5)
    _peak(lp, 10, 2)
    lp[30, 4] = -0.5  # the word delimiter, clearest where the voice pauses
    lp[47, 4] = -2.0
    _peak(lp, 50, 3)
    penalty = np.zeros(60, dtype=np.float32)
    penalty[20:45] = 10.0
    segment = Segment(tokens=(2, 4, 3), owner=(0, -1, 1), skip_penalty=math.inf)

    [path] = align_segments(_finish(lp), [segment], filler_penalty=3.0, token_penalty=penalty)

    assert (path.spans or [])[1][0] == 30
