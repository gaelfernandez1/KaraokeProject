import pytest


@pytest.mark.integration
class TestBasicRoutes:
    def test_index_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_library_returns_200(self, client):
        response = client.get("/library")
        assert response.status_code == 200

    def test_library_search_redirects_on_empty_query(self, client):
        response = client.get("/library/search?q=")
        assert response.status_code in (302, 308)

    def test_library_search_returns_200_with_query(self, client):
        response = client.get("/library/search?q=test")
        assert response.status_code == 200
