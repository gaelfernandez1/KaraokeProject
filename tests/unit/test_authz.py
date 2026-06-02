from karaoke.infra.db import session_scope
from karaoke.infra.db.repository import create_user, save_song


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = user_id
        sess["_fresh"] = True


def _make_user(email):
    with session_scope() as session:
        return create_user(session, email).id


def _make_song(title, filename, user_id):
    with session_scope() as session:
        return save_song(
            session,
            {
                "title": title,
                "original_filename": "orig.mp4",
                "karaoke_filename": filename,
                "source_type": "upload",
                "processing_type": "automatic",
                "user_id": user_id,
            },
        )


class TestRouteProtection:
    def test_library_requires_login(self, client):
        resp = client.get("/library")
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]

    def test_serve_video_requires_login(self, client):
        resp = client.get("/serve_video/whatever.mp4")
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]

    def test_task_status_requires_login(self, client):
        resp = client.get("/api/task_status/task-1")
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]


class TestOwnershipIsolation:
    def test_library_only_shows_own_songs(self, client):
        a = _make_user("owner-a@example.com")
        b = _make_user("owner-b@example.com")
        _make_song("Alice Secret Song", "karaoke_alice.mp4", a)
        _login(client, b)
        resp = client.get("/library")
        assert resp.status_code == 200
        assert b"Alice Secret Song" not in resp.data

    def test_serve_video_blocks_non_owner(self, client):
        a = _make_user("owner-a2@example.com")
        b = _make_user("owner-b2@example.com")
        _make_song("Alice Song", "karaoke_alice2.mp4", a)
        _login(client, b)
        resp = client.get("/serve_video/karaoke_alice2.mp4")
        assert resp.status_code == 403

    def test_owner_passes_ownership_check(self, client):
        a = _make_user("owner-a3@example.com")
        _make_song("Alice Song", "karaoke_alice3.mp4", a)
        _login(client, a)
        # Ownership passes; the file isn't on disk so we get 404, not 403.
        resp = client.get("/serve_video/karaoke_alice3.mp4")
        assert resp.status_code == 404


class TestTaskOwnership:
    def test_task_status_blocks_non_owner(self, client, mocker):
        a = _make_user("t-a@example.com")
        b = _make_user("t-b@example.com")
        mocker.patch("karaoke.api.tasks.get_task_owner", return_value=a)
        _login(client, b)
        resp = client.get("/api/task_status/task-xyz")
        assert resp.status_code == 403
