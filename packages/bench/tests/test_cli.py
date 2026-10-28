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
