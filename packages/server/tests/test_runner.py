import json
import subprocess
import sys
from pathlib import Path

import pytest

from karaoke_contracts import validate_package
from karaoke_server.jobs.runner import classify_error


def run_runner(tmp_path: Path, spec: dict[str, object]) -> tuple[int, list[dict[str, object]]]:
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "karaoke_server.jobs.runner", str(path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    return result.returncode, events


def test_runner_fake_make_emits_stages_and_a_package(tmp_path: Path) -> None:
    out = tmp_path / "out"
    spec = {
        "kind": "make",
        "source": "/nowhere.mp3",
        "out": str(out),
        "language": "gl",
        "lyrics": None,
        "lrclib": False,
        "title": "Proba",
        "artist": None,
        "fake": True,
    }
    code, events = run_runner(tmp_path, spec)
    assert code == 0
    stages = [e["stage"] for e in events if e["event"] == "stage"]
    assert stages == ["decode", "separate", "transcribe", "align", "encode"]
    assert events[-1]["event"] == "done"
    assert validate_package(out) == []
    assert json.loads((out / "karaoke.json").read_text(encoding="utf-8"))["title"] == "Proba"


def test_runner_fake_export_writes_a_video(tmp_path: Path) -> None:
    spec = {
        "kind": "export",
        "package": "/nowhere",
        "out": str(tmp_path / ".partial-a.mp4"),
        "aspect": "16:9",
        "theme": "clasico",
        "fake": True,
    }
    code, events = run_runner(tmp_path, spec)
    assert code == 0
    assert (tmp_path / ".partial-a.mp4").stat().st_size > 0
    assert events[-1] == {"event": "done", "result": {"file": str(tmp_path / ".partial-a.mp4")}}


@pytest.mark.usefixtures("ffmpeg")
def test_runner_reports_bad_lyrics(tmp_path: Path) -> None:
    song = tmp_path / "tone.wav"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=d=2", str(song)], check=True
    )
    spec = {
        "kind": "make",
        "source": str(song),
        "out": str(tmp_path / "out"),
        "language": "gl",
        "lyrics": "[Estribillo]\n(x2)",
        "lrclib": False,
        "title": "Proba",
        "artist": None,
        "fake": False,
    }
    code, events = run_runner(tmp_path, spec)
    assert code == 1
    assert events[-1]["event"] == "error"
    assert events[-1]["code"] == "bad_lyrics"
    assert events[-1]["transient"] is False


@pytest.mark.usefixtures("ffmpeg")
def test_runner_reports_unreadable_audio(tmp_path: Path) -> None:
    song = tmp_path / "not-audio.mp3"
    song.write_text("hello")
    spec = {
        "kind": "make",
        "source": str(song),
        "out": str(tmp_path / "out"),
        "language": "gl",
        "lyrics": "la la la",
        "lrclib": False,
        "title": "Proba",
        "artist": None,
        "fake": False,
    }
    code, events = run_runner(tmp_path, spec)
    assert code == 1
    assert events[-1]["code"] == "unreadable"


class OutOfMemoryError(RuntimeError):
    """Stands in for torch.OutOfMemoryError (torch is not installed in CI)."""


def test_classify_cuda_oom_is_transient() -> None:
    assert classify_error(OutOfMemoryError("CUDA out of memory. Tried to allocate")) == (
        "gpu_memory",
        True,
    )
    assert classify_error(RuntimeError("CUDA out of memory")) == ("gpu_memory", True)
    assert classify_error(RuntimeError("CUDA error: unspecified launch failure")) == (
        "engine_failed",
        True,
    )
    assert classify_error(MemoryError()) == ("out_of_memory", True)
    assert classify_error(ValueError("the lyrics have no sung lines")) == ("bad_lyrics", False)
    assert classify_error(OSError(28, "No space left on device")) == ("disk_full", False)
    assert classify_error(KeyError("x")) == ("engine_failed", False)
