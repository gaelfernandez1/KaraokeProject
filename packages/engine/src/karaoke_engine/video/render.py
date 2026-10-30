"""The MP4 export: a background, the animated lyrics, a title and credits, and the audio.

One ffmpeg run does everything: the background graph (`graph.py`), a dark gradient behind the
lyrics so they read on any picture, the lyrics as ASS (the same layout as the web player, plus
title and credits) drawn by libass, and NVENC (x264 if the GPU cannot). A thumbnail with the title
goes next to the video.
"""

import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from karaoke_contracts import KaraokeDoc, Theme, load_doc
from karaoke_engine.subtitles.ass import (
    ass_color,
    ass_number,
    ass_time,
    escape_text,
    layout_to_ass,
    look_tags,
    style_line,
)
from karaoke_engine.subtitles.layout import SCROLL_ANCHOR, Layout, build_layout
from karaoke_engine.subtitles.metrics import FontMetrics
from karaoke_engine.subtitles.themes import fonts_dir, theme_metrics
from karaoke_engine.video.encode import h264_encoders, run_encoder
from karaoke_engine.video.graph import (
    Background,
    background_graph,
    choose_background,
    dim_factor,
    gradient_colors,
)
from karaoke_engine.video.media import mean_luma

SIZES = {"16:9": (1920, 1080), "9:16": (1080, 1920)}
FPS = 30
VIDEO_QUALITY = 21
THUMBNAIL_WIDTH = 1280
# A title card needs this long before the first line shows; credits, this long after the last.
TITLE_MIN = 4.0
CREDITS_MIN = 4.0
FADE_MS = 400
# The dark gradient behind the lyrics: strongest opacity (0-255).
SCRIM_ALPHA = 170


@dataclass(frozen=True)
class RenderReport:
    out: Path
    seconds: float
    encoder: str
    background: str
    thumbnail: Path | None


def credits_text(package: Path) -> str | None:
    """The first paragraph of the package's LICENSE, on one line (CC songs say whose they are)."""
    licence = package / "LICENSE"
    if not licence.is_file():
        return None
    first = licence.read_text(encoding="utf-8").strip().split("\n\n", 1)[0]
    return " · ".join(line.strip() for line in first.splitlines() if line.strip()) or None


def _text_event(
    text: str,
    start: float,
    end: float,
    x: float,
    y: float,
    px: float,
    color: str,
    theme: Theme,
    metrics: FontMetrics,
    width: int,
    wrap: bool = False,
    fade: int = FADE_MS,
) -> str:
    # A single long line (a title) shrinks to fit; a wrapping one (credits) breaks into rows.
    if not wrap:
        px = min(px, 0.9 * width / max(1e-6, metrics.width(text, 1.0)))
    _, alpha = ass_color(color)
    tags = (
        f"\\an5\\pos({ass_number(x)},{ass_number(y)})\\fad({fade},{fade})"
        f"\\q{0 if wrap else 2}" + look_tags(color, px, theme, metrics) + f"\\1a{alpha}"
    )
    margin = round(0.05 * width)
    return (
        f"Dialogue: 3,{ass_time(round(start * 100))},{ass_time(round(end * 100))},Title,,"
        f"{margin},{margin},0,,{{{tags}}}{escape_text(text)}"
    )


