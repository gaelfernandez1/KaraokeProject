import os
import tempfile
from pathlib import Path

import pytest


def pytest_configure(config):
    """Set env vars and patch database path before any karaoke module is imported.

    pytest_configure fires before test collection, so these side effects happen
    before any test file triggers an import of karaoke.api.app (which has
    module-level calls to init_database and setup_security).
    """
    os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key-for-ci-only")
    # Flask-Limiter reads REDIS_URL; "memory://" keeps tests self-contained.
    os.environ.setdefault("REDIS_URL", "memory://")

    import karaoke.infra.database as _db

    _db.DATABASE_PATH = os.path.join(tempfile.mkdtemp(), "test_ci.db")


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(scope="session")
def sample_srt_path() -> str:
    return str(FIXTURES_DIR / "sample.srt")


@pytest.fixture(scope="session")
def sample_speakers_srt_path() -> str:
    return str(FIXTURES_DIR / "sample_speakers.srt")


@pytest.fixture(scope="session")
def sample_lyrics_text() -> str:
    return (FIXTURES_DIR / "sample_lyrics.txt").read_text()


@pytest.fixture
def db_session():
    """In-memory SQLAlchemy session with a fresh schema, for fast repository tests."""
    from sqlalchemy.orm import Session

    from karaoke.infra.db.engine import create_db_engine
    from karaoke.infra.db.models import Base

    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def flask_app():
    from karaoke.api.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()
