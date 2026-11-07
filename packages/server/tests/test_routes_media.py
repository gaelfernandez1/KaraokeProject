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


def test_media_and_the_app_answer_head_requests(
    settings: Settings, make_client: MakeClient
) -> None:
    folder = write_package(settings.library_dir / "song")
    (folder / "background.mp4").write_bytes(bytes(1024))
    client = make_client("home")
    head = client.head("/media/song/background.mp4")
    assert head.status_code == 200
    assert head.headers["content-length"] == "1024"
    assert client.head("/media/song/karaoke.json").status_code == 200


def test_download_names_the_file_as_asked(settings: Settings, make_client: MakeClient) -> None:
    folder = write_package(settings.library_dir / "song")
    (folder / "exports").mkdir()
    (folder / "exports" / "song-16x9-clasico.mp4").write_bytes(bytes(16))
    client = make_client("home")

    video = client.get(
        "/media/song/exports/song-16x9-clasico.mp4",
        params={"download": "1", "name": "Uxía - Mar de Vigo (karaoke).mp4"},
    )
    assert video.status_code == 200
    assert video.headers["content-disposition"] == (
        "attachment; filename*=utf-8''Ux%C3%ADa%20-%20Mar%20de%20Vigo%20%28karaoke%29.mp4"
    )
    plain = client.get("/media/song/exports/song-16x9-clasico.mp4", params={"download": "1"})
    assert plain.headers["content-disposition"] == 'attachment; filename="song-16x9-clasico.mp4"'
    inline = client.get("/media/song/exports/song-16x9-clasico.mp4")
    assert "content-disposition" not in inline.headers


@pytest.mark.parametrize(
    ("asked", "given"),
    [
        ("../../etc/passwd", "passwd.mp4"),
        ('a\\b:c*d?"e<f>g|h\n.mp4', "b c d e f g h.mp4"),
        ("Mar de Vigo.exe", "Mar de Vigo.exe.mp4"),
        ("   ", "song-16x9-clasico.mp4"),
        ("x" * 300 + ".mp4", "x" * 120 + ".mp4"),
    ],
)
def test_download_names_are_made_safe(
    settings: Settings, make_client: MakeClient, asked: str, given: str
) -> None:
    folder = write_package(settings.library_dir / "song")
    (folder / "exports").mkdir()
    (folder / "exports" / "song-16x9-clasico.mp4").write_bytes(bytes(16))
    response = make_client("home").get(
        "/media/song/exports/song-16x9-clasico.mp4", params={"download": "1", "name": asked}
    )
    assert response.headers["content-disposition"].endswith(quote_disposition(given))


def quote_disposition(name: str) -> str:
    from urllib.parse import quote

    quoted = quote(name)
    return f"filename*=utf-8''{quoted}" if quoted != name else f'filename="{name}"'


def test_lyrics_download_as_a_file(settings: Settings, make_client: MakeClient) -> None:
    write_package(settings.library_dir / "song", title="Mar")
    response = make_client("home").get(
        "/media/song/karaoke.json", params={"download": "1", "name": "Mar.karaoke.json"}
    )
    assert response.json()["title"] == "Mar"
    assert response.headers["content-disposition"] == 'attachment; filename="Mar.karaoke.json"'
