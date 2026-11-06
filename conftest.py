"""Test policy for every package.

- `ffmpeg`: a fixture for tests that run ffmpeg/ffprobe; they skip on a machine without them.
- `@pytest.mark.models`: tests that load real ML models (2 to 3 GB of RAM each). `pytest`
  leaves them out; `make test-models` runs them on their own, one process, after the rest.
- With KARAOKE_STRICT_SKIPS=1 (the CI), a skip is a failure unless its reason is one the CI cannot
  help: no GPU, no ML libraries, no downloaded models or song data, no systemd, local-only timing.
  So a CI image that loses ffmpeg turns red instead of quietly testing less.
"""

import os
import re
import shutil
from collections.abc import Generator

import pytest

pytest_plugins = ["pytester"]

ALLOWED_IN_CI = re.compile(
    r"CUDA GPU"
    r"|could not import '(torch|torchaudio|transformers|faster_whisper|ctranslate2"
    r"|audio_separator|demucs)'"
    r"|download .* first|karaoke-bench fetch|karaoke demo"
    r"|systemd"
    r"|local only"
)


@pytest.fixture
def ffmpeg() -> None:
    """Skips the test when ffmpeg or ffprobe is missing."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg and ffprobe are not installed")


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    report = yield
    if report.skipped and os.environ.get("KARAOKE_STRICT_SKIPS") == "1":
        reason = report.longrepr[2] if isinstance(report.longrepr, tuple) else str(report.longrepr)
        if not ALLOWED_IN_CI.search(reason):
            report.outcome = "failed"
            report.longrepr = f"must not be skipped in CI (KARAOKE_STRICT_SKIPS=1): {reason}"
    return report
