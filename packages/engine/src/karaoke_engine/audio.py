"""Audio in and out of the engine: decode anything ffmpeg reads, even loudness out, and write
the package stems in a format every browser plays (Safari included).

Loudness follows EBU R128. The gain is measured on the original mix and applied equally to the
vocals and the instrumental, so the guide vocals at full volume sound like the original and
every song plays at the same level.
"""

import json
import math
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from karaoke_contracts import AudioRefs, dump_doc, load_doc, resolve_media, validate_package
from karaoke_engine.steps import Stems

SAMPLE_RATE = 44_100
TARGET_LUFS = -14.0
PEAK_CEILING_DBTP = -1.0
BITRATES = {"instrumental": "160k", "vocals": "128k"}


class AudioError(RuntimeError):
    def __init__(self, path: Path, detail: str) -> None:
        super().__init__(f"{path}: {detail.strip()}")


@dataclass(frozen=True)
class AudioInfo:
    codec: str
    sample_rate: int
    channels: int
    duration: float
    frames: int | None


@dataclass(frozen=True)
class Loudness:
    """Integrated loudness (LUFS) and true peak (dBTP); None for silence."""

    integrated: float | None
    true_peak: float | None


@dataclass(frozen=True)
class Gain:
    db: float
    lufs: float | None


def probe(path: Path) -> AudioInfo:
    result = _run(
        path,
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-count_packets", "-show_entries",
         "stream=codec_name,sample_rate,channels,duration,duration_ts,time_base:format=duration",
         "-of", "json", str(path)],
    )  # fmt: skip
    data = json.loads(result)
    if not data.get("streams"):
        raise AudioError(path, "no audio stream")
    stream = data["streams"][0]
    rate = int(stream["sample_rate"])
    duration = float(stream.get("duration") or data["format"]["duration"])
    frames = None
    if stream.get("codec_name", "").startswith("pcm_") and stream.get("duration_ts"):
        frames = int(stream["duration_ts"])
    return AudioInfo(stream["codec_name"], rate, int(stream["channels"]), duration, frames)


def decode(src: Path, dest: Path) -> Path:
    """Any audio or video file to a stereo 44.1 kHz WAV (float, so nothing clips)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run(
        src,
        ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "2", "-ar",
         str(SAMPLE_RATE), "-c:a", "pcm_f32le", str(dest)],
    )  # fmt: skip
    return dest


def measure(path: Path) -> Loudness:
    output = _run(
        path,
        ["ffmpeg", "-nostdin", "-hide_banner", "-i", str(path), "-vn", "-af",
         "loudnorm=print_format=json", "-f", "null", "-"],
        stderr=True,
    )  # fmt: skip
    stats = json.loads(output[output.rindex("{") : output.rindex("}") + 1])
    return Loudness(_level(stats["input_i"]), _level(stats["input_tp"]))


def plan_gain(
    mix: Loudness,
    stem_peaks: Sequence[float | None],
    target: float = TARGET_LUFS,
    ceiling: float = PEAK_CEILING_DBTP,
) -> Gain:
    """The common gain that brings the mix to `target` without any stem passing `ceiling`."""
    if mix.integrated is None:
        return Gain(db=0.0, lufs=None)
    db = target - mix.integrated
    peaks = [p for p in stem_peaks if p is not None]
    if peaks:
        db = min(db, ceiling - max(peaks))
    db = round(db, 2)
    return Gain(db=db, lufs=round(mix.integrated + db, 2))


def encode_m4a(src: Path, dest: Path, gain_db: float, bitrate: str) -> Path:
    """AAC-LC in MP4 with the index first, so browsers can seek before the whole file arrives."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run(
        src,
        ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src), "-vn", "-af",
         f"volume={gain_db:.2f}dB", "-ac", "2", "-ar", str(SAMPLE_RATE), "-c:a", "aac", "-b:a",
         bitrate, "-movflags", "+faststart", str(dest)],
    )  # fmt: skip
    return dest


def package_audio(mix: Path, stems: Stems, out_dir: Path) -> AudioRefs:
    """Writes instrumental.m4a and vocals.m4a, levelled from the original mix."""
    peaks = [measure(stems.instrumental).true_peak, measure(stems.vocals).true_peak]
    gain = plan_gain(measure(mix), peaks)
    encode_m4a(stems.instrumental, out_dir / "instrumental.m4a", gain.db, BITRATES["instrumental"])
    encode_m4a(stems.vocals, out_dir / "vocals.m4a", gain.db, BITRATES["vocals"])
    return AudioRefs(
        instrumental="instrumental.m4a",
        vocals="vocals.m4a",
        loudness_lufs=None if gain.lufs is None else round(gain.lufs, 1),
    )


def convert_package(package_dir: Path, mix: Path | None = None) -> AudioRefs:
    """Turns a package's stems (any format) into levelled m4a and points karaoke.json at them.

    Without the original `mix`, the stems are summed to stand in for it.
    """
    doc = load_doc(package_dir / "karaoke.json")
    if doc.audio.vocals is None:
        raise ValueError("the package has no vocals stem")
    stems = Stems(
        vocals=resolve_media(package_dir, doc.audio.vocals),
        instrumental=resolve_media(package_dir, doc.audio.instrumental),
    )
    with tempfile.TemporaryDirectory() as tmp:
        if mix is None:
            mix = Path(tmp) / "mix.wav"
            _run(
                stems.vocals,
                ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(stems.vocals), "-i",
                 str(stems.instrumental), "-filter_complex", "amix=inputs=2:normalize=0",
                 "-c:a", "pcm_f32le", str(mix)],
            )  # fmt: skip
        refs = package_audio(mix, stems, package_dir)
    dump_doc(doc.model_copy(update={"audio": refs}), package_dir / "karaoke.json")
    issues = validate_package(package_dir)
    if issues:
        raise ValueError("; ".join(f"{i.path}: {i.message}" for i in issues))
    return refs


def _level(value: str) -> float | None:
    level = float(value)
    return level if math.isfinite(level) and level > -70 else None


def _run(path: Path, command: list[str], stderr: bool = False) -> str:
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        raise AudioError(path, result.stderr.decode(errors="replace"))
    return (result.stderr if stderr else result.stdout).decode(errors="replace")
