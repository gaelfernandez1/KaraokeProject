"""The `karaoke` command. `render` (video) comes later."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from karaoke_contracts import validate_file, validate_package
from karaoke_engine.audio import AudioError, convert_package
from karaoke_engine.demo import synthesize_package_audio


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="karaoke", description="Karaoke generator tools.")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser(
        "validate", help="check a karaoke package folder (or just its karaoke.json)"
    )
    validate.add_argument("path", type=Path)

    demo = commands.add_parser(
        "demo", help="write synthetic audio for a package that follows its lyric timings"
    )
    demo.add_argument("package", type=Path)

    audio = commands.add_parser(
        "audio", help="level a package's stems to -14 LUFS and write them as m4a for browsers"
    )
    audio.add_argument("package", type=Path)
    audio.add_argument("--mix", type=Path, help="the original song (default: the stems summed)")

    make = commands.add_parser("make", help="make a karaoke package from a song and its lyrics")
    make.add_argument("source", type=Path, help="the song: any audio or video file ffmpeg reads")
    make.add_argument("--lyrics", type=Path, help="text file with the lyrics, as pasted")
    make.add_argument("--lang", default="gl", help="language of the lyrics (default: gl)")
    make.add_argument("--out", type=Path, help="package folder (default: named after the song)")
    make.add_argument("--title")
    make.add_argument("--artist")

    args = parser.parse_args(argv)
    if args.command == "make":
        return _make(args)
    if args.command == "validate":
        return _validate(args.path)
    if args.command == "audio":
        return _audio(args.package, args.mix)
    try:
        synthesize_package_audio(args.package)
    except (OSError, ValueError) as exc:  # ValueError covers pydantic's ValidationError
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Synthetic audio written to {args.package}")
    return 0


def _make(args: argparse.Namespace) -> int:
    from karaoke_engine.make import make_package, slug

    if args.lyrics is None:
        print("error: give the lyrics with --lyrics letra.txt", file=sys.stderr)
        return 2
    out = args.out or Path(slug(args.title or args.source.stem) or "karaoke")
    try:
        lyrics = args.lyrics.read_text(encoding="utf-8")
        doc = make_package(
            args.source, out, args.lang, lyrics, title=args.title, artist=args.artist
        )
    except (OSError, ValueError, AudioError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    words = sum(len(line.words) for line in doc.lines)
    print(f"{out}: {len(doc.lines)} lines, {words} words, {doc.duration:.0f} s")
    return 0


def _audio(package: Path, mix: Path | None) -> int:
    try:
        refs = convert_package(package, mix)
    except (OSError, ValueError, AudioError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"{package}: {refs.instrumental}, {refs.vocals} at {refs.loudness_lufs} LUFS")
    return 0


def _validate(path: Path) -> int:
    issues = validate_package(path) if path.is_dir() else validate_file(path)
    for issue in issues:
        print(f"{issue.path}: {issue.message}")
    if issues:
        return 1
    print("OK")
    return 0
