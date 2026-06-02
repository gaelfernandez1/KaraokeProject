# Importing the User model here registers it with Base.metadata so init_db /
# create_all build the users table (it lives in domain to satisfy UserMixin).
from karaoke.domain.user import User
from karaoke.infra.db.engine import (
    create_db_engine,
    get_engine,
    get_session,
    init_db,
    session_scope,
)
from karaoke.infra.db.models import Base, Song

__all__ = [
    "Base",
    "Song",
    "User",
    "create_db_engine",
    "get_engine",
    "get_session",
    "init_db",
    "session_scope",
]
