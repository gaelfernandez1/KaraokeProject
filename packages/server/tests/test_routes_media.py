import pytest

from karaoke_server.config import Settings

from .conftest import MakeClient, write_package


def test_media_supports_ranges(settings: Settings, make_client: MakeClient) -> None:
    folder = write_package(settings.library_dir / "song")
    (folder / "background.mp4").write_bytes(bytes(range(256)) * 4)
    client = make_client("home")
    whole = client.get("/media/song/background.mp4")
    assert whole.status_code == 200
    assert whole.headers["accept-ranges"] == "bytes"
    assert whole.headers["content-type"] == "video/mp4"
    part = client.get("/media/song/background.mp4", headers={"Range": "bytes=10-19"})
    assert part.status_code == 206
    assert part.headers["content-range"] == "bytes 10-19/1024"
    assert part.content == bytes(range(10, 20))
    beyond = client.get("/media/song/background.mp4", headers={"Range": "bytes=5000-6000"})
    assert beyond.status_code == 416


def test_karaoke_json_comes_from_the_document(settings: Settings, make_client: MakeClient) -> None:
    write_package(settings.library_dir / "song", title="Mar")
    response = make_client("home").get("/media/song/karaoke.json")
    assert response.status_code == 200
    assert response.json()["title"] == "Mar"
    assert response.json()["id"] == "song"
    assert response.headers["cache-control"] == "no-cache"


@pytest.mark.parametrize(
    "path",
    [
        "/media/song/%2e%2e/%2e%2e/karaoke.db",
        "/media/song/.make-1/a.wav",
        "/media/song/karaoke.original.json",
        "/media/song/link.wav",
        "/media/song/..%2Fkaraoke.db",
        "/media/SONG/instrumental.wav",
        "/media/song/",
    ],
)
def test_media_refuses_escapes_and_hidden_files(
    settings: Settings, make_client: MakeClient, path: str
) -> None:
    folder = write_package(settings.library_dir / "song")
    (folder / ".make-1").mkdir()
    (folder / ".make-1" / "a.wav").write_bytes(b"x")
    (folder / "karaoke.original.json").write_text("{}")
    (folder / "link.wav").symlink_to(settings.db_path)
    assert make_client("local").get(path).status_code == 404


def test_media_needs_a_reader(settings: Settings, make_client: MakeClient) -> None:
    write_package(settings.library_dir / "song")
    assert make_client("remote").get("/media/song/instrumental.wav").status_code == 403
