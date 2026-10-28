import pytest

from karaoke.infra.db import session_scope
from karaoke.infra.db.repository import create_user, get_user_by_email


def _login(client, email="basic@example.com"):
    with session_scope() as session:
        user = get_user_by_email(session, email) or create_user(session, email)
        user_id = user.id
    with client.session_transaction() as sess:
        sess["_user_id"] = user_id
        sess["_fresh"] = True


@pytest.mark.integration
class TestBasicRoutes:
    def test_index_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_library_requires_login(self, client):
        response = client.get("/library")
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]

    def test_library_returns_200_when_logged_in(self, client):
        _login(client)
        response = client.get("/library")
        assert response.status_code == 200

    def test_library_search_redirects_on_empty_query(self, client):
        _login(client)
        response = client.get("/library/search?q=")
        assert response.status_code in (302, 308)

    def test_library_search_returns_200_with_query(self, client):
        _login(client)
        response = client.get("/library/search?q=test")
        assert response.status_code == 200
