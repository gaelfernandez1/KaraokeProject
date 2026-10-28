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
