"""Audio helpers on top of ffmpeg, which every machine of the project already has."""

import hashlib
import subprocess
import wave
from pathlib import Path

import numpy as np
import numpy.typing as npt

SAMPLE_RATE = 16_000

Samples = npt.NDArray[np.float32]


class AudioError(RuntimeError):
    def __init__(self, path: Path, detail: str) -> None:
        super().__init__(f"{path}: {detail.strip() or 'ffmpeg failed'}")
        self.path = path


def duration(path: Path) -> float:
    out = _run(
        path,
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
    )
    try:
        return float(out.decode().strip())
    except ValueError as exc:
        raise AudioError(path, "ffprobe gave no duration") from exc


def load_mono16k(path: Path) -> Samples:
    """Decodes any format ffmpeg reads into mono float32 samples at 16 kHz."""
    out = _run(
        path,
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar",
         str(SAMPLE_RATE), "pipe:1"],
    )  # fmt: skip
    return np.frombuffer(out, dtype=np.float32).copy()


def cut(path: Path, start: float, end: float, dest: Path) -> Path:
    """Writes the [start, end] stretch of `path` as a mono 16 kHz WAV."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run(
        path,
        ["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
         "-i", str(path), "-ac", "1", "-ar", str(SAMPLE_RATE), str(dest)],
    )  # fmt: skip
    return dest


def write_wav(path: Path, samples: npt.NDArray[np.floating], rate: int) -> Path:
    """Writes (channels, frames) float samples in [-1, 1] as 16-bit PCM, clipping overshoots."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = np.atleast_2d(samples)
    pcm = (np.clip(frames, -1.0, 1.0) * 32767).astype("<i2").T.copy()
    with wave.open(str(path), "wb") as out:
        out.setnchannels(frames.shape[0])
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(pcm.tobytes())
    return path


def peaks(samples: Samples, rate: int = 100) -> tuple[list[float], list[float]]:
    """Minimum and maximum of each 1/rate-second block, for drawing a waveform."""
    block = SAMPLE_RATE // rate
    count = len(samples) // block
    blocks = samples[: count * block].reshape(count, block)
    return blocks.min(axis=1).round(4).tolist(), blocks.max(axis=1).round(4).tolist()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(path: Path, command: list[str]) -> bytes:
    if not path.is_file():
        raise AudioError(path, "file not found")
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        raise AudioError(path, result.stderr.decode(errors="replace"))
    return result.stdout
