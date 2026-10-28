"""Runs one pipeline step over many songs: cache first, then a single worker process.

One process per step keeps a single model on the 4 GB GPU, frees all of it when the step
ends, measures memory per step cleanly, and keeps CUDA libraries of different steps apart.
"""

import json
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from karaoke_bench.cache import Cache, CacheEntry, cache_key
from karaoke_bench.codec import decode_output
from karaoke_bench.paths import BenchPaths
from karaoke_bench.pipeline import StepSpec, step_version
from karaoke_bench.resources import GpuSampler


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
            record = records.get(item.key)
            if record is None:
                outcomes[item.key] = ItemOutcome(item.key, None, 0.0, False, stage["error"])
            elif record["error"]:
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
    paths.data.mkdir(parents=True, exist_ok=True)
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
        with GpuSampler() as sampler:
            process = subprocess.Popen([sys.executable, "-m", "karaoke_bench.worker", str(job)])
            code = process.wait()
        records: dict[str, dict[str, Any]] = {}
        stage: dict[str, Any] = {}
        if out.is_file():
            for line in out.read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                if "stage" in record:
                    stage = record["stage"]
                else:
                    records[record["key"]] = record
    stage["error"] = f"worker exited with code {code}"
    vram = _max([sampler.peak_mb, stage.get("torch_peak_mb")])
    return records, stage, vram


def _max(values: Any) -> float | None:
    present = [v for v in values if v is not None]
    return max(present) if present else None
