"""Jobs in the database, as records with everything the queue needs to run or resume them."""

import json
import time
from dataclasses import dataclass, field, fields
from typing import Any

from karaoke_server.db import Database
from karaoke_server.library import iso

TERMINAL = ("done", "error", "cancelled")
_JSON = ("request", "stage_seconds")


@dataclass
class JobRecord:
    id: str
    kind: str
    title: str
    stage: str
    progress: float
    song_id: str | None
    file: str | None
    error: str | None
    error_code: str | None
    with_lyrics: bool
    created_at: str
    updated_at: str
    # When the current stage began (seconds since the epoch).
    stage_started: float | None
    attempt: int
    request: dict[str, Any]
    # The song file on disk, once uploaded or downloaded.
    source: str | None
    # The song's length in seconds, once known.
    duration: float | None
    # Seconds each finished stage took, for the progress estimates.
    stage_seconds: dict[str, float] = field(default_factory=dict)

    @classmethod
    def new(
        cls, job_id: str, kind: str, title: str, request: dict[str, Any], now: float
    ) -> "JobRecord":
        return cls(
            id=job_id,
            kind=kind,
            title=title,
            stage="queued",
            progress=0.0,
            song_id=None,
            file=None,
            error=None,
            error_code=None,
            with_lyrics=kind == "export" or bool((request.get("lyrics") or "").strip()),
            created_at=iso(now),
            updated_at=iso(now),
            stage_started=None,
            attempt=1,
            request=request,
            source=None,
            duration=None,
        )


_COLUMNS = [f.name for f in fields(JobRecord)]


def _to_row(record: JobRecord) -> list[Any]:
    values = []
    for name in _COLUMNS:
        value = getattr(record, name)
        values.append(json.dumps(value) if name in _JSON else value)
    return values


def _from_row(row: Any) -> JobRecord:
    values = {name: row[name] for name in _COLUMNS}
    for name in _JSON:
        values[name] = json.loads(values[name])
    values["with_lyrics"] = bool(values["with_lyrics"])
    return JobRecord(**values)


class JobStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, record: JobRecord) -> None:
        columns, marks = ", ".join(_COLUMNS), ", ".join("?" for _ in _COLUMNS)
        insert = f"INSERT INTO jobs ({columns}) VALUES ({marks})"  # noqa: S608 - names from code
        self.db.execute(insert, _to_row(record))

    def get(self, job_id: str) -> JobRecord | None:
        rows = self.db.query("SELECT * FROM jobs WHERE id = ?", (job_id,))
        return _from_row(rows[0]) if rows else None

    def update(self, job_id: str, **changes: Any) -> JobRecord | None:
        record = self.get(job_id)
        if record is None:
            return None
        for key, value in changes.items():
            setattr(record, key, value)
        record.updated_at = iso(time.time())
        sets = ", ".join(f"{name} = ?" for name in _COLUMNS[1:])
        self.db.execute(f"UPDATE jobs SET {sets} WHERE id = ?", [*_to_row(record)[1:], job_id])  # noqa: S608 - column names come from code
        return record

    def recent(self, limit: int = 50) -> list[JobRecord]:
        rows = self.db.query(
            "SELECT * FROM jobs ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,)
        )
        return [_from_row(row) for row in rows]

    def next_for_gpu(self) -> JobRecord | None:
        rows = self.db.query(
            "SELECT * FROM jobs WHERE stage = 'queued' AND (kind = 'export' OR source IS NOT NULL) "
            "ORDER BY created_at, rowid LIMIT 1"
        )
        return _from_row(rows[0]) if rows else None

    def next_for_download(self) -> JobRecord | None:
        rows = self.db.query(
            "SELECT * FROM jobs WHERE stage = 'queued' AND kind = 'make' AND source IS NULL "
            "AND json_extract(request, '$.url') IS NOT NULL ORDER BY created_at, rowid LIMIT 1"
        )
        return _from_row(rows[0]) if rows else None

    def unfinished(self) -> list[JobRecord]:
        rows = self.db.query(
            "SELECT * FROM jobs WHERE stage NOT IN ('done', 'error', 'cancelled') "
            "ORDER BY created_at, rowid"
        )
        return [_from_row(row) for row in rows]

    def finished_before(self, timestamp: str) -> list[JobRecord]:
        rows = self.db.query(
            "SELECT * FROM jobs WHERE stage IN ('done', 'error', 'cancelled') AND updated_at < ?",
            (timestamp,),
        )
        return [_from_row(row) for row in rows]

    def stage_history(self, stage: str, last: int = 20) -> list[float]:
        """Seconds per second of song that `stage` took in the latest finished jobs."""
        rows = self.db.query(
            "SELECT duration, json_extract(stage_seconds, '$.' || ?) AS seconds FROM jobs "
            "WHERE stage = 'done' AND duration > 0 AND seconds IS NOT NULL "
            "ORDER BY updated_at DESC LIMIT ?",
            (stage, last),
        )
        return [float(row["seconds"]) / float(row["duration"]) for row in rows]
