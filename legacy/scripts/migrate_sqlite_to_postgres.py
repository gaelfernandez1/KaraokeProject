"""One-shot import of the legacy SQLite library into the target database.

Reads every row from the old ``db/karaoke_songs.db`` SQLite file and inserts it
into whatever ``DATABASE_URL`` (Settings) points at — normally Postgres. Run it
once after `alembic upgrade head`; it is idempotent (a song already present,
matched by ``karaoke_filename``, is skipped) so re-running is safe.

    python scripts/migrate_sqlite_to_postgres.py [path/to/karaoke_songs.db]

It is NOT wired into application startup on purpose.
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from datetime import datetime

from karaoke.infra.db import session_scope
from karaoke.infra.db.models import Song
from karaoke.infra.db.repository import get_song_by_filename

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("migrate_sqlite_to_postgres")

DEFAULT_SQLITE_PATH = "db/karaoke_songs.db"

# Legacy SQLite columns that map 1:1 onto Song attributes.
_COLUMNS = (
    "title",
    "original_filename",
    "karaoke_filename",
    "video_only_filename",
    "vocal_filename",
    "instrumental_filename",
    "source_type",
    "source_url",
    "processing_type",
    "manual_lyrics",
    "language",
    "enable_diarization",
    "whisper_model",
    "file_size",
    "duration",
)


def _parse_dt(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace(" ", "T"))
    except ValueError:
        return None


def _row_to_song(row: sqlite3.Row, existing_columns: set[str]) -> Song:
    data = {col: row[col] for col in _COLUMNS if col in existing_columns}
    if "enable_diarization" in data:
        data["enable_diarization"] = bool(data["enable_diarization"])
    song = Song(**data)
    if "created_at" in existing_columns:
        parsed = _parse_dt(row["created_at"])
        if parsed is not None:
            song.created_at = parsed
    if "last_played" in existing_columns:
        song.last_played = _parse_dt(row["last_played"])
    return song


def migrate(sqlite_path: str) -> tuple[int, int]:
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute("SELECT * FROM songs ORDER BY id")
        existing_columns = {d[0] for d in cursor.description}
        rows = cursor.fetchall()
    finally:
        conn.close()

    inserted = 0
    skipped = 0
    with session_scope() as session:
        for row in rows:
            filename = row["karaoke_filename"]
            if get_song_by_filename(session, filename) is not None:
                logger.info("skip (already present): %s", filename)
                skipped += 1
                continue
            session.add(_row_to_song(row, existing_columns))
            inserted += 1
            logger.info("insert: %s", filename)

    return inserted, skipped


def main() -> int:
    sqlite_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SQLITE_PATH
    logger.info("Importing songs from %s", sqlite_path)
    inserted, skipped = migrate(sqlite_path)
    logger.info("Done. inserted=%d skipped=%d", inserted, skipped)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
