import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator

import pytest

from karaoke_bench.paths import BenchPaths
from karaoke_bench.review.server import make_server
from karaoke_bench.sets import Song, load_set


@pytest.fixture
def server(demo_bench: BenchPaths) -> Iterator[tuple[str, Song]]:
    [song] = load_set("private/demo", demo_bench)
    assert song.reference is not None
    httpd = make_server(song, song.reference, vocals=None, port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", song
    httpd.shutdown()
    httpd.server_close()


def _get(url: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""


def _put(url: str, body: bytes) -> int:
    request = urllib.request.Request(url, data=body, method="PUT")
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return exc.code


def test_server_serves_page_and_reference(server: tuple[str, Song]) -> None:
    base, song = server

    page_status, page = _get(f"{base}/")
    ref_status, body = _get(f"{base}/api/reference")

    assert page_status == 200
    assert b"<title>" in page
    assert ref_status == 200
    assert song.reference is not None
    assert json.loads(body) == json.loads(song.reference.read_text(encoding="utf-8"))


def test_server_put_reference_validates(server: tuple[str, Song]) -> None:
    base, song = server
    assert song.reference is not None
    before = song.reference.read_text(encoding="utf-8")

    assert _put(f"{base}/api/reference", b'{"song_id": 1}') == 400
    assert song.reference.read_text(encoding="utf-8") == before

    data = json.loads(before)
    data["lines"][0]["status"] = "wrong"
    data["lines"][0]["note"] = "mal"
    assert _put(f"{base}/api/reference", json.dumps(data).encode()) == 204
    assert json.loads(song.reference.read_text(encoding="utf-8"))["lines"][0]["note"] == "mal"


@pytest.mark.usefixtures("ffmpeg")
def test_server_serves_audio_and_peaks(server: tuple[str, Song]) -> None:
    base, song = server

    status, audio = _get(f"{base}/audio/mix")
    peaks_status, peaks = _get(f"{base}/api/peaks")

    assert status == 200
    assert audio == song.audio.read_bytes()
    assert peaks_status == 200
    data = json.loads(peaks)
    assert data["rate"] == 100
    assert len(data["min"]) == len(data["max"]) > 3000


def test_server_rejects_unknown_paths(server: tuple[str, Song]) -> None:
    base, _ = server

    assert _get(f"{base}/../etc/passwd")[0] == 404
    assert _get(f"{base}/audio/otra")[0] == 404
    assert _get(f"{base}/audio/vocals")[0] == 404
    assert _get(f"{base}/static/../server.py")[0] == 404
