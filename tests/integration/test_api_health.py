import pytest


@pytest.mark.integration
class TestHealthEndpoint:
    def test_health_ok_when_dependencies_up(self, client, monkeypatch):
        monkeypatch.setattr("karaoke.api.health._check_redis", lambda: True)
        monkeypatch.setattr("karaoke.api.health._check_database", lambda: True)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert data["checks"] == {"redis": True, "database": True}

    def test_health_degraded_when_redis_down(self, client, monkeypatch):
        monkeypatch.setattr("karaoke.api.health._check_redis", lambda: False)
        monkeypatch.setattr("karaoke.api.health._check_database", lambda: True)
        response = client.get("/health")
        assert response.status_code == 503
        data = response.get_json()
        assert data["status"] == "degraded"
        assert data["checks"]["redis"] is False

    def test_health_reports_each_dependency(self, client):
        # No mocking: the shape must hold whatever the real check results are.
        response = client.get("/health")
        data = response.get_json()
        assert data is not None
        assert "status" in data
        assert set(data["checks"]) == {"redis", "database"}
