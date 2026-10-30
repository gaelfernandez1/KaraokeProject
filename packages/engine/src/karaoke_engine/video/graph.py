"""The background of the exported video as an ffmpeg filter graph that ends in `[bg]`.

A picture whose shape matches the video fills it (scaled and cropped). Any other shape is shown
whole, over a blurred, darker, enlarged copy of itself that fills the rest: never stretched, never
cut. In a vertical video it sits high, leaving the bottom for the lyrics. Bright pictures are
darkened so white lyrics stay readable.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from karaoke_contracts import KaraokeDoc, Theme
from karaoke_engine.video.media import IMAGES, probe_video

# Shapes this close count as the same (16:9 against 1.85:1, say): cover and crop.
SAME_SHAPE = 0.08
# The blurred fill is made this many times smaller (blur is cheap there and looks the same).
FILL_SHRINK = 6
# Generated gradients are drawn this many times smaller and scaled up.
GRADIENT_SHRINK = 12
# Where the middle of a picture goes in a vertical video (fraction of the height).
PORTRAIT_CENTER = 0.36
BASE_COLOR = "#141428"


@dataclass(frozen=True)
class Background:
    kind: Literal["video", "image", "gradient"]
    path: Path | None = None
    width: int = 0
    height: int = 0
    fps: float = 0.0


def dim_factor(mean_luma: float) -> float:
    """How much to multiply the brightness of a picture whose average brightness is `mean_luma`."""
    if mean_luma <= 0:
        return 1.0
    return min(1.0, max(0.6, 0.5 / mean_luma))


def _num(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _dark(color: str, amount: float = 0.3) -> str:
    channels = [round(int(color[i : i + 2], 16) * amount) for i in (1, 3, 5)]
    return "0x" + "".join(f"{c:02X}" for c in channels)


def gradient_colors(theme: Theme) -> list[str]:
    """A dark base and dark versions of the theme's sung colours, for generated backgrounds."""
    second = theme.colors.singers[1] if len(theme.colors.singers) > 1 else theme.colors.unsung
    return ["0x" + BASE_COLOR[1:], _dark(theme.colors.sung), _dark(second)]


def background_graph(
    bg: Background,
    width: int,
    height: int,
    fps: int,
    dim: float,
    duration: float,
    colors: list[str] | None = None,
) -> str:
    """Filters from input 0 (or from nothing, for a gradient) to a `[bg]` of `width` by `height`."""
    if bg.kind == "gradient":
        c0, c1, c2 = colors or ["0x" + BASE_COLOR[1:]] * 3
        return (
            f"gradients=s={width // GRADIENT_SHRINK}x{height // GRADIENT_SHRINK}:r={fps}"
            f":d={duration:.3f}:c0={c0}:c1={c1}:c2={c2}:nb_colors=3:speed=0.004:type=linear"
            f":seed=1,scale={width}:{height}:flags=bicubic,format=yuv420p[bg]"
        )
    lut = f",lutyuv=y=val*{_num(dim)}" if dim < 1 else ""
    rate = f"fps={fps}," if bg.fps > fps else ""
    source = bg.width / bg.height if bg.height else width / height
    if abs(source / (width / height) - 1) < SAME_SHAPE:
        return (
            f"[0:v]{rate}scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}{lut}[bg]"
        )
    # Even sizes (for yuv420) and never so small that the blur does not fit.
    small_w = max(32, width // FILL_SHRINK // 2 * 2)
    small_h = max(32, height // FILL_SHRINK // 2 * 2)
    blur = min(8, min(small_w, small_h) // 4)
    zoom = (
        f",zoompan=z='min(1.15\\,1+0.0002*on)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'"
        f":d=1:s={small_w}x{small_h}:fps={fps}"
        if bg.kind == "image"
        else ""
    )
    y = f"max(0\\,H*{PORTRAIT_CENTER}-h/2)" if height > width else "(H-h)/2"
    return (
        f"[0:v]{rate}split[a][b];"
        f"[b]scale={small_w}:{small_h}:force_original_aspect_ratio=increase:flags=fast_bilinear,"
        f"crop={small_w}:{small_h}{zoom},boxblur={blur}:2,lutyuv=y=val*{_num(dim * 0.75)},"
        f"scale={width}:{height}:flags=fast_bilinear[fill];"
        f"[a]scale={width}:{height}:force_original_aspect_ratio=decrease:flags=bicubic{lut}[fit];"
        f"[fill][fit]overlay=(W-w)/2:{y}:format=yuv420[bg]"
    )


def _picture(path: Path, kind: Literal["video", "image"]) -> Background:
    info = probe_video(path)
    if info is None:
        raise ValueError(f"{path}: no picture in it")
    return Background(kind, path, info.width, info.height, info.fps if kind == "video" else 0.0)


def choose_background(package: Path, doc: KaraokeDoc, choice: str = "auto") -> Background:
    """`auto` (the package's video, else its cover, else a gradient), `video`, `cover`,
    `gradient`, or the path of a video or picture."""
    video = doc.video.background if doc.video else None
    if choice == "gradient" or (choice == "auto" and video is None and doc.cover is None):
        return Background("gradient")
    if choice == "video" or (choice == "auto" and video is not None):
        if video is None:
            raise ValueError("the package has no background video")
        return _picture(package / video, "video")
    if choice in ("cover", "auto"):
        if doc.cover is None:
            raise ValueError("the package has no cover")
        return _picture(package / doc.cover, "image")
    path = Path(choice).resolve()
    if not path.is_file():
        raise ValueError(f"unknown background {choice!r}: auto, video, cover, gradient or a file")
    return _picture(path, "image" if path.suffix.lower() in IMAGES else "video")
