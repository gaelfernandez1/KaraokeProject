import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from karaoke_bench import stage as stage_module
from karaoke_bench.cache import Cache, cache_key
from karaoke_bench.paths import BenchPaths
from karaoke_bench.pipeline import StepSpec, step_version
from karaoke_bench.stage import StageItem, run_stage

ToneMaker = Callable[..., Path]
pytestmark = pytest.mark.usefixtures("ffmpeg")


def _items(make_tone: ToneMaker) -> list[StageItem]:
    return [
        StageItem(
            key=name,
            args={
                "vocals": str(make_tone(f"{name}.wav", 2.0)),
                "lines": ["ola mar"],
                "language": "gl",
            },
            fingerprint=name,
        )
        for name in ("a", "b")
    ]


def test_run_stage_runs_fake_aligner_in_subprocess(tmp_path: Path, make_tone: ToneMaker) -> None:
    spec = StepSpec("aligner", "karaoke_bench.fakes:EvenSplitAligner")

    outcome = run_stage(spec, _items(make_tone), BenchPaths(tmp_path / "bench"))

    assert set(outcome.items) == {"a", "b"}
    for item in outcome.items.values():
        assert item.error is None
        assert not item.cached
        assert item.seconds > 0
        assert item.output[0].words[1].text == "mar"
    assert outcome.ram_peak_mb is not None
    assert outcome.ram_peak_mb > 0


def test_run_stage_isolates_failures(tmp_path: Path, make_tone: ToneMaker) -> None:
    spec = StepSpec("aligner", "karaoke_bench.fakes:FailingAligner", {"fail_on": "b.wav"})

    outcome = run_stage(spec, _items(make_tone), BenchPaths(tmp_path / "bench"))

    assert outcome.items["a"].error is None
    assert outcome.items["b"].output is None
    assert "RuntimeError" in (outcome.items["b"].error or "")


def test_broken_step_fails_every_item(tmp_path: Path, make_tone: ToneMaker) -> None:
    spec = StepSpec("aligner", "karaoke_bench.fakes:FailingAligner", {"wrong_param": 1})

    outcome = run_stage(spec, _items(make_tone), BenchPaths(tmp_path / "bench"))

    assert all(item.error for item in outcome.items.values())


def test_second_run_hits_cache(
    tmp_path: Path, make_tone: ToneMaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = StepSpec("aligner", "karaoke_bench.fakes:EvenSplitAligner")
    paths = BenchPaths(tmp_path / "bench")
    items = _items(make_tone)
    first = run_stage(spec, items, paths)

    def no_process(*args: object, **kwargs: object) -> None:
        raise AssertionError("the cache should have answered")

    monkeypatch.setattr(stage_module.subprocess, "Popen", no_process)
    second = run_stage(spec, items, paths)

    assert all(item.cached for item in second.items.values())
    assert second.items["a"].output == first.items["a"].output
    assert second.items["a"].seconds == first.items["a"].seconds


def test_no_cache_recomputes(tmp_path: Path, make_tone: ToneMaker) -> None:
    spec = StepSpec("aligner", "karaoke_bench.fakes:EvenSplitAligner")
    paths = BenchPaths(tmp_path / "bench")
    run_stage(spec, _items(make_tone), paths)

    again = run_stage(spec, _items(make_tone), paths, use_cache=False)

    assert not any(item.cached for item in again.items.values())


def test_corrupt_cache_entry_is_ignored(tmp_path: Path) -> None:
    cache = Cache(tmp_path)
    spec = StepSpec("aligner", "karaoke_bench.fakes:EvenSplitAligner")
    key = cache_key(spec, step_version(spec), "x")
    (tmp_path / "aligner").mkdir()
    (tmp_path / "aligner" / f"{key}.json").write_text('{"output": [', encoding="utf-8")

    assert cache.get("aligner", key) is None


def test_cache_key_changes_with_params_version_and_input() -> None:
    spec = StepSpec("aligner", "m:C", {"a": 1})
    base = cache_key(spec, "1", "x")

    assert cache_key(StepSpec("aligner", "m:C", {"a": 2}), "1", "x") != base
    assert cache_key(spec, "2", "x") != base
    assert cache_key(spec, "1", "y") != base
    assert cache_key(StepSpec("aligner", "m:C", {"a": 1}), "1", "x") == base


def test_worker_death_marks_missing_items(
    tmp_path: Path, make_tone: ToneMaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_popen = subprocess.Popen

    def dying_worker(command: list[str], **kwargs: object) -> "subprocess.Popen[bytes]":
        return real_popen(["python3", "-c", "import sys; sys.exit(9)"])

    monkeypatch.setattr(stage_module.subprocess, "Popen", dying_worker)
    spec = StepSpec("aligner", "karaoke_bench.fakes:EvenSplitAligner")

    outcome = run_stage(spec, _items(make_tone), BenchPaths(tmp_path / "bench"))

    assert all("exited with code 9" in (item.error or "") for item in outcome.items.values())
