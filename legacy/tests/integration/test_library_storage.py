"""Library endpoint behavior under the R2 storage backend.

Runs in CI/worker (needs Flask). Verifies that play checks availability via the
DB record (not local disk) and that delete removes every artifact from storage.
"""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")

from flask import Flask  # noqa: E402
from flask_login import LoginManager, UserMixin  # noqa: E402

from karaoke.api import library, player  # noqa: E402


@contextmanager
def _fake_scope():
    yield None


class _FakeUser(UserMixin):
    def __init__(self, user_id):
        self.id = user_id


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(library, "session_scope", _fake_scope)
    app = Flask(__name__)
    app.secret_key = "test"
    app.config["APP_SETTINGS"] = SimpleNamespace(
        storage_backend="r2",
        r2_account_id="acc",
        r2_bucket="bucket",
        r2_access_key_id="key",
        r2_secret_access_key="secret",
    )
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.user_loader(lambda user_id: _FakeUser(user_id))
    app.register_blueprint(library.bp)
    app.register_blueprint(player.bp)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "u1"
        sess["_fresh"] = True
    return client


@pytest.mark.integration
class TestLibraryPlayR2:
    def test_play_redirects_when_storage_key_present(self, client, monkeypatch):
        song = SimpleNamespace(
            karaoke_filename="karaoke_x.mp4", storage_key="karaoke/t/karaoke_x.mp4", user_id="u1"
        )
        monkeypatch.setattr(library, "get_song_by_id", lambda s, i: song)
        monkeypatch.setattr(library, "update_last_played", lambda s, i: None)

        resp = client.get("/library/play/1")

        assert resp.status_code == 302
        assert "/player/karaoke_x.mp4" in resp.headers["Location"]

    def test_play_404_when_storage_key_missing(self, client, monkeypatch):
        song = SimpleNamespace(karaoke_filename="karaoke_x.mp4", storage_key=None, user_id="u1")
        monkeypatch.setattr(library, "get_song_by_id", lambda s, i: song)

        resp = client.get("/library/play/1")

        assert resp.status_code == 404


@pytest.mark.integration
class TestLibraryDeleteR2:
    def test_delete_removes_every_artifact_from_storage(self, client, monkeypatch):
        song = SimpleNamespace(
            title="X",
            karaoke_filename="karaoke_x.mp4",
            video_only_filename="karaoke_x_video_only.mp4",
            vocal_filename="vocal_x.wav",
            instrumental_filename="instrumental_x.wav",
            storage_key="karaoke/task-1/karaoke_x.mp4",
            user_id="u1",
        )
        deleted_keys: list[str] = []

        class FakeStorage:
            def upload(self, local_path, key):
                return key

            def get_signed_url(self, key, expires_in=3600):
                return ""

            def delete(self, key):
                deleted_keys.append(key)

            def exists(self, key):
                return True

        monkeypatch.setattr(library, "get_song_by_id", lambda s, i: song)
        monkeypatch.setattr(library, "delete_song", lambda s, i: True)
        monkeypatch.setattr("karaoke.infra.storage.get_storage", lambda settings: FakeStorage())

        resp = client.post("/library/delete/1")

        assert resp.status_code == 302
        assert set(deleted_keys) == {
            "karaoke/task-1/karaoke_x.mp4",
            "karaoke/task-1/karaoke_x_video_only.mp4",
            "karaoke/task-1/vocal_x.wav",
            "karaoke/task-1/instrumental_x.wav",
        }
