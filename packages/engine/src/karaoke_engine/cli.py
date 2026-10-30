"""The `karaoke` command. `render` (video) comes later."""

import argparse
import re
import subprocess
import sys
import time
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

    subtitles = commands.add_parser(
        "subtitles", help="write the animated lyrics of a package as ASS subtitles for a video"
    )
    subtitles.add_argument("package", type=Path)
    subtitles.add_argument("--theme", default="clasico", help="theme id or theme.json path")
    subtitles.add_argument("--size", default="1920x1080", help="video size, e.g. 1080x1920")
    subtitles.add_argument("-o", "--out", type=Path, help="default: lyrics-<theme>-<size>.ass")

    preview = commands.add_parser(
        "preview", help="a quick MP4 of a package's lyrics on a plain background, with its audio"
    )
    preview.add_argument("package", type=Path)
    preview.add_argument("--theme", default="clasico", help="theme id or theme.json path")
    preview.add_argument("--size", default="1920x1080", help="video size, e.g. 1080x1920")
    preview.add_argument("--start", type=float, help="seconds into the song")
    preview.add_argument("--duration", type=float, help="seconds to render")
    preview.add_argument("-o", "--out", type=Path, help="default: preview-<theme>-<size>.mp4")

    render = commands.add_parser(
        "render", help="export a package as an MP4 with its animated lyrics, title and credits"
    )
    render.add_argument("package", type=Path)
    render.add_argument("--theme", default="clasico", help="theme id or theme.json path")
    render.add_argument("--aspect", default="16:9", choices=["16:9", "9:16"])
    render.add_argument("--size", help="instead of 1920x1080 or 1080x1920, e.g. 1280x720")
    render.add_argument(
        "--background",
        default="auto",
        help="auto, video, cover, gradient or a picture or video file",
    )
    render.add_argument("--vocals", type=float, default=0.0, help="guide vocals level, 0 to 1")
    render.add_argument(
        "--dim", type=float, help="background brightness 0.3-1 (default: by its light)"
    )
    render.add_argument("-o", "--out", type=Path, help="default: <package>-16x9.mp4 (and .jpg)")

    background = commands.add_parser(
        "background", help="give a package a background video (and cover) or a cover picture"
    )
    background.add_argument("package", type=Path)
    background.add_argument(
        "source", type=Path, help="a video, or a song file with cover art, or a picture"
    )

    args = parser.parse_args(argv)
    if args.command == "render":
        return _render(args)
    if args.command == "background":
        return _background(args.package, args.source)
    if args.command in ("subtitles", "preview"):
        return _subtitles(args)
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


_STEPS = {
    "decode": "reading the song",
    "separate": "separating the voice",
    "transcribe": "transcribing the voice",
    "align": "placing the lyrics",
    "encode": "writing the package",
}


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
        started = time.monotonic()

        def progress(step: str) -> None:
            print(f"[{time.monotonic() - started:5.0f} s] {_STEPS[step]}", file=sys.stderr)

        doc = make_package(
            args.source, out, args.lang, lyrics, title=args.title, artist=args.artist,
            lyrics_source=source, overlap_backing=args.overlap_backing, progress=progress,
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


def _subtitles(args: argparse.Namespace) -> int:
    from karaoke_contracts import load_doc
    from karaoke_engine.subtitles.ass import build_ass
    from karaoke_engine.subtitles.preview import render_preview
    from karaoke_engine.subtitles.themes import load_theme

    size = re.fullmatch(r"(\d{2,5})x(\d{2,5})", args.size)
    if size is None:
        print(f"error: --size must look like 1920x1080, not {args.size!r}", file=sys.stderr)
        return 2
    width, height = int(size[1]), int(size[2])
    try:
        theme = load_theme(args.theme)
        if args.command == "preview":
            out = args.out or Path(f"preview-{theme.id}-{args.size}.mp4")
            render_preview(args.package, theme, width, height, out, args.start, args.duration)
        else:
            doc = load_doc(args.package / "karaoke.json")
            out = args.out or args.package / f"lyrics-{theme.id}-{args.size}.ass"
            out.write_text(build_ass(doc, theme, width, height), encoding="utf-8")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Written {out}")
    return 0


def _render(args: argparse.Namespace) -> int:
    from karaoke_engine.subtitles.themes import load_theme
    from karaoke_engine.video.render import render

    size = None
    if args.size:
        match = re.fullmatch(r"(\d{2,5})x(\d{2,5})", args.size)
        if match is None:
            print(f"error: --size must look like 1280x720, not {args.size!r}", file=sys.stderr)
            return 2
        size = (int(match[1]), int(match[2]))
    out = args.out or Path(f"{args.package.resolve().name}-{args.aspect.replace(':', 'x')}.mp4")
    try:
        report = render(
            args.package, out, load_theme(args.theme), aspect=args.aspect,
            background=args.background, vocals=args.vocals, dim=args.dim, size=size,
        )  # fmt: skip
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"{report.out}: {report.background} background, {report.encoder}, {report.seconds:.0f} s")
    return 0


def _background(package: Path, source: Path) -> int:
    from karaoke_engine.video.media import add_background

    try:
        doc = add_background(package, source)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"{package}: background {doc.video.background if doc.video else None}, cover {doc.cover}")
    return 0


def _validate(path: Path) -> int:
    issues = validate_package(path) if path.is_dir() else validate_file(path)
    for issue in issues:
        print(f"{issue.path}: {issue.message}")
    if issues:
        return 1
    print("OK")
    return 0
