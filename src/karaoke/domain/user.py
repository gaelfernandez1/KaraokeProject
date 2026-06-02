from __future__ import annotations

import uuid
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from karaoke.infra.db.models import Base


class User(Base, UserMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    # FK to the billing plans table introduced in Fase 11; plain nullable column for now.
    plan_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # Shadows UserMixin.is_active with the real DB state so login_user respects it.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
