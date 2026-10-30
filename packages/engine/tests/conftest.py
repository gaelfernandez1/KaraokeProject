import shutil
from pathlib import Path

import pytest

DEMO_JSON = Path(__file__).resolve().parents[3] / "fixtures/packages/demo-sintetico/karaoke.json"


@pytest.fixture
def bare_package(tmp_path: Path) -> Path:
    """A copy of the demo package with its karaoke.json only (no media yet)."""
    package = tmp_path / "demo"
    package.mkdir()
    shutil.copy(DEMO_JSON, package / "karaoke.json")
    return package


@pytest.fixture
def ffmpeg() -> None:
    """Skips the test when ffmpeg is missing (CI images may not have it)."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg and ffprobe are not installed")
