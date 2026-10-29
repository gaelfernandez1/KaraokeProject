from karaoke_bench.compare import compare_runs
from karaoke_bench.metrics import TimingStats
from karaoke_bench.results import GroupSummary, RunResults, SongResult


def _timing(median: float) -> TimingStats:
    return TimingStats(
        words=10, coverage=1.0, start_median=median, start_mean=median, start_within=0.9,
        end_median=median, end_mean=median, start_bias=0.0,
    )  # fmt: skip


def _results(
    median: float, wer: float, normalization: int = 1, songs: dict[str, float] | None = None
) -> RunResults:
    group = GroupSummary(
        songs=1, failed=0, wer=wer, cer=wer / 2, timing=_timing(median), line_start_median=None,
        language_switches=0, rtf_median={"aligner": 0.1}, est_seconds_4min=24.0,
    )  # fmt: skip
    song_results = [
        SongResult(
            song_id=song_id,
            set_name="gl",
            language="gl",
            duration=200.0,
            mode="lyrics",
            steps={},
            wer=wer,
            timing=_timing(value),
        )
        for song_id, value in (songs or {"a": median}).items()
    ]
    return RunResults(
        bench_version="0.1.0", normalization_version=normalization, created="2026-10-28",
        git_commit=None, pipeline={"name": "p", "steps": {}}, set_name="gl", mode="lyrics",
        environment={}, reference_kind={}, stages={}, songs=song_results,
        summary={"all": group, "gl": group},
    )  # fmt: skip


def test_compare_shows_deltas() -> None:
    report = compare_runs(_results(0.2, 0.30), _results(0.3, 0.25))

    assert "+0.100" in report
    assert "-5.0" in report
    assert "## gl" in report


def test_compare_warns_on_normalization_change() -> None:
    report = compare_runs(_results(0.2, 0.3), _results(0.2, 0.3, normalization=2))

    assert "normalización" in report.lower()
    assert "⚠" in report


def test_compare_lists_regressions() -> None:
    before = _results(0.2, 0.3, songs={"a": 0.2, "b": 0.2})
    after = _results(0.2, 0.3, songs={"a": 0.21, "b": 0.4})

    report = compare_runs(before, after)

    regressions = report.split("## Canciones que empeoran", 1)[1]
    assert "b" in regressions
    assert "- a" not in regressions
