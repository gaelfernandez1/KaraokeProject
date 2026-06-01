from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(_PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_PROJECT_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


@pytest.fixture
def db_url(tmp_path) -> str:
    return f"sqlite:///{tmp_path / 'migration_test.db'}"


def _tables(db_url: str) -> set[str]:
    engine = create_engine(db_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_creates_songs_table(db_url):
    command.upgrade(_alembic_config(db_url), "head")
    assert "songs" in _tables(db_url)


def test_full_downgrade_drops_songs_table(db_url):
    cfg = _alembic_config(db_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    assert "songs" not in _tables(db_url)


def test_roundtrip_is_idempotent(db_url):
    """upgrade -> downgrade -> upgrade leaves the same schema."""
    cfg = _alembic_config(db_url)
    command.upgrade(cfg, "head")
    after_first = _tables(db_url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    after_second = _tables(db_url)
    assert after_first == after_second
    assert "songs" in after_second
