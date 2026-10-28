"""The `karaoke-bench` command."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from karaoke_bench.fetch import FetchError, fetch_jamendo, fetch_manifest_set
from karaoke_bench.paths import BenchPaths
from karaoke_bench.pipeline import Mode, PipelineError, load_pipeline
from karaoke_bench.runner import RunOptions, run
from karaoke_bench.sets import SetError


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

    run_cmd = commands.add_parser("run", help="run a pipeline over a set and write a report")
    run_cmd.add_argument("--pipeline", type=Path, required=True, help="pipeline TOML file")
    run_cmd.add_argument("--set", dest="set_name", required=True, help="set name, or set/song")
    run_cmd.add_argument("--mode", choices=["lyrics", "asr", "both"], default="both")
    run_cmd.add_argument("--songs", nargs="+", help="only these song ids")
    run_cmd.add_argument("--no-cache", action="store_true", help="recompute every step")

    args = parser.parse_args(argv)
    paths = BenchPaths(args.bench_dir)
    try:
        if args.command == "fetch":
            return _fetch(paths, args.set_name)
        return _run(paths, args)
    except (FetchError, PipelineError, SetError, OSError) as exc:
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


def _run(paths: BenchPaths, args: argparse.Namespace) -> int:
    pipeline = load_pipeline(args.pipeline)
    modes: list[Mode] = ["lyrics", "asr"] if args.mode == "both" else [args.mode]
    for mode in modes:
        options = RunOptions(pipeline, args.set_name, mode, args.songs, not args.no_cache)
        print(run(options, paths))
    return 0
