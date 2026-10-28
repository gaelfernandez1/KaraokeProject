from pathlib import Path

import pytest

from karaoke_bench.cli import main
from karaoke_bench.paths import BenchPaths


def test_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])

    assert exc.value.code == 0


def test_bench_paths_layout() -> None:
    paths = BenchPaths(Path("/x"))

    assert paths.cache == Path("/x/data/cache")
    assert paths.runs == Path("/x/data/runs")
    assert paths.sets == Path("/x/sets")
    assert paths.results == Path("/x/results")


def test_fetch_empty_manifest_set(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "sets" / "gl").mkdir(parents=True)
    (tmp_path / "sets" / "gl" / "manifest.toml").write_text("songs = []\n", encoding="utf-8")

    code = main(["--bench-dir", str(tmp_path), "fetch", "--set", "gl"])

    assert code == 0
    assert "gl: 0 songs" in capsys.readouterr().out


@pytest.mark.usefixtures("ffmpeg")
def test_run_both_modes_prints_two_reports(
    demo_bench: BenchPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    smoke = Path(__file__).resolve().parents[3] / "bench" / "pipelines" / "smoke.toml"

    code = main(
        ["--bench-dir", str(demo_bench.root), "run", "--pipeline", str(smoke), "--set", "private",
         "--mode", "both"]
    )  # fmt: skip

    printed = capsys.readouterr().out.split()
    assert code == 0
    assert [Path(p).name.rsplit("-", 1)[-1] for p in printed if p.endswith(("lyrics", "asr"))] == [
        "lyrics",
        "asr",
    ]


def test_run_reports_unknown_set(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    smoke = Path(__file__).resolve().parents[3] / "bench" / "pipelines" / "smoke.toml"

    code = main(["--bench-dir", str(tmp_path), "run", "--pipeline", str(smoke), "--set", "nada"])

    assert code == 1
    assert "unknown set" in capsys.readouterr().err


@pytest.mark.usefixtures("ffmpeg")
def test_compare_two_runs(demo_bench: BenchPaths, capsys: pytest.CaptureFixture[str]) -> None:
    smoke = Path(__file__).resolve().parents[3] / "bench" / "pipelines" / "smoke.toml"
    base = ["--bench-dir", str(demo_bench.root)]
    run_args = ["run", "--pipeline", str(smoke), "--set", "private", "--mode", "lyrics"]
    main([*base, *run_args])
    main([*base, *run_args])
    first, second = capsys.readouterr().out.split()
    out = demo_bench.root / "cmp.md"

    code = main([*base, "compare", first, second, "--out", str(out)])

    assert code == 0
    assert out.read_text(encoding="utf-8").startswith("# Comparación")


def _fake_draft_pipeline(tmp_path: Path) -> Path:
    path = tmp_path / "draft.toml"
    path.write_text(
        'name = "draft"\n[steps.aligner]\ntarget = "karaoke_bench.fakes:EvenSplitAligner"\n',
        encoding="utf-8",
    )
    return path


@pytest.mark.usefixtures("ffmpeg")
def test_draft_refuses_to_overwrite_reviewed_reference(
    demo_bench: BenchPaths, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = ["--bench-dir", str(demo_bench.root)]
    pipeline = str(_fake_draft_pipeline(tmp_path))
    ref_path = demo_bench.data / "private" / "demo" / "reference.json"
    before = ref_path.read_text(encoding="utf-8")

    refused = main([*base, "draft", "private/demo", "--pipeline", pipeline])
    forced = main([*base, "draft", "private/demo", "--pipeline", pipeline, "--force"])

    assert refused == 1
    assert "--force" in capsys.readouterr().err
    assert forced == 0
    assert ref_path.read_text(encoding="utf-8") != before
    assert '"status": "draft"' in ref_path.read_text(encoding="utf-8")


@pytest.mark.usefixtures("ffmpeg")
def test_realign_marks_fixed_lines_for_review(demo_bench: BenchPaths, tmp_path: Path) -> None:
    from karaoke_bench.reference import dump_reference, load_reference

    ref_path = demo_bench.data / "private" / "demo" / "reference.json"
    ref = load_reference(ref_path)
    ref.lines[2].status = "wrong"
    dump_reference(ref, ref_path)

    code = main(
        ["--bench-dir", str(demo_bench.root), "realign", "private/demo", "--pipeline",
         str(_fake_draft_pipeline(tmp_path))]
    )  # fmt: skip

    fixed = load_reference(ref_path)
    assert code == 0
    assert fixed.lines[2].status == "draft"
    assert fixed.lines[2].revised


@pytest.mark.usefixtures("ffmpeg")
def test_package_command_builds_a_valid_package(demo_bench: BenchPaths, tmp_path: Path) -> None:
    from karaoke_contracts import validate_package

    pipeline = tmp_path / "sep.toml"
    pipeline.write_text(
        'name = "sep"\n[steps.separator]\ntarget = "karaoke_bench.fakes:PassthroughSeparator"\n',
        encoding="utf-8",
    )
    out = tmp_path / "pkg"

    code = main(
        ["--bench-dir", str(demo_bench.root), "package", "private/demo", "--pipeline",
         str(pipeline), "--out", str(out)]
    )  # fmt: skip

    assert code == 0
    assert validate_package(out) == []
    credits = (out / "LICENSE").read_text(encoding="utf-8")
    assert "Demo" in credits
    # Says where the audio comes from, so anyone can rebuild it with the same command.
    assert "karaoke-bench package private/demo" in credits


def test_package_credits_quote_the_song_id() -> None:
    import shlex

    from karaoke_bench.cli import _credits
    from karaoke_bench.sets import Song

    song = Song(
        "jamendo", "Mère_nature_-_Law'", "Mère nature", "Law'", "fr", Path("a.mp3"), None, None
    )

    credits = _credits(song, {}, Path("bench/pipelines/base-turbo.toml"))

    command = next(line for line in credits.splitlines() if "karaoke-bench package" in line)
    assert shlex.split(command)[4] == "jamendo/Mère_nature_-_Law'"
