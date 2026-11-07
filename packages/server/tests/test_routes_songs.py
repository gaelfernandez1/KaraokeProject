import json
import os
from pathlib import Path

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
    # No other site may frame the app: inside a frame, clicks would count as the owner's.
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def _video(folder: Path, name: str, when: float, size: int = 64) -> Path:
    exports = folder / "exports"
    exports.mkdir(exist_ok=True)
    video = exports / name
    video.write_bytes(bytes(size))
    os.utime(video, (when, when))
    return video


def test_song_exports_are_listed_newest_first(settings: Settings, make_client: MakeClient) -> None:
    folder = write_package(settings.library_dir / "mar")
    os.utime(folder / "karaoke.json", (1000, 1000))
    _video(folder, "mar-16x9-clasico.mp4", 2000, size=100)
    (folder / "exports" / "mar-16x9-clasico.jpg").write_bytes(b"jpg")
    _video(folder, "mar-9x16-moderno.mp4", 3000)
    _video(folder, ".partial-mar-16x9-contraste.mp4", 4000)  # still being written
    _video(folder, "notes.mp4", 4000)  # not ours: ignored

    listed = make_client("home").get("/api/songs/mar/exports")

    assert listed.status_code == 200
    assert listed.json() == [
        {
            "file": "exports/mar-9x16-moderno.mp4",
            "aspect": "9:16",
            "theme": "moderno",
            "size": 64,
            "created_at": "1970-01-01T00:50:00Z",
            "thumbnail": None,
            "outdated": False,
            "vocals": 0.0,
        },
        {
            "file": "exports/mar-16x9-clasico.mp4",
            "aspect": "16:9",
            "theme": "clasico",
            "size": 100,
            "created_at": "1970-01-01T00:33:20Z",
            "thumbnail": "exports/mar-16x9-clasico.jpg",
            "outdated": False,
            "vocals": 0.0,
        },
    ]


def test_an_export_made_before_a_correction_is_outdated(
    settings: Settings, make_client: MakeClient
) -> None:
    folder = write_package(settings.library_dir / "mar")
    _video(folder, "mar-16x9-clasico.mp4", 1000)
    os.utime(folder / "karaoke.json", (2000, 2000))
    [video] = make_client("home").get("/api/songs/mar/exports").json()
    assert video["outdated"] is True


def test_song_exports_need_a_reader_and_a_song(settings: Settings, make_client: MakeClient) -> None:
    write_package(settings.library_dir / "mar")
    assert make_client("home").get("/api/songs/mar/exports").json() == []
    assert make_client("remote").get("/api/songs/mar/exports").status_code == 403
    assert make_client("home").get("/api/songs/missing/exports").status_code == 404


def test_owner_deletes_an_export_and_its_thumbnail(
    settings: Settings, make_client: MakeClient
) -> None:
    folder = write_package(settings.library_dir / "mar")
    video = _video(folder, "mar-16x9-clasico.mp4", 1000)
    thumb = folder / "exports" / "mar-16x9-clasico.jpg"
    thumb.write_bytes(b"jpg")
    url = "/api/songs/mar/exports/mar-16x9-clasico.mp4"

    assert make_client("home").delete(url).json()["code"] == "not_owner"
    local = make_client("local")
    assert local.delete(url).status_code == 204
    assert not video.exists()
    assert not thumb.exists()
    assert local.delete(url).status_code == 404
    assert local.delete("/api/songs/mar/exports/..%2Fkaraoke.json").status_code in (404, 405)
    assert local.delete("/api/songs/mar/exports/notes.mp4").status_code == 404
    assert (folder / "karaoke.json").is_file()


def test_exports_say_how_loud_the_guide_vocals_are(
    settings: Settings, make_client: MakeClient
) -> None:
    folder = write_package(settings.library_dir / "mar")
    _video(folder, "mar-16x9-clasico.mp4", 1000)
    _video(folder, "mar-16x9-clasico-v30.mp4", 2000)
    listed = make_client("home").get("/api/songs/mar/exports").json()
    assert [(v["file"], v["theme"], v["vocals"]) for v in listed] == [
        ("exports/mar-16x9-clasico-v30.mp4", "clasico", 0.3),
        ("exports/mar-16x9-clasico.mp4", "clasico", 0.0),
    ]


def test_the_guide_vocals_level_goes_from_0_to_1(
    settings: Settings, make_client: MakeClient
) -> None:
    write_package(settings.library_dir / "mar")
    local = make_client("local")
    too_loud = local.post("/api/songs/mar/exports", json={"vocals": 1.5})
    assert too_loud.status_code == 422
