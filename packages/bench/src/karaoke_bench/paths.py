"""Where the bench keeps its versioned inputs and its local, untracked data."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BenchPaths:
    """Layout under the bench folder (`bench/` at the repo root by default)."""

    root: Path

    @property
    def sets(self) -> Path:
        return self.root / "sets"

    @property
    def pipelines(self) -> Path:
        return self.root / "pipelines"

    @property
    def results(self) -> Path:
        return self.root / "results"

    @property
    def data(self) -> Path:
        """Downloaded audio, caches and raw outputs. Ignored by git."""
        return self.root / "data"

    @property
    def private_results(self) -> Path:
        """Reports of the private set: the user's own songs never reach the versioned results."""
        return self.data / "results"

    @property
    def cache(self) -> Path:
        return self.data / "cache"

    @property
    def runs(self) -> Path:
        return self.data / "runs"
