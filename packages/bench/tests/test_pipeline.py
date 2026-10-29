from collections.abc import Callable
from pathlib import Path

import pytest

from karaoke_bench.baseline.segment import SegmentPerLine
from karaoke_bench.fakes import EvenSplitAligner, FailingAligner, FixedTranscriber
from karaoke_bench.pipeline import (
    PipelineError,
    StepSpec,
    build_step,
    load_pipeline,
    step_version,
)
from karaoke_engine.steps import Transcript, TranscriptSegment

SMOKE = Path(__file__).resolve().parents[3] / "bench" / "pipelines" / "smoke.toml"
ToneMaker = Callable[..., Path]


def test_load_smoke_pipeline() -> None:
    pipeline = load_pipeline(SMOKE)

    assert pipeline.name == "smoke"
    assert set(pipeline.steps) == {"separator", "transcriber", "segmenter", "aligner"}
    assert pipeline.steps["transcriber"].params == {"text": "ola mar"}
    assert pipeline.required("asr") == ["transcriber", "segmenter", "aligner"]
    assert pipeline.required("lyrics") == ["aligner"]


@pytest.mark.parametrize(
    "body",
    [
        'name = "Bad Name"\n[steps.aligner]\ntarget = "a:B"\n',
        'name = "ok"\n[steps.foo]\ntarget = "a:B"\n',
        'name = "ok"\n[steps.aligner]\ntarget = "no_colon"\n',
    ],
)
def test_bad_name_kind_or_target_rejected(tmp_path: Path, body: str) -> None:
    path = tmp_path / "p.toml"
    path.write_text(body, encoding="utf-8")

    with pytest.raises(PipelineError):
        load_pipeline(path)


def test_check_reports_missing_steps(tmp_path: Path) -> None:
    path = tmp_path / "p.toml"
    path.write_text('name = "only-align"\n[steps.aligner]\ntarget = "a:B"\n', encoding="utf-8")

    pipeline = load_pipeline(path)

    pipeline.check("lyrics")
    with pytest.raises(PipelineError, match="transcriber"):
        pipeline.check("asr")


def test_build_step_instantiates_with_params() -> None:
    step = build_step(
        StepSpec("transcriber", "karaoke_bench.fakes:FixedTranscriber", {"text": "x"})
    )

    assert isinstance(step, FixedTranscriber)
    assert step.text == "x"


def test_build_step_checks_protocol() -> None:
    spec = StepSpec("aligner", "karaoke_bench.fakes:FixedTranscriber", {"text": "x"})

    with pytest.raises(PipelineError, match="Aligner"):
        build_step(spec)


def test_build_step_unknown_target() -> None:
    with pytest.raises(PipelineError):
        build_step(StepSpec("aligner", "karaoke_bench.fakes:Nope", {}))


def test_step_version() -> None:
    assert step_version(StepSpec("aligner", "karaoke_bench.fakes:EvenSplitAligner", {})) == "1"
    assert step_version(StepSpec("aligner", "karaoke_bench.pipeline:StepSpec", {})) == "0"


def test_segment_per_line() -> None:
    transcript = Transcript(
        language="gl",
        segments=(
            TranscriptSegment(0, 1, "  ola   mar "),
            TranscriptSegment(1, 2, " "),
            TranscriptSegment(2, 3, "adeus"),
        ),
    )

    assert SegmentPerLine().segment(transcript) == ["ola mar", "adeus"]


@pytest.mark.usefixtures("ffmpeg")
def test_even_split_aligner(make_tone: ToneMaker) -> None:
    lines = EvenSplitAligner().align(make_tone("a.wav", 4.0), ["a b", "c d"], "gl")

    assert [line.id for line in lines] == ["l1", "l2"]
    assert lines[0].start == pytest.approx(0.0)
    assert lines[0].end == pytest.approx(2.0, abs=0.01)
    assert lines[1].words[1].end == pytest.approx(4.0, abs=0.01)


@pytest.mark.usefixtures("ffmpeg")
def test_failing_aligner_fails_only_on_its_song(make_tone: ToneMaker) -> None:
    aligner = FailingAligner(fail_on="bad")

    assert aligner.align(make_tone("good.wav", 1.0), ["a"], "gl")
    with pytest.raises(RuntimeError):
        aligner.align(make_tone("bad.wav", 1.0), ["a"], "gl")
