from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_DIR = REPO_ROOT / "fixtures" / "packages" / "demo-sintetico"


@pytest.fixture
def demo_json() -> Path:
    return DEMO_DIR / "karaoke.json"
