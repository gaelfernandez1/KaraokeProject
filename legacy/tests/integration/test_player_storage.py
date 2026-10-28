"""Endpoint wiring for the R2 storage backend.

Runs in CI/worker (needs Flask). The underlying resolution pieces — derive_key
and get_song_owning_file — are unit-tested in test_storage.py / test_repository.py;
here we only check that the routes consult storage and redirect in r2 mode.
"""

import pytest

pytest.importorskip("flask")

from flask import Flask  # noqa: E402
from flask_login import LoginManager, UserMixin  # noqa: E402

from karaoke.api import player  # noqa: E402


class _Settings:
    storage_backend = "r2"


class _FakeUser(UserMixin):
    def __init__(self, user_id):
        self.id = user_id


@pytest.fixture
def client(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test"
    app.config["APP_SETTINGS"] = _Settings()
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.user_loader(lambda user_id: _FakeUser(user_id))
    app.register_blueprint(player.bp)
    # Ownership is exercised in test_authz; here we only assert storage wiring.
    monkeypatch.setattr(player, "_require_owns_file", lambda filename: None)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "u1"
        sess["_fresh"] = True
    return client


@pytest.mark.integration
class TestServeInR2Mode:
    def test_serve_video_redirects_to_signed_url(self, client, monkeypatch):
        monkeypatch.setattr(player, "_signed_url_for", lambda s, f: "https://r2.example/v")
        resp = client.get("/serve_video/karaoke_x.mp4")
        assert resp.status_code == 302
        assert resp.headers["Location"] == "https://r2.example/v"

    def test_serve_audio_redirects_to_signed_url(self, client, monkeypatch):
        monkeypatch.setattr(player, "_signed_url_for", lambda s, f: "https://r2.example/a")
        resp = client.get("/serve_audio/vocal_x.wav")
        assert resp.status_code == 302
        assert resp.headers["Location"] == "https://r2.example/a"

    def test_download_redirects_to_signed_url(self, client, monkeypatch):
        monkeypatch.setattr(player, "_signed_url_for", lambda s, f: "https://r2.example/d")
        resp = client.get("/download/instrumental_x.wav")
        assert resp.status_code == 302
        assert resp.headers["Location"] == "https://r2.example/d"

    def test_unknown_file_returns_404(self, client, monkeypatch):
        monkeypatch.setattr(player, "_signed_url_for", lambda s, f: None)
        resp = client.get("/serve_audio/missing.wav")
        assert resp.status_code == 404
