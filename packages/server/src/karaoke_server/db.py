"""The server's SQLite database: the song index, jobs, paired devices and party rooms.

The package folders on disk are the truth about songs; the database only adds what a folder
cannot say (when it was made, by which job). Every call runs on the event loop's thread and
takes well under a millisecond, so one connection is enough.
"""

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

# Each entry upgrades the schema by one version; PRAGMA user_version says how many have run.
MIGRATIONS: list[str] = [
    """
    CREATE TABLE songs (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        job_id TEXT
    );
    CREATE TABLE jobs (
        id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        title TEXT NOT NULL,
        stage TEXT NOT NULL,
        progress REAL NOT NULL DEFAULT 0,
        song_id TEXT,
        file TEXT,
        error TEXT,
        error_code TEXT,
        with_lyrics INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        stage_started REAL,
        attempt INTEGER NOT NULL DEFAULT 1,
        request TEXT NOT NULL,
        source TEXT,
        duration REAL,
        stage_seconds TEXT NOT NULL DEFAULT '{}'
    );
    CREATE INDEX jobs_by_stage ON jobs (stage, created_at);
    CREATE TABLE devices (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        token_hash TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL,
        last_seen TEXT NOT NULL
    );
    CREATE TABLE pairings (
        code TEXT PRIMARY KEY,
        expires_at REAL NOT NULL
    );
    CREATE TABLE parties (
        code TEXT PRIMARY KEY,
        data TEXT NOT NULL,
        updated_at REAL NOT NULL
    );
    """,
]


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None: autocommit, with explicit transactions where several rows change.
        self._conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._depth = 0

    def migrate(self) -> None:
        version = int(self._conn.execute("PRAGMA user_version").fetchone()[0])
        for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
            with self.transaction():
                for statement in script.split(";"):
                    if statement.strip():
                        self._conn.execute(statement)
                self._conn.execute(f"PRAGMA user_version = {number}")

    def execute(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> int:
        """Runs one statement; returns the number of rows it changed."""
        return self._conn.execute(sql, params).rowcount

    def query(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> list[sqlite3.Row]:
        return self._conn.execute(sql, params).fetchall()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if self._depth:
            # Nested: the outer transaction commits or rolls back everything.
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
            return
        self._conn.execute("BEGIN IMMEDIATE")
        self._depth = 1
        try:
            yield
        except BaseException:
            self._conn.execute("ROLLBACK")
            raise
        else:
            self._conn.execute("COMMIT")
        finally:
            self._depth = 0

    def backup(self, dest: Path) -> None:
        """A consistent copy while the server keeps running.

        It reads through a connection of its own: it runs in a worker thread, and the server's
        connection belongs to the event loop (and may be inside a transaction).
        """
        dest.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(self.path)
        target = sqlite3.connect(dest)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

    def close(self) -> None:
        self._conn.close()
