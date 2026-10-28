"""The `karaoke-bench` command."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from karaoke_bench.fetch import FetchError, fetch_jamendo, fetch_manifest_set
from karaoke_bench.paths import BenchPaths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="karaoke-bench", description="Measure the karaoke engine on song sets."
    )
    parser.add_argument(
        "--bench-dir", type=Path, default=Path("bench"), help="bench folder (default: bench)"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    fetch = commands.add_parser("fetch", help="download a song set into bench/data")
    fetch.add_argument("--set", dest="set_name", default="all", help="jamendo, gl or all")

    args = parser.parse_args(argv)
    paths = BenchPaths(args.bench_dir)
    try:
        return _fetch(paths, args.set_name)
    except (FetchError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _fetch(paths: BenchPaths, set_name: str) -> int:
    manifest_sets = sorted(p.parent.name for p in paths.sets.glob("*/manifest.toml"))
    if set_name not in ("all", "jamendo", *manifest_sets):
        print(f"error: unknown set '{set_name}'", file=sys.stderr)
        return 2
    if set_name in ("all", "jamendo"):
        print(f"jamendo: {len(fetch_jamendo(paths))} songs")
    for name in manifest_sets:
        if set_name in ("all", name):
            print(f"{name}: {len(fetch_manifest_set(name, paths))} songs")
    return 0
