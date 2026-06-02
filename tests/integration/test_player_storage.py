"""Endpoint wiring for the R2 storage backend.

Runs in CI/worker (needs Flask). The underlying resolution pieces — derive_key
and get_song_owning_file — are unit-tested in test_storage.py / test_repository.py;
here we only check that the routes consult storage and redirect in r2 mode.
"""

import pytest

pytest.importorskip("flask")

from flask import Flask  # noqa: E402

from karaoke.api import player  # noqa: E402


class _Settings:
    storage_backend = "r2"


@pytest.fixture
def client(monkeypatch):
    app = Flask(__name__)
    app.config["APP_SETTINGS"] = _Settings()
    app.register_blueprint(player.bp)
    return app.test_client()


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
