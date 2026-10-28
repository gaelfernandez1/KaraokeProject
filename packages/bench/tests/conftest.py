import math
import shutil
import wave
from array import array
from collections.abc import Callable
from pathlib import Path

import pytest

from karaoke_bench.paths import BenchPaths
from karaoke_bench.reference import dump_reference, reference_from_doc
from karaoke_contracts import load_doc
from karaoke_engine.demo import synthesize_package_audio

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


DemoSongAdder = Callable[[BenchPaths, str], None]


@pytest.fixture
def add_demo_song(demo_json: Path) -> DemoSongAdder:
    """Adds a private song made from the synthetic demo package (beeps on every syllable)."""

    def add(paths: BenchPaths, song_id: str) -> None:
        package = paths.root.parent / f"pkg-{song_id}"
        package.mkdir(parents=True)
        shutil.copy(demo_json, package / "karaoke.json")
        synthesize_package_audio(package)
        song_dir = paths.data / "private" / song_id
        song_dir.mkdir(parents=True)
        shutil.copy(package / "vocals.wav", song_dir / "audio.wav")
        (song_dir / "meta.toml").write_text('title = "Demo"\nlanguage = "gl"\n', encoding="utf-8")
        reference = reference_from_doc(load_doc(demo_json), "manual")
        dump_reference(reference, song_dir / "reference.json")

    return add


@pytest.fixture
def demo_bench(tmp_path: Path, add_demo_song: DemoSongAdder) -> BenchPaths:
    """A bench folder with one private song, `demo`."""
    paths = BenchPaths(tmp_path / "bench")
    add_demo_song(paths, "demo")
    return paths
