"""The `karaoke` command. `render` (video) comes later."""

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from karaoke_contracts import validate_file, validate_package
from karaoke_engine.audio import AudioError, convert_package, probe
from karaoke_engine.demo import synthesize_package_audio
from karaoke_engine.lyrics_lookup import find_lyrics


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
    make.add_argument(
        "--lyrics", type=Path, help="text file with the lyrics, as pasted (default: transcribe)"
    )
    make.add_argument("--lang", default="gl", help="language of the lyrics (default: gl)")
    make.add_argument("--out", type=Path, help="package folder (default: named after the song)")
    make.add_argument("--title")
    make.add_argument("--artist")
    make.add_argument(
        "--overlap-backing",
        action="store_true",
        help="let backing vocals that do not fit in their written place overlap the lead line",
    )
    make.add_argument(
        "--lrclib",
        action="store_true",
        help="look the lyrics up on lrclib.net (sends --title and --artist, both needed)",
    )

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

    if args.lrclib and not (args.title and args.artist):
        print("error: --lrclib needs --title and --artist", file=sys.stderr)
        return 2
    out = args.out or Path(slug(args.title or args.source.stem) or "karaoke")
    try:
        lyrics = args.lyrics.read_text(encoding="utf-8") if args.lyrics else None
        source: Literal["user", "lrclib"] = "user"
        if lyrics is None and args.lrclib:
            found = find_lyrics(args.title, args.artist, probe(args.source).duration)
            if found is None:
                print("LRCLIB has no lyrics for this song; transcribing instead", file=sys.stderr)
            else:
                lyrics, source = found.text, "lrclib"
        doc = make_package(
            args.source, out, args.lang, lyrics, title=args.title, artist=args.artist,
            lyrics_source=source, overlap_backing=args.overlap_backing,
        )  # fmt: skip
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        # RuntimeError covers AudioError, a model that fails to convert, and CUDA out of memory.
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
