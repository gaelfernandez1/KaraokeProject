from collections.abc import Callable
from pathlib import Path

import pytest

from karaoke_bench.audio import (
    SAMPLE_RATE,
    AudioError,
    cut,
    duration,
    file_sha256,
    load_mono16k,
    peaks,
)

ToneMaker = Callable[..., Path]

pytestmark = pytest.mark.usefixtures("ffmpeg")


def test_duration_of_wav(make_tone: ToneMaker) -> None:
    audio = make_tone("tone.wav", 2.0)

    assert duration(audio) == pytest.approx(2.0, abs=0.01)


def test_load_mono16k_length(make_tone: ToneMaker) -> None:
    samples = load_mono16k(make_tone("tone.wav", 2.0))

    assert samples.dtype.name == "float32"
    assert abs(len(samples) - 2 * SAMPLE_RATE) <= 160
    assert 0.1 < float(abs(samples).max()) <= 1.0


def test_cut_segment(make_tone: ToneMaker, tmp_path: Path) -> None:
    audio = make_tone("tone.wav", 2.0)

    piece = cut(audio, 0.5, 1.5, tmp_path / "piece.wav")

    assert duration(piece) == pytest.approx(1.0, abs=0.01)


def test_peaks_shape(make_tone: ToneMaker) -> None:
    samples = load_mono16k(make_tone("tone.wav", 2.0))

    low, high = peaks(samples, rate=100)

    assert len(low) == len(high) == 200
    assert all(lo <= hi for lo, hi in zip(low, high, strict=True))


def test_missing_file_raises_audio_error(tmp_path: Path) -> None:
    with pytest.raises(AudioError):
        duration(tmp_path / "missing.wav")


def test_file_sha256(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_bytes(b"abc")

    assert file_sha256(path).startswith("ba7816bf")
