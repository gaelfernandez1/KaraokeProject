import json
import shutil
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_DIR = REPO_ROOT / "fixtures" / "packages" / "demo-sintetico"
DEMO_JSON = DEMO_DIR / "karaoke.json"


@pytest.fixture
def demo_json() -> Path:
    return DEMO_JSON


@pytest.fixture
def demo_data() -> dict[str, Any]:
    """The demo document as a plain dict, safe to mutate per test."""
    data: dict[str, Any] = json.loads(DEMO_JSON.read_text(encoding="utf-8"))
    return data


@pytest.fixture
def demo_package(tmp_path: Path) -> Path:
    """A copy of the demo package with empty placeholder media files."""
    package = tmp_path / "demo"
    package.mkdir()
    shutil.copy(DEMO_JSON, package / "karaoke.json")
    for name in ("instrumental.wav", "vocals.wav"):
        (package / name).write_bytes(b"")
    return package
