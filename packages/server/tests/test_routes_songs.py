import json

from karaoke_server.config import Settings
from karaoke_server.db import Database

from .conftest import MakeClient, write_package


def test_songs_list_for_home_but_not_remote(settings: Settings, make_client: MakeClient) -> None:
    write_package(settings.library_dir / "mar-de-vigo")
    home = make_client("home").get("/api/songs")
    assert home.status_code == 200
    assert [s["id"] for s in home.json()] == ["mar-de-vigo"]
    assert set(home.json()[0]) >= {"id", "title", "hook", "has_video", "created_at"}
    remote = make_client("remote").get("/api/songs")
    assert remote.status_code == 403
    assert remote.json()["code"] == "not_paired"
    assert isinstance(remote.json()["detail"], str)


def test_put_doc_needs_owner_and_valid_doc(settings: Settings, make_client: MakeClient) -> None:
    folder = write_package(settings.library_dir / "song")
    doc = json.loads((folder / "karaoke.json").read_text(encoding="utf-8"))
    doc["title"] = "Corrected"
    assert make_client("home").put("/api/songs/song/doc", json=doc).json()["code"] == "not_owner"
    local = make_client("local")
    saved = local.put("/api/songs/song/doc", json=doc)
    assert saved.status_code == 200
    assert saved.json()["edited"] is True
    assert saved.json()["title"] == "Corrected"
    doc["lines"][0]["start"] = 999
    bad = local.put("/api/songs/song/doc", json=doc)
    assert bad.status_code == 422
    assert bad.json()["code"] == "invalid_doc"
    assert local.put("/api/songs/missing/doc", json=doc).status_code == 404


def test_put_doc_rejects_cross_origin(settings: Settings, make_client: MakeClient) -> None:
    folder = write_package(settings.library_dir / "song")
    doc = json.loads((folder / "karaoke.json").read_text(encoding="utf-8"))
    local = make_client("local")
    evil = local.put("/api/songs/song/doc", json=doc, headers={"Origin": "http://evil.example"})
    assert evil.status_code == 403
    assert evil.json()["code"] == "bad_origin"
    ok = local.put(
        "/api/songs/song/doc",
        json=doc,
        headers={"Origin": f"http://localhost:{settings.home_port}"},
    )
    assert ok.status_code == 200


def test_delete_song_goes_to_trash(settings: Settings, make_client: MakeClient) -> None:
    write_package(settings.library_dir / "song")
    assert make_client("home").delete("/api/songs/song").status_code == 403
    local = make_client("local")
    assert local.delete("/api/songs/song").status_code == 204
    assert local.get("/api/songs").json() == []
    assert local.delete("/api/songs/song").status_code == 404
    assert any(settings.trash_dir.iterdir())


def test_open_home_lets_the_home_network_edit(settings: Settings, db: Database) -> None:
    from fastapi.testclient import TestClient

    from karaoke_server.app import build_services, create_app
    from karaoke_server.network import NetworkState

    open_settings = Settings.from_env(data_dir=settings.data_dir, open_home=True)
    write_package(open_settings.library_dir / "song")
    services = build_services(
        open_settings, db=db, network_state=NetworkState(None, None, None, None)
    )
    with TestClient(create_app(open_settings, services=services), client=("192.168.1.9", 1)) as c:
        assert c.delete("/api/songs/song").status_code == 204


def test_unknown_api_route_is_404_json(make_client: MakeClient) -> None:
    response = make_client("local").get("/api/nothing-here")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


def test_security_headers(make_client: MakeClient) -> None:
    response = make_client("local").get("/api/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "same-origin"
