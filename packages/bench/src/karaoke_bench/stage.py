"""Runs one pipeline step over many songs: cache first, then a worker process.

One process per step keeps a single model on the 4 GB GPU, frees all of it when the step
ends, measures memory per step cleanly, and keeps CUDA libraries of different steps apart.
"""

import json
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from karaoke_bench.cache import Cache, CacheEntry, cache_key
from karaoke_bench.codec import decode_output
from karaoke_bench.paths import BenchPaths
from karaoke_bench.pipeline import StepSpec, step_version
from karaoke_bench.resources import GpuSampler

# A worker that keeps dying is broken for every song, not just one.
MAX_CRASHES = 3
POLL_SECONDS = 0.2


@dataclass(frozen=True)
class StageItem:
    key: str
    args: dict[str, Any]
    fingerprint: str


@dataclass(frozen=True)
class ItemOutcome:
    key: str
    output: Any | None
    seconds: float
    cached: bool
    error: str | None


@dataclass(frozen=True)
class StageOutcome:
    items: dict[str, ItemOutcome]
    load_seconds: float | None
    vram_peak_mb: float | None
    ram_peak_mb: float | None


def run_stage(
    spec: StepSpec, items: Sequence[StageItem], paths: BenchPaths, use_cache: bool = True
) -> StageOutcome:
    cache = Cache(paths.cache)
    version = step_version(spec)
    keys = {item.key: cache_key(spec, version, item.fingerprint) for item in items}
    outcomes: dict[str, ItemOutcome] = {}
    entries: list[CacheEntry] = []
    todo = []
    for item in items:
        entry = cache.get(spec.kind, keys[item.key]) if use_cache else None
        if entry is None:
            todo.append(item)
            continue
        entries.append(entry)
        output = decode_output(spec.kind, entry.output)
        outcomes[item.key] = ItemOutcome(item.key, output, entry.seconds, True, None)

    if todo:
        records, stage, vram = _run_worker(spec, todo, keys, cache, paths)
        fresh = []
        for item in todo:
            record = records[item.key]
            if record["error"]:
                outcomes[item.key] = ItemOutcome(item.key, None, 0.0, False, record["error"])
            else:
                output = decode_output(spec.kind, record["output"])
                outcomes[item.key] = ItemOutcome(item.key, output, record["seconds"], False, None)
                fresh.append((item.key, record))
        for key, record in fresh:
            entry = CacheEntry(
                output=record["output"],
                seconds=record["seconds"],
                load_seconds=stage.get("load_seconds"),
                stage_vram_mb=vram,
                stage_ram_mb=stage.get("ram_peak_mb"),
            )
            cache.put(spec.kind, keys[key], entry)
            entries.append(entry)

    return StageOutcome(
        items={item.key: outcomes[item.key] for item in items},
        load_seconds=_max(e.load_seconds for e in entries),
        vram_peak_mb=_max(e.stage_vram_mb for e in entries),
        ram_peak_mb=_max(e.stage_ram_mb for e in entries),
    )


def _run_worker(
    spec: StepSpec,
    items: Sequence[StageItem],
    keys: dict[str, str],
    cache: Cache,
    paths: BenchPaths,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], float | None]:
    """Runs the items in worker processes and returns one record per item.

    The worker handles the items in order, so when it dies (an OOM kill, a crash in CUDA) the
    first item without a record is the one it died on: that one fails and a new worker carries on
    with the rest, up to MAX_CRASHES times.
    """
    records: dict[str, dict[str, Any]] = {}
    stages: list[dict[str, Any]] = []
    peaks: list[float | None] = []
    remaining = list(items)
    crashes = 0
    while remaining:
        found, stage, code, peak = _launch(spec, remaining, keys, cache, paths)
        records.update(found)
        stages.append(stage)
        peaks.append(peak)
        remaining = [item for item in remaining if item.key not in found]
        if not remaining:
            break
        crashes += 1
        culprit = remaining.pop(0)
        records[culprit.key] = _failed(culprit, f"worker exited with code {code} on this song")
        if crashes >= MAX_CRASHES:
            for item in remaining:
                records[item.key] = _failed(
                    item, f"not run: the worker exited with code {code} {crashes} times"
                )
            break
    merged = {
        name: _max(stage.get(name) for stage in stages)
        for name in ("load_seconds", "ram_peak_mb", "torch_peak_mb")
    }
    return records, merged, _max([*peaks, merged["torch_peak_mb"]])


def _launch(
    spec: StepSpec,
    items: Sequence[StageItem],
    keys: dict[str, str],
    cache: Cache,
    paths: BenchPaths,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], int, float | None]:
    """One worker process. Each finished item is cached as soon as its line appears, so a run
    stopped half way (Ctrl+C, a killed terminal) keeps what it already did."""
    paths.data.mkdir(parents=True, exist_ok=True)
    records: dict[str, dict[str, Any]] = {}
    stage: dict[str, Any] = {}

    def collect(lines: list[str]) -> None:
        for line in lines:
            record = json.loads(line)
            if "stage" in record:
                stage.update(record["stage"])
                continue
            records[record["key"]] = record
            if record["error"] is None:
                entry = CacheEntry(output=record["output"], seconds=record["seconds"])
                cache.put(spec.kind, keys[record["key"]], entry)

    with tempfile.TemporaryDirectory(dir=paths.data, prefix="job-") as tmp:
        job, out = Path(tmp) / "job.json", Path(tmp) / "out.jsonl"
        job.write_text(
            json.dumps(
                {
                    "spec": spec.to_json(),
                    "out": str(out),
                    "items": [
                        {
                            "key": item.key,
                            "args": item.args,
                            "work_dir": str(cache.item_dir(spec.kind, keys[item.key])),
                        }
                        for item in items
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        reader = _LineReader(out)
        with GpuSampler() as sampler:
            process = subprocess.Popen([sys.executable, "-m", "karaoke_bench.worker", str(job)])
            try:
                while process.poll() is None:
                    collect(reader.read())
                    time.sleep(POLL_SECONDS)
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait()
                # Also on Ctrl+C: whatever the worker finished is kept.
                collect(reader.read())
    return records, stage, process.returncode, sampler.peak_mb


class _LineReader:
    """Complete lines appended to a file since the last read; a half-written last line waits."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.offset = 0
        self.partial = b""

    def read(self) -> list[str]:
        if not self.path.is_file():
            return []
        with self.path.open("rb") as handle:
            handle.seek(self.offset)
            data = self.partial + handle.read()
            self.offset = handle.tell()
        *lines, self.partial = data.split(b"\n")
        return [line.decode("utf-8") for line in lines if line.strip()]


def _failed(item: StageItem, error: str) -> dict[str, Any]:
    return {"key": item.key, "output": None, "seconds": 0.0, "error": error}


def _max(values: Any) -> float | None:
    present = [v for v in values if v is not None]
    return max(present) if present else None
