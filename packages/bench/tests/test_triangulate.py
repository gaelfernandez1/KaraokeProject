import pytest

from karaoke_bench.paths import BenchPaths
from karaoke_bench.reference import Reference, RefLine, RefWord
from karaoke_bench.triangulate import triangulate
from karaoke_contracts import Line, Word


def _ref() -> Reference:
    def line(words: list[tuple[str, float]], status: str = "draft") -> RefLine:
        refs = [RefWord(text=t, start=s, end=s + 0.3) for t, s in words]
        return RefLine.model_validate(
            {"text": " ".join(t for t, _ in words), "start": refs[0].start, "end": refs[-1].end,
             "words": [r.model_dump() for r in refs], "status": status}
        )  # fmt: skip

    lines = [line([("ola", 1.0), ("mar", 1.5)]), line([("adeus", 5.0)])]
    return Reference(song_id="s", language="gl", duration=10.0, timing="semiautomatic", lines=lines)


def _run(starts: list[float]) -> list[Line]:
    texts = ["ola", "mar", "adeus"]
    words = [Word(text=t, start=s, end=s + 0.3) for t, s in zip(texts, starts, strict=True)]
    return [
        Line(id="l1", start=words[0].start, end=words[1].end, words=words[:2]),
        Line(id="l2", start=words[2].start, end=words[2].end, words=words[2:]),
    ]


def test_agreeing_runs_mark_line_ok_with_median_times() -> None:
    runs = [_run([1.0, 1.5, 5.0]), _run([1.1, 1.6, 5.1]), _run([1.05, 1.55, 5.3])]

    ref = triangulate(_ref(), runs, tolerance=0.15)

    first = ref.lines[0]
    assert first.status == "ok"
    assert [w.start for w in first.words] == pytest.approx([1.05, 1.55])
    assert "3" in (first.note or "")


def test_one_disagreeing_run_makes_line_unsure() -> None:
    runs = [_run([1.0, 1.5, 5.0]), _run([1.1, 1.6, 5.1]), _run([1.05, 1.55, 7.0])]

    ref = triangulate(_ref(), runs, tolerance=0.15)

    assert ref.lines[1].status == "unsure"
    assert ref.lines[1].words[0].start == 5.0


def test_a_run_missing_the_line_makes_it_unsure() -> None:
    short = _run([1.0, 1.5, 5.0])[:1]

    ref = triangulate(_ref(), [_run([1.0, 1.5, 5.0]), short], tolerance=0.15)

    assert ref.lines[1].status == "unsure"


def test_song_approved_only_above_share() -> None:
    agree = [_run([1.0, 1.5, 5.0]), _run([1.0, 1.5, 5.0])]
    split = [_run([1.0, 1.5, 5.0]), _run([2.0, 2.5, 5.0])]

    assert triangulate(_ref(), agree, tolerance=0.15).approved
    assert not triangulate(_ref(), split, tolerance=0.15).approved


def test_reviewed_lines_are_left_alone() -> None:
    ref = _ref()
    ref.lines[0].status = "wrong"

    out = triangulate(ref, [_run([3.0, 3.5, 5.0]), _run([3.0, 3.5, 5.0])], tolerance=0.15)

    assert out.lines[0].status == "wrong"
    assert out.lines[0].words[0].start == 1.0


@pytest.mark.usefixtures("ffmpeg")
def test_triangulate_command_updates_the_reference(demo_bench: BenchPaths) -> None:
    from pathlib import Path

    from karaoke_bench.cli import main
    from karaoke_bench.reference import dump_reference, load_reference

    path = demo_bench.data / "private" / "demo" / "reference.json"
    ref = load_reference(path)
    drafts = [line.model_copy(update={"status": "draft"}) for line in ref.lines]
    dump_reference(ref.model_copy(update={"timing": "semiautomatic", "lines": drafts}), path)
    smoke = Path(__file__).resolve().parents[3] / "bench" / "pipelines" / "smoke.toml"

    code = main(["--bench-dir", str(demo_bench.root), "triangulate", "private/demo",
                 "--pipelines", str(smoke), str(smoke)])  # fmt: skip

    assert code == 0
    assert all(line.status == "ok" for line in load_reference(path).lines)
