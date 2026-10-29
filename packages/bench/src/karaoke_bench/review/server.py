"""Local server for the review page: the song, its reference and a waveform. Localhost only."""

import json
from functools import cached_property
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from karaoke_bench.audio import load_mono16k, peaks
from karaoke_bench.reference import Reference, dump_reference
from karaoke_bench.sets import Song

STATIC = Path(__file__).parent / "static"
_PAGES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
_AUDIO_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".opus": "audio/ogg",
}


class _Review:
    def __init__(self, song: Song, reference_path: Path, vocals: Path | None) -> None:
        self.song = song
        self.reference_path = reference_path
        self.vocals = vocals

    @cached_property
    def peaks(self) -> dict[str, Any]:
        low, high = peaks(load_mono16k(self.vocals or self.song.audio), rate=100)
        return {"rate": 100, "min": low, "max": high, "source": "vocals" if self.vocals else "mix"}


def make_server(
    song: Song, reference_path: Path, vocals: Path | None, port: int
) -> ThreadingHTTPServer:
    review = _Review(song, reference_path, vocals)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in _PAGES:
                name, content_type = _PAGES[self.path]
                self._send(HTTPStatus.OK, (STATIC / name).read_bytes(), content_type)
            elif self.path == "/api/reference":
                body = review.reference_path.read_bytes()
                self._send(HTTPStatus.OK, body, "application/json; charset=utf-8")
            elif self.path == "/api/song":
                info = {"id": song.song_id, "title": song.title, "artist": song.artist,
                        "has_vocals": review.vocals is not None}  # fmt: skip
                self._send_json(info)
            elif self.path == "/api/peaks":
                self._send_json(review.peaks)
            elif self.path == "/audio/mix":
                self._send_audio(song.audio)
            elif self.path == "/audio/vocals" and review.vocals is not None:
                self._send_audio(review.vocals)
            else:
                self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")

        def do_PUT(self) -> None:
            if self.path != "/api/reference":
                self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")
                return
            length = int(self.headers.get("Content-Length", "0"))
            try:
                ref = Reference.model_validate_json(self.rfile.read(length))
            except ValidationError as exc:
                self._send(HTTPStatus.BAD_REQUEST, str(exc).encode(), "text/plain; charset=utf-8")
                return
            dump_reference(ref, review.reference_path)
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:
            return  # keep the terminal for the instructions

        def _send_audio(self, path: Path) -> None:
            content_type = _AUDIO_TYPES.get(path.suffix.lower(), "application/octet-stream")
            self._send(HTTPStatus.OK, path.read_bytes(), content_type)

        def _send_json(self, data: Any) -> None:
            body = json.dumps(data, ensure_ascii=False).encode()
            self._send(HTTPStatus.OK, body, "application/json; charset=utf-8")

        def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
