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
