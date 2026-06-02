from datetime import datetime, timedelta

import pytest
from itsdangerous import URLSafeTimedSerializer

from karaoke.infra.db import session_scope
from karaoke.infra.db.repository import get_user_by_email


def _serializer(app):
    return URLSafeTimedSerializer(app.secret_key, salt="magic-login")


@pytest.fixture
def resend_send(mocker):
    return mocker.patch("resend.Emails.send", return_value={"id": "mail-1"})


class TestLogin:
    def test_login_get_renders_form(self, client):
        resp = client.get("/auth/login")
        assert resp.status_code == 200

    def test_login_sends_magic_link_when_configured(self, flask_app, client, resend_send):
        flask_app.config["APP_SETTINGS"].resend_api_key = "re_test"
        resp = client.post("/auth/login", data={"email": "alice@example.com"})
        assert resp.status_code == 200
        resend_send.assert_called_once()

    def test_login_returns_generic_200_without_resend_key(self, flask_app, client, resend_send):
        flask_app.config["APP_SETTINGS"].resend_api_key = None
        resp = client.post("/auth/login", data={"email": "bob@example.com"})
        assert resp.status_code == 200
        resend_send.assert_not_called()


class TestVerify:
    def test_valid_token_logs_in_and_creates_user(self, flask_app, client):
        token = _serializer(flask_app).dumps("carol@example.com")
        resp = client.get(f"/auth/verify/{token}")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/")
        with session_scope() as session:
            assert get_user_by_email(session, "carol@example.com") is not None

    def test_expired_token_shows_error_without_crashing(self, flask_app, client):
        # Sign the token 20 minutes in the past so the 15 min max_age has elapsed.
        with _frozen(datetime.now() - timedelta(minutes=20)):
            token = _serializer(flask_app).dumps("dave@example.com")
        resp = client.get(f"/auth/verify/{token}")
        assert resp.status_code == 200
        with session_scope() as session:
            assert get_user_by_email(session, "dave@example.com") is None

    def test_garbage_token_shows_error(self, client):
        resp = client.get("/auth/verify/not-a-real-token")
        assert resp.status_code == 200


class TestLogout:
    def test_logout_redirects_home(self, client):
        resp = client.get("/auth/logout")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/")


# Minimal time-freeze helper (freezegun) kept local so the intent reads inline.
def _frozen(when):
    from freezegun import freeze_time

    return freeze_time(when)
