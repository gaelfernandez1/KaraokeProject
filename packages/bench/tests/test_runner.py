from collections.abc import Callable
from pathlib import Path

import pytest

from karaoke_bench.paths import BenchPaths
from karaoke_bench.pipeline import Pipeline, load_pipeline
from karaoke_bench.report import render_report
from karaoke_bench.results import load_results
from karaoke_bench.runner import RunOptions, run

SMOKE = Path(__file__).resolve().parents[3] / "bench" / "pipelines" / "smoke.toml"
pytestmark = pytest.mark.usefixtures("ffmpeg")


DemoSongAdder = Callable[[BenchPaths, str], None]


@pytest.fixture
def paths(demo_bench: BenchPaths) -> BenchPaths:
    return demo_bench


def _pipeline(tmp_path: Path, aligner: str, transcriber: str = "") -> Pipeline:
    path = tmp_path / "p.toml"
    path.write_text(
        f'name = "test"\n{transcriber}\n'
        '[steps.segmenter]\ntarget = "karaoke_bench.baseline.segment:SegmentPerLine"\n'
        f"[steps.aligner]\n{aligner}\n",
        encoding="utf-8",
    )
    return load_pipeline(path)


def test_run_lyrics_mode_with_smoke_pipeline(paths: BenchPaths) -> None:
    out = run(RunOptions(load_pipeline(SMOKE), "private", "lyrics"), paths)

    results = load_results(out / "results.json")
    [song] = results.songs
    assert (out / "report.md").is_file()
    assert out.parent == paths.results
    assert song.error is None
    assert song.timing is not None
    assert song.timing.coverage == pytest.approx(1.0)
    assert song.line_start_median is not None
    assert song.wer is None
    assert results.summary["all"].songs == 1
    assert results.summary["gl"].timing is not None
    assert (paths.runs / out.name / "demo.json").is_file()


def test_run_asr_mode_reports_wer_and_language(paths: BenchPaths, tmp_path: Path) -> None:
    pipeline = _pipeline(
        tmp_path,
        'target = "karaoke_bench.fakes:EvenSplitAligner"',
        '[steps.transcriber]\ntarget = "karaoke_bench.fakes:FixedTranscriber"\n'
        'params = { text = "ola mar", language = "es" }',
    )

    out = run(RunOptions(pipeline, "private", "asr"), paths)

    [song] = load_results(out / "results.json").songs
    assert song.wer is not None
    assert song.wer > 0
    assert song.language_reported == "es"
    assert song.language_switch is True
    assert load_results(out / "results.json").summary["all"].language_switches == 1


def test_failing_song_is_reported_not_fatal(
    paths: BenchPaths, tmp_path: Path, add_demo_song: DemoSongAdder
) -> None:
    add_demo_song(paths, "bad-song")
    pipeline = _pipeline(
        tmp_path,
        'target = "karaoke_bench.fakes:FailingAligner"\nparams = { fail_on = "bad-song" }',
    )

    out = run(RunOptions(pipeline, "private", "lyrics"), paths)

    results = load_results(out / "results.json")
    by_id = {song.song_id: song for song in results.songs}
    assert by_id["bad-song"].error is not None
    assert by_id["demo"].timing is not None
    assert results.summary["all"].failed == 1


def test_mismatched_line_count_marks_error(paths: BenchPaths, tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path, 'target = "karaoke_bench.fakes:DropLastLineAligner"')

    out = run(RunOptions(pipeline, "private", "lyrics"), paths)

    [song] = load_results(out / "results.json").songs
    assert song.error is not None
    assert "lines" in song.error
    assert song.timing is None


def test_existing_results_dir_gets_suffix(paths: BenchPaths) -> None:
    options = RunOptions(load_pipeline(SMOKE), "private", "lyrics")

    first = run(options, paths)
    second = run(options, paths)

    assert second.name == f"{first.name}-2"


def test_report_has_fixed_sections(paths: BenchPaths) -> None:
    out = run(RunOptions(load_pipeline(SMOKE), "private", "lyrics"), paths)

    report = render_report(load_results(out / "results.json"))

    for heading in ("## Resumen", "## Etapas", "## Por canción", "## Peores casos", "## Notas"):
        assert heading in report
    assert "demo" in report
    assert report == (out / "report.md").read_text(encoding="utf-8")


def test_songs_filter_and_unknown_song(paths: BenchPaths) -> None:
    with pytest.raises(ValueError, match="nope"):
        run(RunOptions(load_pipeline(SMOKE), "private", "lyrics", songs=["nope"]), paths)


def _set_review(paths: BenchPaths, approved: bool) -> None:
    from karaoke_bench.reference import dump_reference, load_reference

    path = paths.data / "private" / "demo" / "reference.json"
    ref = load_reference(path)
    dump_reference(ref.model_copy(update={"timing": "semiautomatic", "approved": approved}), path)


def test_unvalidated_reference_does_not_score_timing(paths: BenchPaths) -> None:
    _set_review(paths, approved=False)

    out = run(RunOptions(load_pipeline(SMOKE), "private", "lyrics"), paths)

    [song] = load_results(out / "results.json").songs
    assert song.reference_validated is False
    assert song.timing is None
    assert song.line_start_median is None
    assert "sin validar" in (out / "report.md").read_text(encoding="utf-8")


def test_validated_reference_scores_timing(paths: BenchPaths) -> None:
    _set_review(paths, approved=True)

    out = run(RunOptions(load_pipeline(SMOKE), "private", "lyrics"), paths)

    [song] = load_results(out / "results.json").songs
    assert song.reference_validated is True
    assert song.timing is not None
    assert song.scored_share == pytest.approx(1.0)
