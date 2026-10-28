from pathlib import Path

import pytest

from karaoke_bench.drafting import draft_reference, realign_reference, realign_windows
from karaoke_bench.paths import BenchPaths
from karaoke_bench.pipeline import Pipeline, load_pipeline
from karaoke_bench.reference import Reference, RefLine, RefWord
from karaoke_bench.sets import load_set


def _ref(statuses: list[str], anchors: dict[int, float] | None = None) -> Reference:
    lines = []
    for i, status in enumerate(statuses):
        start = 5.0 * i + 1.0
        lines.append(
            RefLine.model_validate(
                {
                    "text": f"line {i}",
                    "start": start,
                    "end": start + 3.0,
                    "words": [RefWord(text=f"w{i}", start=start, end=start + 3.0)],
                    "status": status,
                    "anchor": (anchors or {}).get(i),
                }
            )
        )
    return Reference(song_id="s", language="gl", duration=30.0, timing="semiautomatic", lines=lines)


def test_realign_windows_uses_anchor_and_neighbours() -> None:
    ref = _ref(["ok", "wrong", "wrong", "ok", "ok"], anchors={1: 10.0})

    assert realign_windows(ref) == [(1, 3, 9.8, 16.0)]


def test_realign_windows_without_anchor_use_previous_end() -> None:
    ref = _ref(["ok", "wrong", "ok"])

    assert realign_windows(ref) == [(1, 2, 4.0, 11.0)]


def test_realign_windows_next_anchor_closes_the_window() -> None:
    ref = _ref(["wrong", "ok"], anchors={1: 5.5})

    assert realign_windows(ref) == [(0, 1, 0.0, 5.5)]


def test_realign_windows_at_song_edges() -> None:
    ref = _ref(["wrong", "ok", "draft", "unsure", "wrong"])

    assert realign_windows(ref) == [(0, 1, 0.0, 6.0), (4, 5, 19.0, 30.0)]


def _pipeline(tmp_path: Path) -> Pipeline:
    path = tmp_path / "draft.toml"
    path.write_text(
        'name = "draft"\n[steps.aligner]\ntarget = "karaoke_bench.fakes:EvenSplitAligner"\n',
        encoding="utf-8",
    )
    return load_pipeline(path)


@pytest.mark.usefixtures("ffmpeg")
def test_draft_reference_with_fake_aligner(demo_bench: BenchPaths, tmp_path: Path) -> None:
    [song] = load_set("private/demo", demo_bench)

    ref = draft_reference(song, _pipeline(tmp_path), demo_bench)

    assert ref.timing == "semiautomatic"
    assert not ref.approved
    assert all(line.status == "draft" for line in ref.lines)
    assert ref.lines[0].text == song.load_reference().lines[0].text  # type: ignore[union-attr]
    assert ref.duration == pytest.approx(32.0, abs=0.05)


@pytest.mark.usefixtures("ffmpeg")
def test_realign_with_fake_aligner_shifts_times(demo_bench: BenchPaths, tmp_path: Path) -> None:
    [song] = load_set("private/demo", demo_bench)
    ref = song.load_reference()
    assert ref is not None
    ref.lines[1].status = "wrong"
    ref.lines[1].note = "entra tarde"
    ref.lines[2].status = "wrong"
    [(_, _, start, end)] = realign_windows(ref)

    fixed = realign_reference(song, ref, _pipeline(tmp_path), demo_bench)

    for line in fixed.lines[1:3]:
        assert line.status == "draft"
        assert line.revised
        assert line.anchor is None
        assert all(start - 0.01 <= w.start and w.end <= end + 0.01 for w in line.words)
    assert fixed.lines[1].note == "entra tarde"
    assert fixed.lines[0] == ref.lines[0]
    assert fixed.lines[3] == ref.lines[3]
