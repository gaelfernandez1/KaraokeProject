import pytest

from karaoke_bench.metrics import (
    TimingErrors,
    line_start_errors,
    pair_words,
    text_errors,
    timing_errors,
    timing_stats,
)
from karaoke_bench.reference import RefLine, RefWord
from karaoke_contracts import Line, Word


def test_text_errors_ignore_case_and_punctuation() -> None:
    errors = text_errors("Ola, mar!", "ola mar")

    assert errors.wer == 0.0
    assert errors.cer == 0.0
    assert errors.ref_words == 2


def test_text_errors_count_lost_accent_as_error() -> None:
    assert text_errors("o mar é azul", "o mar e azul").wer == pytest.approx(0.25)


def test_text_errors_empty_hypothesis() -> None:
    errors = text_errors("ola mar", "")

    assert errors.wer == 1.0
    assert errors.cer == 1.0


def test_pair_words_ignores_accents_and_skips_inserted_words() -> None:
    ref = [
        RefWord(text="linea", start=1.0, end=1.4),
        RefWord(text="mar", start=1.5, end=2.0),
        RefWord(text="azul", start=2.0, end=2.5),
    ]
    hyp = [
        Word(text="Línea,", start=1.1, end=1.4),
        Word(text="verde", start=1.4, end=1.5),
        Word(text="mar", start=1.6, end=2.0),
        Word(text="azul", start=2.4, end=2.6),
    ]

    pairs = pair_words(ref, hyp)

    assert [p.ref.text for p in pairs] == ["linea", "mar", "azul"]
    assert pairs[0].hyp_start == 1.1
    assert pairs[2].hyp_end == 2.6


def test_pair_words_skips_punctuation_only_words() -> None:
    ref = [RefWord(text="ola", start=0.0, end=0.5), RefWord(text="mar", start=1.0, end=1.5)]
    hyp = [
        Word(text="ola", start=0.1, end=0.5),
        Word(text="—", start=0.5, end=0.6),
        Word(text="mar", start=1.0, end=1.4),
    ]

    assert [p.hyp_start for p in pair_words(ref, hyp)] == [0.1, 1.0]


def test_pair_words_with_nothing_to_pair() -> None:
    assert pair_words([], [Word(text="ola", start=0, end=1)]) == []
    assert pair_words([RefWord(text="ola", start=0, end=1)], []) == []


def test_timing_errors_are_signed() -> None:
    ref = [RefWord(text="ola", start=1.0, end=1.5)]
    pairs = pair_words(ref, [Word(text="ola", start=0.8, end=1.7)])

    errors = timing_errors(pairs, ref_words=1)

    assert errors.start == [pytest.approx(-0.2)]
    assert errors.end == [pytest.approx(0.2)]


def test_timing_stats_values() -> None:
    errors = TimingErrors(start=[0.1, -0.2, 0.5], end=[0.0, 0.1, -0.3], ref_words=4)

    stats = timing_stats([errors])

    assert stats is not None
    assert stats.words == 3
    assert stats.coverage == pytest.approx(0.75)
    assert stats.start_median == pytest.approx(0.2)
    assert stats.start_mean == pytest.approx(0.8 / 3)
    assert stats.start_within == pytest.approx(2 / 3)
    assert stats.start_bias == pytest.approx(0.4 / 3)
    assert stats.end_median == pytest.approx(0.1)
    assert stats.end_mean == pytest.approx(0.4 / 3)


def test_timing_stats_pools_songs() -> None:
    a = TimingErrors(start=[0.1], end=[0.1], ref_words=1)
    b = TimingErrors(start=[0.4, 0.4], end=[0.0, 0.0], ref_words=4)

    stats = timing_stats([a, b])

    assert stats is not None
    assert stats.words == 3
    assert stats.coverage == pytest.approx(3 / 5)
    assert stats.start_median == pytest.approx(0.4)


def test_timing_stats_none_without_pairs() -> None:
    assert timing_stats([TimingErrors(start=[], end=[], ref_words=10)]) is None
    assert timing_stats([]) is None


def _ref_line(start: float) -> RefLine:
    return RefLine(text="ola", start=start, end=start + 1, words=[])


def _hyp_line(start: float) -> Line:
    return Line(
        id="l", start=start, end=start + 1, words=[Word(text="ola", start=start, end=start + 1)]
    )


def test_line_start_errors_by_index() -> None:
    errors = line_start_errors([_ref_line(1.0), _ref_line(5.0)], [_hyp_line(1.2), _hyp_line(4.5)])

    assert errors == [pytest.approx(0.2), pytest.approx(-0.5)]


def test_line_start_errors_none_when_counts_differ() -> None:
    hyp = [_hyp_line(1.0), _hyp_line(2.0), _hyp_line(3.0)]

    assert line_start_errors([_ref_line(1.0), _ref_line(2.0)], hyp) is None


def test_start_within_wide_uses_half_a_second() -> None:
    errors = TimingErrors(start=[0.4, -0.6], end=[0.0, 0.0], ref_words=2)

    stats = timing_stats([errors])

    assert stats is not None
    assert stats.start_within == 0.0
    assert stats.start_within_wide == pytest.approx(0.5)
