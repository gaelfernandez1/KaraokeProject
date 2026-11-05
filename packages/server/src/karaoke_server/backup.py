"""Copies of the library: the database and every song, incrementally, somewhere safe.

Exported videos are left out (they can be made again). A song gone from the library is not
deleted from the copy but moved to `_borrado/<date>/`, in case it was a mistake.
"""

import asyncio
import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from karaoke_server.config import Settings
from karaoke_server.db import Database

logger = logging.getLogger(__name__)

DAY = 86400
MARKER = ".last-backup"
# Windows file systems keep times less precisely than Linux.
MTIME_SLACK = 2.0


@dataclass
class BackupReport:
    copied: int = 0
    skipped: int = 0
    removed: int = 0
    bytes: int = 0


def _library_files(root: Path) -> dict[Path, Path]:
    files = {}
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(part.startswith(".") for part in rel.parts) or "exports" in rel.parts[1:2]:
            continue
        if path.is_file():
            files[rel] = path
    return files


def backup(settings: Settings, db: Database, dest: Path) -> BackupReport:
    dest.mkdir(parents=True, exist_ok=True)
    report = BackupReport()
    db.backup(dest / "karaoke.db")
    target = dest / "library"
    source_files = _library_files(settings.library_dir)
    for rel, path in source_files.items():
        copy = target / rel
        stat = path.stat()
        if copy.is_file():
            old = copy.stat()
            if old.st_size == stat.st_size and abs(old.st_mtime - stat.st_mtime) <= MTIME_SLACK:
                report.skipped += 1
                continue
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, copy)
        report.copied += 1
        report.bytes += stat.st_size
    if target.is_dir():
        aside = dest / "_borrado" / time.strftime("%Y-%m-%d")
        for rel in sorted(set(_library_files(target)) - set(source_files)):
            moved = aside / rel
            moved.parent.mkdir(parents=True, exist_ok=True)
            (target / rel).replace(moved)
            report.removed += 1
        for folder in sorted(target.glob("*/"), reverse=True):
            if folder.is_dir() and not any(folder.rglob("*")):
                folder.rmdir()
    (dest / MARKER).write_text(str(time.time()), encoding="utf-8")
    return report


async def backup_daily(settings: Settings, db: Database) -> None:
    """Copies to `backup_dir` once a day while the server runs (and at start if one is due)."""
    dest = settings.backup_dir
    if dest is None:
        return
    while True:
        try:
            last = float((dest / MARKER).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            last = 0.0
        wait = last + DAY - time.time()
        if wait > 0:
            await asyncio.sleep(wait)
            continue
        try:
            report = await asyncio.to_thread(backup, settings, db, dest)
            logger.info("backup done: %s files copied, %s removed", report.copied, report.removed)
        except Exception:
            # A full disk, a missing drive or a busy database: try again later, never give up.
            logger.exception("the backup to %s failed; trying again in an hour", dest)
            await asyncio.sleep(3600)
