"""The `karaoke-bench` command."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from karaoke_bench.paths import BenchPaths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="karaoke-bench", description="Measure the karaoke engine on song sets."
    )
    parser.add_argument(
        "--bench-dir", type=Path, default=Path("bench"), help="bench folder (default: bench)"
    )
    parser.add_subparsers(dest="command", required=True)

    args = parser.parse_args(argv)
    BenchPaths(args.bench_dir)
    return 0
