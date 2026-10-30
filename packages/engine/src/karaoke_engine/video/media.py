"""What a song file brings for the eyes: its video (kept as the package background) and its cover.

The background is re-encoded for browsers: H.264 that every phone and TV plays, a keyframe every
second so seeking is instant, the index at the front so it starts at once, and no audio (the
player plays the package stems).
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from karaoke_contracts import KaraokeDoc, VideoRefs, dump_doc, load_doc
from karaoke_engine.video.encode import h264_encoders, run_encoder

# 720p: a dimmed background under the lyrics looks the same, at a third of the size of 1080p.
MAX_WIDTH, MAX_HEIGHT = 1280, 720
MAX_FPS = 30
IMAGES = {".jpg", ".jpeg", ".png", ".webp"}
COVER_SIZE = 1280
BACKGROUND_QUALITY = 30


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    fps: float
    duration: float


def _ffprobe(path: Path) -> dict[str, list[dict[str, object]] | dict[str, object]]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"{path}: not a media file ffmpeg can read")
    data: dict[str, list[dict[str, object]] | dict[str, object]] = json.loads(result.stdout)
    return data


def _streams(
    data: dict[str, list[dict[str, object]] | dict[str, object]],
) -> list[dict[str, object]]:
    streams = data.get("streams", [])
    return streams if isinstance(streams, list) else []


def _is_picture(stream: dict[str, object]) -> bool:
    disposition = stream.get("disposition")
    return isinstance(disposition, dict) and disposition.get("attached_pic") == 1


def _rate(text: object) -> float:
    num, _, den = str(text).partition("/")
    try:
        return float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _rotation(stream: dict[str, object]) -> int:
    """Degrees the stream must be turned when shown (display matrix or the old `rotate` tag)."""
    side = stream.get("side_data_list")
    for item in side if isinstance(side, list) else []:
        if isinstance(item, dict) and "rotation" in item:
            return round(float(str(item["rotation"])))
    tags = stream.get("tags")
    if isinstance(tags, dict) and "rotate" in tags:
        return round(float(str(tags["rotate"])))
    return 0


def probe_video(path: Path) -> VideoInfo | None:
    """The first real video stream (not a cover picture), or None for audio-only files."""
    data = _ffprobe(path)
    for stream in _streams(data):
        if stream.get("codec_type") != "video" or _is_picture(stream):
            continue
        fps = _rate(stream.get("avg_frame_rate")) or _rate(stream.get("r_frame_rate"))
        width, height = int(str(stream["width"])), int(str(stream["height"]))
        # Phone clips are often stored sideways with a rotation to apply; ffmpeg applies it.
        if _rotation(stream) % 180 == 90:
            width, height = height, width
        fmt = data.get("format", {})
        duration = stream.get("duration") or (fmt.get("duration") if isinstance(fmt, dict) else 0)
        return VideoInfo(
            width=width,
            height=height,
            fps=fps,
            duration=float(str(duration or 0)),
        )
    return None


def extract_background(source: Path, out: Path) -> Path:
    """Writes the video of `source` as a background for the web player and the video export."""
    info = probe_video(source)
    if info is None:
        raise ValueError(f"{source} has no video")
    fps = min(info.fps or MAX_FPS, MAX_FPS)
    filters = (
        f"scale='min({MAX_WIDTH},iw)':'min({MAX_HEIGHT},ih)'"
        ":force_original_aspect_ratio=decrease:force_divisible_by=2"
    )
    if info.fps > MAX_FPS:
        filters += f",fps={MAX_FPS}"
    keyframes = str(round(fps))
    command = [
        "ffmpeg", "-v", "error", "-y", "-i", str(source), "-map", "0:v:0", "-an", "-sn",
        "-vf", filters + ",format=yuv420p",
    ]  # fmt: skip
    tail = ["-g", keyframes, "-keyint_min", keyframes, "-movflags", "+faststart", str(out)]
    run_encoder(command, h264_encoders(BACKGROUND_QUALITY), tail)
    return out


def extract_cover(source: Path, out: Path) -> Path | None:
    """The cover art embedded in `source`, or else a frame a third of the way into its video."""
    data = _ffprobe(source)
    pictures = [s for s in _streams(data) if s.get("codec_type") == "video" and _is_picture(s)]
    scale = (
        f"scale='min({COVER_SIZE},iw)':'min({COVER_SIZE},ih)':force_original_aspect_ratio=decrease"
    )
    if pictures:
        args = ["-i", str(source), "-map", f"0:{pictures[0]['index']}"]
    else:
        info = probe_video(source)
        if info is None:
            return None
        args = ["-ss", f"{info.duration / 3:.3f}", "-i", str(source), "-map", "0:v:0"]
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            *args,
            "-frames:v",
            "1",
            "-vf",
            scale,
            "-q:v",
            "3",
            str(out),
        ],
        capture_output=True,
        check=True,
    )
    return out


def mean_luma(path: Path, samples: int = 12) -> float:
    """Average brightness (0 black to 1 white) of an image, or of frames spread over a video."""
    info = probe_video(path)
    picture = info is None or info.duration <= 0 or path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    pick = "" if picture else f"fps={samples}/{info.duration:.3f}," if info else ""
    result = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-i", str(path), "-vf",
            f"{pick}scale=160:-2,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
            *(["-frames:v", "1"] if picture else []), "-f", "null", "-",
        ],
        capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    values = [
        float(line.split("=", 1)[1])
        for line in result.splitlines()
        if line.startswith("lavfi.signalstats.YAVG=")
    ]
    if not values:
        raise ValueError(f"{path}: no frames to measure")
    # Video luma runs from 16 (black) to 235 (white).
    return min(1.0, max(0.0, (sum(values) / len(values) - 16) / 219))


def add_background(package: Path, source: Path) -> KaraokeDoc:
    """Gives a package the video of `source` as background, and its picture as cover: the art of
    a song file or a picture always, a frame of a video only if the package has no cover yet.

    New files are written aside and only replace the old ones (and karaoke.json changes) once
    everything worked, so a failure leaves the package as it was.
    """
    doc = load_doc(package / "karaoke.json")
    picture = source.suffix.lower() in IMAGES
    has_video = not picture and probe_video(source) is not None
    parts = {
        "background.mp4": package / ".background.part.mp4",
        "cover.jpg": package / ".cover.part.jpg",
    }
    staged: dict[str, Path] = {}
    try:
        if has_video:
            staged["background.mp4"] = extract_background(source, parts["background.mp4"])
        if not has_video or doc.cover is None:
            cover = extract_cover(source, parts["cover.jpg"])
            if cover is not None:
                staged["cover.jpg"] = cover
        if not staged:
            raise ValueError(f"{source} has no video and no picture")
    except BaseException:
        for part in parts.values():
            part.unlink(missing_ok=True)
        raise
    updates: dict[str, object] = {}
    if "background.mp4" in staged:
        updates["video"] = VideoRefs(background="background.mp4")
    if "cover.jpg" in staged:
        updates["cover"] = "cover.jpg"
    for name, part in staged.items():
        part.replace(package / name)
    doc = doc.model_copy(update=updates)
    written = package / ".karaoke.json.tmp"
    dump_doc(doc, written)
    written.replace(package / "karaoke.json")
    return doc
