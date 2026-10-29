"""Lyrics from LRCLIB (lrclib.net), an open and free lyrics database, only when asked for.

It sends the title and the artist to that service, never the audio. The entry whose duration is
closest to the song's (within a few seconds) is taken, because the same song often appears in
several edits. The service is sometimes busy: it is asked again a couple of times.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

URL = "https://lrclib.net/api/search"
USER_AGENT = "karaoke-engine (local karaoke generator)"
# Entries whose duration differs more than this are another edit of the song.
MAX_DURATION_GAP = 5.0
_ATTEMPTS = 3

Fetch = Callable[[str], tuple[int, bytes]]


@dataclass(frozen=True)
class FoundLyrics:
    text: str
    synced: str | None  # LRC with line times, when the entry has them
    source_id: int
    duration: float


def find_lyrics(
    title: str,
    artist: str,
    duration: float,
    fetch: Fetch | None = None,
    wait: Callable[[float], None] = time.sleep,
) -> FoundLyrics | None:
    query = urllib.parse.urlencode({"track_name": title, "artist_name": artist})
    entries = _ask(f"{URL}?{query}", fetch or _http_get, wait)
    close = [
        e
        for e in entries
        if e.get("plainLyrics")
        and abs(float(e.get("duration") or 0) - duration) <= MAX_DURATION_GAP
    ]
    if not close:
        return None
    best = min(close, key=lambda e: abs(float(e["duration"]) - duration))
    return FoundLyrics(
        text=str(best["plainLyrics"]),
        synced=best.get("syncedLyrics"),
        source_id=int(best["id"]),
        duration=float(best["duration"]),
    )


def _ask(url: str, fetch: Fetch, wait: Callable[[float], None]) -> list[dict[str, Any]]:
    for attempt in range(_ATTEMPTS):
        status, body = fetch(url)
        if status == 200:
            data = json.loads(body)
            return data if isinstance(data, list) else []
        if status not in (429, 502, 503):
            raise OSError(f"LRCLIB answered {status}")
        if attempt + 1 < _ATTEMPTS:
            wait(2.0 * (attempt + 1))
    raise OSError("LRCLIB is busy; try again later or pass the lyrics with --lyrics")


def _http_get(url: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return int(response.status), response.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read()
