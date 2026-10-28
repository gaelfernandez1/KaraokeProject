"""Per-step cache: trying another aligner must not redo the separation."""

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from karaoke_bench.files import write_text_atomic
from karaoke_bench.pipeline import StepKind, StepSpec


class CacheEntry(BaseModel):
    output: Any
    seconds: float
    load_seconds: float | None = None
    stage_vram_mb: float | None = None
    stage_ram_mb: float | None = None


def cache_key(spec: StepSpec, version: str, fingerprint: str) -> str:
    canonical = json.dumps(
        {"target": spec.target, "params": spec.params, "version": version, "input": fingerprint},
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


class Cache:
    def __init__(self, root: Path) -> None:
        self.root = root

    def get(self, kind: StepKind, key: str) -> CacheEntry | None:
        path = self.root / kind / f"{key}.json"
        try:
            return CacheEntry.model_validate_json(path.read_bytes())
        except (OSError, ValidationError):
            return None

    def put(self, kind: StepKind, key: str, entry: CacheEntry) -> None:
        write_text_atomic(self.root / kind / f"{key}.json", entry.model_dump_json())

    def item_dir(self, kind: StepKind, key: str) -> Path:
        """Folder for the files a step writes (separated stems), kept with the cache entry."""
        return self.root / kind / key
