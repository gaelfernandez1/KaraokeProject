"""Requests generated from the server's own OpenAPI: whatever a phone or a script sends, the
server answers with an error it means (4xx), never a crash (5xx)."""

from collections.abc import Callable
from typing import Any

import pytest
import schemathesis
from hypothesis import HealthCheck, settings

from karaoke_server.config import Settings
from karaoke_server.db import Database

from .conftest import HOME_IP, write_package

ASGI = Callable[[dict[str, Any], Any, Any], Any]


def _seen_from(app: ASGI, host: str, port: int) -> ASGI:
    """The app as a client at `host` sees it (the zones come from the client and the port)."""

    async def wrapped(scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            scope = {**scope, "client": (host, 50000), "server": ("localhost", port)}
        await app(scope, receive, send)

    return wrapped


def _schema(settings: Settings, db: Database, host: str) -> Any:
    from karaoke_server.app import build_services, create_app
    from karaoke_server.network import NetworkState

    write_package(settings.library_dir / "song")
    services = build_services(
        settings, db=db, network_state=NetworkState("mirrored", HOME_IP, None, None)
    )
    app = _seen_from(create_app(settings, services=services), host, settings.home_port)
    schema = schemathesis.openapi.from_asgi("/openapi.json", app)
    # Live streams never end, and a link job would go out to the internet: left out here, they
    # have their own tests.
    return schema.exclude(path_regex=r"/events$").exclude(method="POST", path="/api/jobs")


@pytest.fixture(params=["127.0.0.1", HOME_IP], ids=["owner", "home-guest"])
def api(request: pytest.FixtureRequest, settings: Settings, db: Database) -> Any:
    return _schema(settings, db, request.param)


schema = schemathesis.pytest.from_fixture("api")


@schema.parametrize()
@settings(
    max_examples=12,
    derandomize=True,
    deadline=None,
    suppress_health_check=list(HealthCheck),
)
def test_no_request_crashes_the_server(case: Any, settings: Settings) -> None:
    origin = f"http://localhost:{settings.home_port}"
    response = case.call(headers={"Origin": origin, "Host": f"localhost:{settings.home_port}"})
    assert response.status_code < 500, (
        f"{case.method} {case.formatted_path} → {response.status_code}: {response.text[:300]}"
    )
