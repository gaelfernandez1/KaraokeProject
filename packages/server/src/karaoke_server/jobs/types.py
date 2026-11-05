"""What the job queue needs from the outside: a way to run the engine and a downloader."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from karaoke_server.models import ErrorCode

Event = dict[str, Any]


@dataclass(frozen=True)
class Outcome:
    ok: bool
    code: ErrorCode | None = None
    message: str | None = None
    # Worth trying again (out of memory, a crash), unlike a problem with the song itself.
    transient: bool = False
    result: dict[str, Any] = field(default_factory=dict)


class Spawner(Protocol):
    async def run(
        self, job_id: str, spec: dict[str, Any], log: Path, on_event: Callable[[Event], None]
    ) -> Outcome:
        """Runs one job to the end; cancelling the awaiting task stops it."""
        ...


@dataclass(frozen=True)
class RemoteInfo:
    title: str | None
    artist: str | None
    track: str | None
    duration: float | None
    is_live: bool
    # Files the download is made of: video and audio apart are two.
    parts: int = 1


class DownloadError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code: ErrorCode = code


class Downloader(Protocol):
    async def probe(self, url: str) -> RemoteInfo: ...

    async def download(
        self, url: str, dest: Path, on_progress: Callable[[float], None], parts: int = 1
    ) -> Path: ...
