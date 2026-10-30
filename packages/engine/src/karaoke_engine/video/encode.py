"""H.264 encoding with the GPU when it works (NVENC), else with x264 on the CPU."""

import subprocess
from functools import cache
from pathlib import Path


@cache
def _has_nvenc() -> bool:
    listed = subprocess.run(
        ["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True, check=False
    ).stdout
    return "h264_nvenc" in listed


def h264_encoders(quality: int) -> list[list[str]]:
    """Encoder options to try in order; `quality` is a CRF-like number (lower is better)."""
    x264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(quality), "-profile:v", "high"]
    if not _has_nvenc():
        return [x264]
    nvenc = [
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", str(quality), "-b:v", "0",
        "-profile:v", "high",
    ]  # fmt: skip
    # NVENC can be listed and still fail (no GPU, driver busy): x264 is the fallback.
    return [nvenc, x264]


def run_encoder(
    head: list[str], encoders: list[list[str]], tail: list[str], cwd: Path | None = None
) -> list[str]:
    """Runs `head + encoder + tail` with each encoder until one works; returns the one used."""
    error = ""
    for encoder in encoders:
        result = subprocess.run(
            [*head, *encoder, *tail], cwd=cwd, capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            return encoder
        error = result.stderr
    raise RuntimeError(f"ffmpeg failed: {error.strip()[-600:]}")
