"""A quick MP4 of a package's lyrics on a plain background, with the guide vocals audible.

It is for checking the lyrics against the singing (and against the web player) by eye and ear;
the real video export, with backgrounds and titles, is `karaoke render`.
"""

import subprocess
import tempfile
from pathlib import Path

from karaoke_contracts import Theme, load_doc
from karaoke_engine.subtitles.ass import build_ass
from karaoke_engine.subtitles.themes import fonts_dir

BACKGROUND = "0x101018"
VOCALS_LEVEL = 0.6


def _encoders() -> list[list[str]]:
    """NVENC when ffmpeg has it (it may still fail without a GPU), then x264."""
    listed = subprocess.run(
        ["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True, check=False
    ).stdout
    x264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]
    if "h264_nvenc" in listed:
        return [["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "21"], x264]
    return [x264]


def render_preview(
    package: Path,
    theme: Theme,
    width: int,
    height: int,
    out: Path,
    start: float | None = None,
    duration: float | None = None,
) -> Path:
    doc = load_doc(package / "karaoke.json")
    begin = max(0.0, start or 0.0)
    length = duration if duration is not None else doc.duration - begin
    if length <= 0:
        raise ValueError(f"nothing to render from {begin} s in a {doc.duration:.1f} s song")
    out = out.resolve()
    with tempfile.TemporaryDirectory() as work:
        # ffmpeg filter arguments need escaping; relative names in a scratch folder do not.
        folder = Path(work)
        (folder / "lyrics.ass").write_text(build_ass(doc, theme, width, height), encoding="utf-8")
        (folder / "fonts").symlink_to(fonts_dir())
        inputs = [
            "-f", "lavfi", "-i", f"color=c={BACKGROUND}:s={width}x{height}:r=30:d={length:.3f}",
            "-ss", f"{begin:.3f}", "-t", f"{length:.3f}",
            "-i", str((package / doc.audio.instrumental).resolve()),
        ]  # fmt: skip
        video = (
            f"[0:v]setpts=PTS+{begin:.3f}/TB,subtitles=lyrics.ass:fontsdir=fonts,"
            "setpts=PTS-STARTPTS[v]"
        )
        if doc.audio.vocals is not None:
            inputs += ["-ss", f"{begin:.3f}", "-t", f"{length:.3f}"]
            inputs += ["-i", str((package / doc.audio.vocals).resolve())]
            audio = f";[2:a]volume={VOCALS_LEVEL}[voc];[1:a][voc]amix=inputs=2:normalize=0[a]"
        else:
            audio = ";[1:a]anull[a]"
        error = ""
        for encoder in _encoders():
            command = [
                "ffmpeg", "-v", "error", "-y", *inputs,
                "-filter_complex", video + audio, "-map", "[v]", "-map", "[a]",
                *encoder, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                "-shortest", str(out),
            ]  # fmt: skip
            result = subprocess.run(
                command, cwd=folder, capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                return out
            error = result.stderr
        raise RuntimeError(f"ffmpeg could not render the preview: {error.strip()[-500:]}")
