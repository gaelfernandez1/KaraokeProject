from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from karaoke.domain.user import User
from karaoke.infra.db.models import Song

_DEFAULT_ORDER = (Song.created_at.desc(), Song.id.desc())


def save_song(session: Session, song_data: dict[str, Any]) -> int:
    song = Song(
        title=song_data.get("title"),
        original_filename=song_data.get("original_filename"),
        karaoke_filename=song_data.get("karaoke_filename"),
        video_only_filename=song_data.get("video_only_filename"),
        vocal_filename=song_data.get("vocal_filename"),
        instrumental_filename=song_data.get("instrumental_filename"),
        source_type=song_data.get("source_type"),
        source_url=song_data.get("source_url"),
        processing_type=song_data.get("processing_type"),
        manual_lyrics=song_data.get("manual_lyrics"),
        language=song_data.get("language"),
        enable_diarization=bool(song_data.get("enable_diarization", False)),
        whisper_model=song_data.get("whisper_model", "small"),
        file_size=song_data.get("file_size"),
        duration=song_data.get("duration"),
        user_id=song_data.get("user_id"),
        storage_key=song_data.get("storage_key"),
    )
    session.add(song)
    session.flush()
    return song.id


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalars(select(User).where(User.email == email)).first()


def get_user_by_id(session: Session, user_id: str) -> User | None:
    return session.get(User, user_id)


def create_user(session: Session, email: str) -> User:
    user = User(email=email)
    session.add(user)
    session.flush()
    return user


def get_all_songs(session: Session, user_id: str | None = None) -> list[Song]:
    stmt = select(Song)
    if user_id is not None:
        stmt = stmt.where(Song.user_id == user_id)
    return list(session.scalars(stmt.order_by(*_DEFAULT_ORDER)))


def get_song_by_id(session: Session, song_id: int) -> Song | None:
    return session.get(Song, song_id)


def get_song_by_filename(session: Session, filename: str) -> Song | None:
    return session.scalars(select(Song).where(Song.karaoke_filename == filename)).first()


def get_song_owning_file(session: Session, filename: str) -> Song | None:
    """Find the song that references filename in any of its artifact columns."""
    stmt = select(Song).where(
        or_(
            Song.karaoke_filename == filename,
            Song.video_only_filename == filename,
            Song.vocal_filename == filename,
            Song.instrumental_filename == filename,
        )
    )
    return session.scalars(stmt).first()


def update_last_played(session: Session, song_id: int) -> None:
    song = session.get(Song, song_id)
    if song is not None:
        song.last_played = datetime.now()


def delete_song(session: Session, song_id: int) -> bool:
    song = session.get(Song, song_id)
    if song is None:
        return False
    session.delete(song)
    session.flush()
    return True


def get_songs_by_search(session: Session, query: str, user_id: str | None = None) -> list[Song]:
    stmt = select(Song).where(Song.title.ilike(f"%{query}%"))
    if user_id is not None:
        stmt = stmt.where(Song.user_id == user_id)
    return list(session.scalars(stmt.order_by(*_DEFAULT_ORDER)))


def get_database_stats(session: Session, user_id: str | None = None) -> dict[str, int]:
    def _scoped(stmt):
        return stmt.where(Song.user_id == user_id) if user_id is not None else stmt

    def _count(processing_type: str) -> int:
        return (
            session.scalar(
                _scoped(
                    select(func.count())
                    .select_from(Song)
                    .where(Song.processing_type == processing_type)
                )
            )
            or 0
        )

    total_songs = session.scalar(_scoped(select(func.count()).select_from(Song))) or 0
    total_size = session.scalar(_scoped(select(func.coalesce(func.sum(Song.file_size), 0)))) or 0

    return {
        "total_songs": total_songs,
        "automatic_songs": _count("automatic"),
        "manual_songs": _count("manual_lyrics"),
        "instrumental_songs": _count("instrumental"),
        "total_size": total_size,
    }
