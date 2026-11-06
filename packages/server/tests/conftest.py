import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from karaoke_server.config import Settings
from karaoke_server.db import Database

REPO = Path(__file__).resolve().parents[3]
DEMO = REPO / "fixtures" / "packages" / "demo-sintetico"


def write_package(folder: Path, title: str = "Mar de Vigo", **changes: object) -> Path:
    """A valid package: the demo's karaoke.json with small stand-in media files."""
    folder.mkdir(parents=True, exist_ok=True)
    doc = json.loads((DEMO / "karaoke.json").read_text(encoding="utf-8"))
    doc.update(id=folder.name, title=title, **changes)
    (folder / "karaoke.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    for ref in (doc["audio"]["instrumental"], doc["audio"]["vocals"]):
        (folder / ref).write_bytes(b"RIFF" + bytes(2048))
    return folder


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    s = Settings.from_env(data_dir=tmp_path / "data", web_dir=tmp_path / "web")
    s.ensure_dirs()
    return s


@pytest.fixture
def db(settings: Settings) -> Database:
    database = Database(settings.db_path)
    database.migrate()
    return database


HOME_IP = "192.168.1.20"
REMOTE_IP = "100.85.1.2"


MakeClient = Callable[..., TestClient]


@pytest.fixture
def make_client(settings: Settings, db: Database) -> Iterator[MakeClient]:
    """Clients of one app, as seen from a zone: local (the laptop), home or remote.

    They do not run the app's startup (the job queue stays idle): tests that need it run a real
    server (tests/live.py).
    """
    from karaoke_server.app import build_services, create_app
    from karaoke_server.network import NetworkState

    services = build_services(
        settings, db=db, network_state=NetworkState("mirrored", HOME_IP, None, None)
    )
    app = create_app(settings, services=services)
    opened: list[TestClient] = []

    def make(zone: str = "local", **kwargs: object) -> TestClient:
        host = {"local": "127.0.0.1", "home": HOME_IP, "remote": REMOTE_IP}[zone]
        base = kwargs.pop("base_url", f"http://localhost:{settings.home_port}")
        client = TestClient(app, base_url=str(base), client=(host, 50000), **kwargs)  # type: ignore[arg-type]
        opened.append(client)
        return client

    yield make
    for client in opened:
        client.close()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
