"""Unit tests for the Celery -> Modal dispatch switch.

modal is injected via sys.modules so these run without the real client installed.
"""

import sys
import types
from pathlib import Path

from karaoke.domain.pipeline import JobConfig
from karaoke.workers.celery_tasks import _maybe_dispatch_to_modal


class _Reporter:
    def __init__(self):
        self.calls: list = []

    def report(self, step, percent):
        self.calls.append((step, percent))

    def check_cancelled(self):
        pass


def _config(tmp_path: Path) -> JobConfig:
    return JobConfig(video_path=tmp_path / "song.mp4", task_id="task-9", work_dir=tmp_path)


def test_disabled_runs_local(tmp_path, monkeypatch):
    monkeypatch.setenv("MODAL_DISPATCH", "false")
    result = _maybe_dispatch_to_modal(_config(tmp_path), {"kind": "automatic"}, _Reporter())
    assert result is None


def test_enabled_dispatches_with_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("MODAL_DISPATCH", "true")
    captured: dict = {}

    class _Remote:
        def remote(self, task_id, payload):
            captured["task_id"] = task_id
            captured["payload"] = payload
            return "karaoke/task-9/out.mp4"

    class _Function:
        @staticmethod
        def from_name(app_name, fn_name):
            captured["lookup"] = (app_name, fn_name)
            return _Remote()

    fake_modal = types.ModuleType("modal")
    fake_modal.Function = _Function
    monkeypatch.setitem(sys.modules, "modal", fake_modal)

    result = _maybe_dispatch_to_modal(
        _config(tmp_path),
        {"kind": "manual", "lyrics": "la", "language": "gl"},
        _Reporter(),
    )

    assert result == "karaoke/task-9/out.mp4"
    assert captured["lookup"] == ("karaoke-gpu", "run_karaoke_job")
    assert captured["task_id"] == "task-9"
    assert captured["payload"]["task_id"] == "task-9"
    assert captured["payload"]["strategy"] == {"kind": "manual", "lyrics": "la", "language": "gl"}
    # The Storage object must never ride along in the transport payload.
    assert "storage" not in captured["payload"]
