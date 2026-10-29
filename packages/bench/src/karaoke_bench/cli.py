"""The `karaoke-bench` command."""

import argparse
import shlex
import sys
from collections.abc import Sequence
from pathlib import Path

from karaoke_bench.audio import AudioError, duration
from karaoke_bench.compare import compare_runs
from karaoke_bench.drafting import (
    DraftError,
    draft_reference,
    realign_reference,
    reference_path,
)
from karaoke_bench.fetch import FetchError, fetch_jamendo, fetch_manifest_set
from karaoke_bench.package import PackageError, build_package
from karaoke_bench.paths import BenchPaths
from karaoke_bench.pipeline import Mode, PipelineError, load_pipeline
from karaoke_bench.reference import dump_reference, load_reference
from karaoke_bench.results import load_results
from karaoke_bench.runner import RunOptions, run
from karaoke_bench.sets import SetError, Song, load_set
from karaoke_bench.srt import parse_srt, reference_from_srt
from karaoke_bench.textnorm import lyrics_lines


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

    compare = commands.add_parser("compare", help="compare two runs (folders or results.json)")
    compare.add_argument("run_a", type=Path)
    compare.add_argument("run_b", type=Path)
    compare.add_argument("--out", type=Path, help="write the comparison here instead of stdout")

    draft = commands.add_parser("draft", help="draft a song's reference timings with an aligner")
    draft.add_argument("song", help="set/song, e.g. gl/some-song")
    draft.add_argument("--pipeline", type=Path, required=True)
    draft.add_argument("--force", action="store_true", help="overwrite a reviewed reference")

    realign = commands.add_parser("realign", help="realign the lines flagged wrong in a review")
    realign.add_argument("song", help="set/song")
    realign.add_argument("--pipeline", type=Path, required=True)

    review = commands.add_parser("review", help="open the review page for a song's reference")
    review.add_argument("song", help="set/song")
    review.add_argument("--port", type=int, default=8765)
    review.add_argument("--pipeline", type=Path, help="pipeline whose separator gives the vocals")

    package = commands.add_parser("package", help="build a karaoke package from a reference")
    package.add_argument("song", help="set/song")
    package.add_argument(
        "--pipeline", type=Path, required=True, help="its separator makes the stems"
    )
    package.add_argument("--out", type=Path, required=True)

    import_srt = commands.add_parser(
        "import-srt", help="make a private song's reference from word-timed subtitles"
    )
    import_srt.add_argument("song", help="private/song")
    import_srt.add_argument("srt", type=Path, help="subtitle file with one entry per word")

    args = parser.parse_args(argv)
    paths = BenchPaths(args.bench_dir)
    try:
        if args.command == "fetch":
            return _fetch(paths, args.set_name)
        if args.command == "compare":
            return _compare(args.run_a, args.run_b, args.out)
        if args.command == "draft":
            return _draft(paths, _one_song(args.song, paths), args.pipeline, args.force)
        if args.command == "realign":
            return _realign(paths, _one_song(args.song, paths), args.pipeline)
        if args.command == "package":
            return _package(paths, _one_song(args.song, paths), args.pipeline, args.out)
        if args.command == "import-srt":
            return _import_srt(paths, args.song, args.srt)
        if args.command == "review":
            return _review(paths, _one_song(args.song, paths), args.port, args.pipeline)
        return _run(paths, args)
    except (
        FetchError,
        PipelineError,
        SetError,
        DraftError,
        PackageError,
        AudioError,
        OSError,
    ) as exc:
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


def _compare(run_a: Path, run_b: Path, out: Path | None) -> int:
    text = compare_runs(load_results(run_a), load_results(run_b))
    if out is None:
        print(text, end="")
    else:
        out.write_text(text, encoding="utf-8")
    return 0


def _one_song(name: str, paths: BenchPaths) -> Song:
    if "/" not in name:
        raise SetError(f"give the song as set/song, got '{name}'")
    return load_set(name, paths)[0]