def title_events(
    doc: KaraokeDoc,
    theme: Theme,
    layout: Layout,
    width: int,
    height: int,
    credits: str | None,
    metrics: FontMetrics | None = None,
) -> list[str]:
    """Title and artist before the first line, and credits after the last, when there is time."""
    m = metrics or theme_metrics(theme)
    shift = theme.animation.anticipation
    px = layout.font_px
    x, y = width / 2, height * 0.42
    colors = theme.colors
    events: list[str] = []
    if not layout.groups:
        return events
    first_show = min(g.show for g in layout.groups) - shift
    if first_show >= TITLE_MIN:
        end = first_show - 0.5
        events.append(
            _text_event(doc.title, 0.5, end, x, y, 1.5 * px, colors.sung, theme, m, width)
        )
        if doc.artist:
            events.append(
                _text_event(
                    doc.artist, 0.5, end, x, y + 1.4 * px, 0.9 * px, colors.unsung, theme, m, width
                )
            )
    last_hide = max(g.hide for g in layout.groups) - shift
    if doc.duration - last_hide >= CREDITS_MIN:
        start, end = last_hide + 0.5, doc.duration - 0.3
        names = " · ".join(t for t in (doc.title, doc.artist) if t)
        events.append(_text_event(names, start, end, x, y, 0.9 * px, colors.sung, theme, m, width))
        if credits:
            events.append(
                _text_event(
                    credits,
                    start,
                    end,
                    x,
                    y + 1.3 * px,
                    0.5 * px,
                    colors.unsung,
                    theme,
                    m,
                    width,
                    wrap=True,
                )
            )
    return events


def _scrim_band(layout: Layout, theme: Theme, height: int) -> tuple[int, int, bool]:
    """(top, height, to_the_bottom) of the dark band behind the lyrics."""
    px = layout.font_px
    if layout.mode == "scroll":
        anchor = SCROLL_ANCHOR[theme.layout.position] * height
        top = max(0, round(anchor - 3 * px))
        return top, min(height - top, round(6.5 * px)), False
    tops = [row.y - row.height / 2 for g in layout.groups for row in g.rows] or [height * 0.7]
    top = max(0, round(min(tops) - 1.2 * px))
    if theme.layout.position == "bottom":
        return top, height - top, True
    bottoms = [row.y + row.height / 2 for g in layout.groups for row in g.rows] or [height * 0.9]
    bottom = min(height, round(max(bottoms) + 1.2 * px))
    return top, bottom - top, False


def _write_scrim(path: Path, width: int, height: int, to_the_bottom: bool) -> None:
    shape = "pow(Y/H\\,1.4)" if to_the_bottom else "pow(sin(PI*Y/H)\\,0.7)"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y", "-f", "lavfi",
            "-i", f"color=black:s={width}x{max(2, height)},format=rgba",
            "-vf", f"geq=r=0:g=0:b=0:a='{SCRIM_ALPHA}*{shape}'", "-frames:v", "1", str(path),
        ],
        check=True, capture_output=True,
    )  # fmt: skip


def _background_input(bg: Background, fps: int) -> list[str]:
    if bg.kind == "video":
        return ["-stream_loop", "-1", "-i", str(bg.path)]
    if bg.kind == "image":
        return ["-loop", "1", "-framerate", str(fps), "-i", str(bg.path)]
    return []


def _output_fps(bg: Background) -> int:
    if bg.kind == "video" and bg.fps >= 20:
        return min(FPS, round(bg.fps))
    return FPS


