import numpy as np
import pytest

from karaoke_bench.checks import low_confidence, outside_voice
from karaoke_contracts import Word


def test_outside_voice_share() -> None:
    active = np.zeros(100, dtype=bool)
    active[50:] = True
    words = [Word(text="ola", start=0.5, end=1.5)]

    assert outside_voice(words, active, hop=0.02) == pytest.approx(0.5)


def test_outside_voice_ignores_empty_words() -> None:
    active = np.ones(100, dtype=bool)

    assert outside_voice([Word(text="a", start=1.0, end=1.0)], active, hop=0.02) == 0.0


def test_low_confidence_share() -> None:
    words = [
        Word(text="a", start=0.0, end=1.0, confidence=0.1),
        Word(text="b", start=1.0, end=2.0, confidence=0.9),
        Word(text="c", start=2.0, end=3.0),
    ]

    assert low_confidence(words) == pytest.approx(0.5)
