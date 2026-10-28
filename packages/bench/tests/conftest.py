import math
import shutil
import wave
from array import array
from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_DIR = REPO_ROOT / "fixtures" / "packages" / "demo-sintetico"

ToneMaker = Callable[..., Path]


@pytest.fixture
def demo_json() -> Path:
    return DEMO_DIR / "karaoke.json"


@pytest.fixture
def ffmpeg() -> None:
    """Skips the test when ffmpeg is missing (CI images may not have it)."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg and ffprobe are not installed")


@pytest.fixture
def make_tone(tmp_path: Path) -> ToneMaker:
    """Writes a mono 16-bit sine wave: enough for anything that only needs real audio."""

    def make(name: str, seconds: float, rate: int = 22_050, hz: float = 440.0) -> Path:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        count = round(seconds * rate)
        samples = array(
            "h", (int(8000 * math.sin(2 * math.pi * hz * i / rate)) for i in range(count))
        )
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(samples.tobytes())
        return path

    return make
