"""Runs one step over several items in its own process: `python -m karaoke_bench.worker job.json`.

Writes one JSON line per item as soon as it is done, so a crash keeps the finished ones, and a
last line with the stage's load time and memory peaks.
"""

import json
import resource
import sys
import time
from pathlib import Path
from typing import IO, Any

from karaoke_bench.codec import encode_output, invoke
from karaoke_bench.pipeline import StepSpec, build_step


def main(argv: list[str]) -> int:
    job = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    spec = StepSpec.from_json(job["spec"])
    with Path(job["out"]).open("w", encoding="utf-8") as out:
        load_seconds = None
        try:
            started = time.perf_counter()
            step = build_step(spec)
            if callable(getattr(step, "load", None)):
                step.load()
                load_seconds = time.perf_counter() - started
        except Exception as exc:
            for item in job["items"]:
                _write(out, {"key": item["key"], "output": None, "seconds": 0.0,
                             "error": f"could not build the step: {_describe(exc)}"})  # fmt: skip
            return 0
        for item in job["items"]:
            _write(out, _run_item(spec, step, item))
        _write(out, {"stage": {"load_seconds": load_seconds, "ram_peak_mb": _ram_peak_mb(),
                               "torch_peak_mb": _torch_peak_mb()}})  # fmt: skip
    return 0


def _run_item(spec: StepSpec, step: Any, item: dict[str, Any]) -> dict[str, Any]:
    work_dir = Path(item["work_dir"])
    if spec.kind == "separator":
        work_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    try:
        output = encode_output(spec.kind, invoke(spec.kind, step, item["args"], work_dir))
    except Exception as exc:
        return {"key": item["key"], "output": None, "seconds": 0.0, "error": _describe(exc)}
    return {"key": item["key"], "output": output, "seconds": time.perf_counter() - started,
            "error": None}  # fmt: skip


def _write(out: IO[str], record: dict[str, Any]) -> None:
    out.write(json.dumps(record, ensure_ascii=False) + "\n")
    out.flush()


def _describe(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def _ram_peak_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # KiB on Linux


def _torch_peak_mb() -> float | None:
    torch = sys.modules.get("torch")
    if torch is None or not torch.cuda.is_initialized():
        return None
    return float(torch.cuda.max_memory_allocated()) / 2**20


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