def render(
    package: Path,
    out: Path,
    theme: Theme,
    aspect: str = "16:9",
    background: str = "auto",
    vocals: float = 0.0,
    dim: float | None = None,
    size: tuple[int, int] | None = None,
) -> RenderReport:
    """Exports a package as an MP4 with its animated lyrics; `vocals` is the guide level (0-1)."""
    if aspect not in SIZES:
        raise ValueError(f"aspect must be one of {', '.join(SIZES)}")
    width, height = size or SIZES[aspect]
    # ffmpeg runs in a scratch folder: every path it gets must be absolute.
    package = package.resolve()
    doc = load_doc(package / "karaoke.json")
    metrics = theme_metrics(theme)
    layout = build_layout(doc, theme, width, height, metrics)
    bg = choose_background(package, doc, background)
    if dim is None:
        dim = dim_factor(mean_luma(bg.path)) if bg.path is not None else 1.0
    fps = _output_fps(bg)
    duration = doc.duration
    out = out.resolve()
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as work:
        folder = Path(work)
        extra = [style_line("Title", theme, metrics.ass_font_size(layout.font_px))]
        events = title_events(doc, theme, layout, width, height, credits_text(package), metrics)
        ass = layout_to_ass(layout, doc, theme, metrics, extra, events)
        (folder / "lyrics.ass").write_text(ass, encoding="utf-8")
        (folder / "fonts").symlink_to(fonts_dir())

        inputs = _background_input(bg, fps)
        graph = background_graph(bg, width, height, fps, dim, duration, gradient_colors(theme))
        index = 1 if inputs else 0
        if bg.kind != "gradient":
            top, band, to_the_bottom = _scrim_band(layout, theme, height)
            _write_scrim(folder / "scrim.png", width, band, to_the_bottom)
            inputs += ["-i", "scrim.png"]
            graph += (
                f";[{index}:v]format=yuva420p,loop=loop=-1:size=1[scrim];"
                f"[bg][scrim]overlay=0:{top}:format=yuv420:shortest=0[base]"
            )
            index += 1
        else:
            graph += ";[bg]null[base]"
        graph += ";[base]subtitles=lyrics.ass:fontsdir=fonts,format=yuv420p[v]"

        instrumental = (package / doc.audio.instrumental).resolve()
        inputs += ["-i", str(instrumental)]
        audio_map = f"{index}:a"
        audio_codec = (
            ["-c:a", "copy"] if instrumental.suffix == ".m4a" else ["-c:a", "aac", "-b:a", "192k"]
        )
        if vocals > 0 and doc.audio.vocals:
            inputs += ["-i", str((package / doc.audio.vocals).resolve())]
            graph += (
                f";[{index + 1}:a]volume={ass_number(vocals)}[voc];"
                f"[{index}:a][voc]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]"
            )
            audio_map = "[a]"
            audio_codec = ["-c:a", "aac", "-b:a", "192k"]

        head = [
            "ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph,
            "-map", "[v]", "-map", audio_map, "-r", str(fps),
        ]  # fmt: skip
        tail = [*audio_codec, "-t", f"{duration:.3f}", "-movflags", "+faststart", str(out)]
        encoder = run_encoder(head, h264_encoders(VIDEO_QUALITY), tail, cwd=folder)
        seconds = time.monotonic() - started
        thumb = _thumbnail(doc, theme, bg, layout, width, height, dim, metrics, folder, out)
    return RenderReport(out, seconds, encoder[1], bg.kind, thumb)


def _thumbnail(
    doc: KaraokeDoc,
    theme: Theme,
    bg: Background,
    layout: Layout,
    width: int,
    height: int,
    dim: float,
    metrics: FontMetrics,
    folder: Path,
    video: Path,
) -> Path | None:
    """A still with the title over the background, for YouTube or a library grid."""
    out = video.with_suffix(".jpg")
    x, y = width / 2, height * 0.42
    px = layout.font_px
    # No fade: the still is the very first frame.
    title = _text_event(
        doc.title, 0, 10, x, y, 1.5 * px, theme.colors.sung, theme, metrics, width, fade=0
    )
    events = [title]
    if doc.artist:
        events.append(
            _text_event(
                doc.artist,
                0,
                10,
                x,
                y + 1.4 * px,
                0.9 * px,
                theme.colors.unsung,
                theme,
                metrics,
                width,
                fade=0,
            )
        )
    empty = Layout(
        width=width, height=height, font_px=px, mode=layout.mode, groups=[], countdowns=[], bars=[]
    )
    extra = [style_line("Title", theme, metrics.ass_font_size(px))]
    (folder / "title.ass").write_text(
        layout_to_ass(empty, doc, theme, metrics, extra, events), encoding="utf-8"
    )
    seek = ["-ss", f"{doc.duration / 3:.3f}"] if bg.kind == "video" else []
    inputs = [*seek, *_background_input(bg, FPS)]
    graph = background_graph(bg, width, height, FPS, dim, 1.0, gradient_colors(theme))
    scale = f"scale={THUMBNAIL_WIDTH}:-2" if width >= height else f"scale=-2:{THUMBNAIL_WIDTH}"
    graph += f";[bg]subtitles=title.ass:fontsdir=fonts,{scale}[v]"
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[v]",
         "-frames:v", "1", "-q:v", "3", str(out)],
        cwd=folder, capture_output=True, text=True, check=False,
    )  # fmt: skip
    return out if result.returncode == 0 else None
