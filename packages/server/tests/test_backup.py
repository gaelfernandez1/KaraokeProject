import os
import sqlite3
import time
from pathlib import Path

import pytest

from karaoke_server.backup import backup
from karaoke_server.config import Settings
from karaoke_server.db import Database

from .conftest import write_package


def test_backup_is_incremental_and_skips_exports(
    settings: Settings, db: Database, tmp_path: Path
) -> None:
    song = write_package(settings.library_dir / "song")
    (song / "exports").mkdir()
    (song / "exports" / "song-16x9-clasico.mp4").write_bytes(b"mp4")
    (song / ".make-1").mkdir()
    (song / ".make-1" / "mix.wav").write_bytes(b"x")
    dest = tmp_path / "copies"
    first = backup(settings, db, dest)
    assert first.copied == 3
    assert (dest / "library" / "song" / "karaoke.json").is_file()
    assert not (dest / "library" / "song" / "exports").exists()
    assert not (dest / "library" / "song" / ".make-1").exists()
    assert sqlite3.connect(dest / "karaoke.db").execute("SELECT count(*) FROM jobs").fetchone() == (
        0,
    )
    second = backup(settings, db, dest)
    assert (second.copied, second.skipped) == (0, 3)
    later = time.time() + 10
    (song / "karaoke.json").write_text((song / "karaoke.json").read_text() + " ")
    os.utime(song / "karaoke.json", (later, later))
    assert backup(settings, db, dest).copied == 1


def test_backup_moves_deleted_songs_aside(settings: Settings, db: Database, tmp_path: Path) -> None:
    write_package(settings.library_dir / "song")
    dest = tmp_path / "copies"
    backup(settings, db, dest)
    import shutil

    shutil.rmtree(settings.library_dir / "song")
    report = backup(settings, db, dest)
    assert report.removed == 3
    assert not (dest / "library" / "song").exists()
    kept = list((dest / "_borrado").rglob("karaoke.json"))
    assert len(kept) == 1


@pytest.mark.anyio
async def test_daily_backup_keeps_going_after_a_database_error(
    settings: Settings, db: Database, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio
    import sqlite3
    from types import SimpleNamespace

    from karaoke_server import backup as module

    def broken(*args: object) -> None:
        raise sqlite3.OperationalError("database is locked")

    waits: list[float] = []

    async def sleep(seconds: float) -> None:
        waits.append(seconds)
        raise asyncio.CancelledError

    monkeypatch.setattr(module, "backup", broken)
    monkeypatch.setattr(
        module, "asyncio", SimpleNamespace(sleep=sleep, to_thread=asyncio.to_thread)
    )
    with_copies = Settings.from_env(data_dir=settings.data_dir, backup_dir=tmp_path / "copies")
    with pytest.raises(asyncio.CancelledError):
        await module.backup_daily(with_copies, db)
    assert waits == [3600]
