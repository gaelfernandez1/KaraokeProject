import numpy as np

from karaoke_engine.align.activity import vocal_activity

RATE = 16000
HOP = 0.02


def _tone(seconds: float, amplitude: float = 0.5) -> np.ndarray:
    t = np.arange(round(seconds * RATE)) / RATE
    return (amplitude * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def _silence(seconds: float) -> np.ndarray:
    return np.zeros(round(seconds * RATE), dtype=np.float32)


def test_activity_follows_tone_bursts() -> None:
    samples = np.concatenate([_silence(1), _tone(1), _silence(2), _tone(1), _silence(1)])

    active = vocal_activity(samples, RATE, HOP)

    assert len(active) == round(6 / HOP)
    expected = np.zeros(len(active), dtype=bool)
    expected[50:100] = True
    expected[200:250] = True
    assert np.count_nonzero(active != expected) <= 4


def test_quiet_bleed_is_not_voice() -> None:
    bleed = _tone(2, amplitude=0.5 * 10 ** (-45 / 20))
    samples = np.concatenate([_tone(1), bleed, _tone(1)])

    active = vocal_activity(samples, RATE, HOP)

    assert not active[60:140].any()


def test_short_gap_is_filled() -> None:
    samples = np.concatenate([_tone(1), _silence(0.1), _tone(1)])

    active = vocal_activity(samples, RATE, HOP)

    assert active[45:60].all()


def test_short_blip_is_dropped() -> None:
    samples = np.concatenate([_silence(1), _tone(0.06), _silence(1)])

    assert not vocal_activity(samples, RATE, HOP).any()


def test_silent_input_has_no_voice() -> None:
    assert not vocal_activity(_silence(2), RATE, HOP).any()
