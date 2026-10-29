import json

import pytest

from karaoke_engine.lyrics_lookup import find_lyrics


def _entry(i: int, duration: float, plain: str | None = "Ola\nmar") -> dict[str, object]:
    return {"id": i, "trackName": "Canción", "artistName": "Grupo", "duration": duration,
            "plainLyrics": plain, "syncedLyrics": None}  # fmt: skip


class FakeWeb:
    def __init__(self, *answers: tuple[int, object]) -> None:
        self.answers = list(answers)
        self.urls: list[str] = []

    def __call__(self, url: str) -> tuple[int, bytes]:
        self.urls.append(url)
        status, body = self.answers.pop(0)
        return status, json.dumps(body).encode()


def test_closest_duration_wins() -> None:
    web = FakeWeb((200, [_entry(1, 200.0), _entry(2, 181.0), _entry(3, 179.5, None)]))

    found = find_lyrics("Canción", "Grupo", 180.0, fetch=web, wait=lambda s: None)

    assert found is not None
    assert found.source_id == 2
    assert found.text == "Ola\nmar"
    assert "track_name=Canci%C3%B3n" in web.urls[0]


def test_retries_when_the_server_is_busy() -> None:
    web = FakeWeb((503, {"message": "busy"}), (200, [_entry(1, 180.0)]))

    found = find_lyrics("Canción", "Grupo", 180.0, fetch=web, wait=lambda s: None)

    assert found is not None
    assert len(web.urls) == 2


def test_nothing_close_in_duration_is_no_match() -> None:
    web = FakeWeb((200, [_entry(1, 240.0)]))

    assert find_lyrics("Canción", "Grupo", 180.0, fetch=web, wait=lambda s: None) is None


def test_gives_up_after_three_busy_answers() -> None:
    web = FakeWeb(*[(503, {})] * 3)

    with pytest.raises(OSError, match="busy"):
        find_lyrics("Canción", "Grupo", 180.0, fetch=web, wait=lambda s: None)
