from pathlib import Path

import pytest

from karaoke_server.config import Settings


def test_from_env_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("KARAOKE_DATA", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    settings = Settings.from_env()
    assert settings.data_dir == tmp_path / "karaoke"
    assert (settings.home_port, settings.tunnel_port) == (8765, 8766)
    assert settings.max_upload_bytes == 2 * 1024**3
    assert settings.max_duration == 1200.0
    assert settings.min_free_bytes == 2 * 1024**3
    assert not settings.open_home
    assert not settings.fake_engine


def test_from_env_reads_data_dir_and_flags(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KARAOKE_DATA", str(tmp_path / "data"))
    monkeypatch.setenv("KARAOKE_PORT", "9000")
    monkeypatch.setenv("KARAOKE_OPEN_HOME", "1")
    monkeypatch.setenv("KARAOKE_FAKE_ENGINE", "true")
    settings = Settings.from_env()
    assert settings.data_dir == tmp_path / "data"
    assert (settings.home_port, settings.tunnel_port) == (9000, 9001)
    assert settings.open_home
    assert settings.fake_engine


def test_overrides_win_over_the_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("KARAOKE_DATA", str(tmp_path / "env"))
    settings = Settings.from_env(data_dir=tmp_path / "given", max_duration=5.0)
    assert settings.data_dir == tmp_path / "given"
    assert settings.max_duration == 5.0


def test_ensure_dirs_creates_the_layout(tmp_path: Path) -> None:
    settings = Settings.from_env(data_dir=tmp_path / "d")
    settings.ensure_dirs()
    for path in (
        settings.library_dir,
        settings.jobs_dir,
        settings.trash_dir,
        settings.tmp_dir,
        settings.logs_dir,
    ):
        assert path.is_dir()
    assert settings.db_path == tmp_path / "d" / "karaoke.db"
