from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Song(Base):
    __tablename__ = "songs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    karaoke_filename: Mapped[str] = mapped_column(String, nullable=False)
    video_only_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    vocal_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    instrumental_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    processing_type: Mapped[str] = mapped_column(String, nullable=False)
    manual_lyrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    enable_diarization: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    whisper_model: Mapped[str | None] = mapped_column(String, nullable=True, default="small")
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    last_played: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # FK to the song's owner (Fase 10). NULL for rows created before auth existed.
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    # Storage key in the configured backend (e.g. "karaoke/{task_id}/{filename}").
    # NULL for rows created before Fase 8.
    storage_key: Mapped[str | None] = mapped_column(String, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "original_filename": self.original_filename,
            "karaoke_filename": self.karaoke_filename,
            "video_only_filename": self.video_only_filename,
            "vocal_filename": self.vocal_filename,
            "instrumental_filename": self.instrumental_filename,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "processing_type": self.processing_type,
            "manual_lyrics": self.manual_lyrics,
            "language": self.language,
            "enable_diarization": self.enable_diarization,
            "whisper_model": self.whisper_model,
            "file_size": self.file_size,
            "duration": self.duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_played": self.last_played.isoformat() if self.last_played else None,
            "user_id": self.user_id,
            "storage_key": self.storage_key,
        }