def _draft(paths: BenchPaths, song: Song, pipeline_path: Path, force: bool) -> int:
    target = reference_path(song, paths)
    if target.is_file() and not force:
        reviewed = [line for line in load_reference(target).lines if line.status != "draft"]
        if reviewed:
            print(
                f"error: {target} has {len(reviewed)} reviewed lines; use --force to replace it",
                file=sys.stderr,
            )
            return 1
    dump_reference(draft_reference(song, load_pipeline(pipeline_path), paths), target)
    print(target)
    return 0


def _realign(paths: BenchPaths, song: Song, pipeline_path: Path) -> int:
    target = reference_path(song, paths)
    ref = load_reference(target)
    fixed = realign_reference(song, ref, load_pipeline(pipeline_path), paths)
    dump_reference(fixed, target)
    changed = sum(
        line.revised and not old.revised for line, old in zip(fixed.lines, ref.lines, strict=True)
    )
    print(f"{target}: {changed} lines realigned, listen to them again")
    return 0


def _review(paths: BenchPaths, song: Song, port: int, pipeline_path: Path | None) -> int:
    from karaoke_bench.drafting import separated_vocals
    from karaoke_bench.review.server import make_server

    target = reference_path(song, paths)
    if not target.is_file():
        raise DraftError(f"{target} does not exist; run `karaoke-bench draft` first")
    vocals = separated_vocals(song, load_pipeline(pipeline_path), paths) if pipeline_path else None
    server = make_server(song, target, vocals, port)
    print(f"Review page: http://localhost:{server.server_address[1]}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _package(paths: BenchPaths, song: Song, pipeline_path: Path, out: Path) -> int:
    from karaoke_bench.drafting import separated_stems
    from karaoke_bench.sets import read_meta

    ref = song.load_reference()
    if ref is None:
        raise DraftError(f"{song.song_id} has no reference")
    meta_path = song.audio.parent / "meta.toml"
    meta = read_meta(meta_path) if meta_path.is_file() else {}
    credits = _credits(song, meta, pipeline_path)
    stems = separated_stems(song, load_pipeline(pipeline_path), paths)
    doc = build_package(song, ref, stems, out, credits)
    print(f"{out}: {len(doc.lines)} lines")
    return 0


def _import_srt(paths: BenchPaths, name: str, srt: Path) -> int:
    if not name.startswith("private/"):
        raise SetError(
            f"subtitle timings are approximate: only private songs take them, not {name}"
        )
    song = _one_song(name, paths)
    if song.lyrics is None:
        raise SetError(f"{song.song_id} needs a lyrics.txt with the lines of the song")
    try:
        entries = parse_srt(srt.read_text(encoding="utf-8"))
        ref = reference_from_srt(
            entries, lyrics_lines(song.lyrics_text() or ""), song.song_id, song.language,
            duration(song.audio),
        )  # fmt: skip
    except ValueError as exc:
        raise SetError(f"{srt}: {exc}") from exc
    target = song.audio.parent / "reference.json"
    dump_reference(ref, target)
    print(f"{target}: {len(ref.lines)} lines, {len(ref.scored_words())} words")
    return 0


def _credits(song: Song, meta: dict[str, str], pipeline_path: Path) -> str:
    lines = [
        f"Song: {song.title}" + (f" by {song.artist}" if song.artist else ""),
        f"Licence: {meta.get('license', 'see source')}",
        f"Source: {meta.get('source', '-')}",
    ]
    if song.set_name == "jamendo":
        lines += [
            "",
            "Word timings: JamendoLyrics MultiLang (Durand, Stoller and Ewert, ICASSP 2023).",
            "Lyrics text and line timings: Jam-ALT (Cífka et al., 2023 and 2025).",
        ]
    lines += [
        "",
        "The audio (vocals.wav, instrumental.wav) is never versioned. To rebuild it:",
        f"  uv run karaoke-bench package {shlex.quote(f'{song.set_name}/{song.song_id}')}"
        f" --pipeline {shlex.quote(str(pipeline_path))} --out <this folder>",
    ]
    return "\n".join(lines) + "\n"
