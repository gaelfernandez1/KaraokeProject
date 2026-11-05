import sqlite3
from pathlib import Path

import pytest

from karaoke_server.db import Database


def test_migrate_creates_tables_once(tmp_path: Path) -> None:
    db = Database(tmp_path / "k.db")
    db.migrate()
    db.migrate()
    assert db.query("PRAGMA user_version")[0][0] == 1
    tables = {row[0] for row in db.query("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"songs", "jobs", "devices", "parties"} <= tables


def test_uses_write_ahead_logging(tmp_path: Path) -> None:
    db = Database(tmp_path / "k.db")
    db.migrate()
    assert db.query("PRAGMA journal_mode")[0][0] == "wal"


def test_transaction_rolls_back_on_error(tmp_path: Path) -> None:
    db = Database(tmp_path / "k.db")
    db.migrate()

    def insert_then_fail() -> None:
        with db.transaction():
            db.execute("INSERT INTO songs (id, created_at) VALUES ('a', '2026-10-31T00:00:00Z')")
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        insert_then_fail()
    assert db.query("SELECT count(*) FROM songs")[0][0] == 0


def test_rows_read_by_name(tmp_path: Path) -> None:
    db = Database(tmp_path / "k.db")
    db.migrate()
    db.execute("INSERT INTO songs (id, created_at) VALUES (?, ?)", ("a", "2026"))
    assert db.query("SELECT id, created_at FROM songs")[0]["id"] == "a"


def test_backup_copies_a_consistent_db(tmp_path: Path) -> None:
    db = Database(tmp_path / "k.db")
    db.migrate()
    db.execute("INSERT INTO songs (id, created_at) VALUES ('a', '2026')")
    db.backup(tmp_path / "copy.db")
    copy = sqlite3.connect(tmp_path / "copy.db")
    assert copy.execute("SELECT id FROM songs").fetchall() == [("a",)]


def test_backup_reads_through_a_connection_of_its_own(tmp_path: Path) -> None:
    # It runs in a worker thread while the server keeps using its own connection.
    db = Database(tmp_path / "k.db")
    db.migrate()
    db.execute("INSERT INTO songs (id, created_at) VALUES ('a', '2026')")
    with db.transaction():
        db.execute("INSERT INTO songs (id, created_at) VALUES ('b', '2026')")
        db.backup(tmp_path / "copy.db")
    copy = sqlite3.connect(tmp_path / "copy.db")
    assert copy.execute("SELECT id FROM songs").fetchall() == [("a",)]
