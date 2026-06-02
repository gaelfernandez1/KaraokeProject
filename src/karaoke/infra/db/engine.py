from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from karaoke.config import Settings
from karaoke.infra.db.models import Base

logger = logging.getLogger(__name__)


def create_db_engine(url: str) -> Engine:
    connect_args: dict[str, object] = {}
    kwargs: dict[str, object] = {}
    if url.startswith("sqlite"):
        # Flask serves requests from multiple threads; SQLite needs this relaxed.
        connect_args["check_same_thread"] = False
        if ":memory:" in url:
            # Share a single in-memory DB across connections (tests).
            kwargs["poolclass"] = StaticPool
    return create_engine(url, connect_args=connect_args, future=True, **kwargs)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_db_engine(Settings().database_url)


@lru_cache(maxsize=1)
def _sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


def get_session() -> Session:
    return _sessionmaker()()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create tables from ORM metadata if missing.

    Alembic owns schema migrations; this is a dev/test convenience that is a
    no-op once the tables exist (checkfirst). Production runs `alembic upgrade head`.
    """
    try:
        Base.metadata.create_all(bind=get_engine())
    except (OperationalError, ProgrammingError):
        # gunicorn boots several workers at once; checkfirst isn't atomic across
        # processes, so whoever loses the create race just finds the tables there.
        logger.info("init_db: tables already present (concurrent worker boot)")
