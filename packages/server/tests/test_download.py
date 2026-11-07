import json
import sys
from pathlib import Path

import pytest

from karaoke_server.jobs.download import FORMAT, YtDlp
from karaoke_server.jobs.titles import clean_artist, clean_title, split_artist
from karaoke_server.jobs.types import DownloadError

pytestmark = pytest.mark.anyio

FAKE = [sys.executable, str(Path(__file__).with_name("fake_ytdlp.py"))]


async def test_probe_reads_title_artist_and_length(monkeypatch: pytest.MonkeyPatch) -> None:
    info = await YtDlp(FAKE).probe("https://example.com/v")
    assert info.title == "Pandeireta (Videoclip Oficial)"
    assert info.artist == "Banda - Topic"
    assert info.duration == 45.0
    assert info.is_live is False


async def test_probe_refuses_playlists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_YTDLP", json.dumps({"info": {"_type": "playlist"}}))
    with pytest.raises(DownloadError) as caught:
        await YtDlp(FAKE).probe("https://example.com/list")
    assert caught.value.code == "bad_url"


async def test_probe_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_YTDLP", json.dumps({"fail": "Unsupported URL: https://x"}))
    with pytest.raises(DownloadError) as caught:
        await YtDlp(FAKE).probe("https://x")
    assert caught.value.code == "bad_url"
    monkeypatch.setenv("FAKE_YTDLP", json.dumps({"fail": "Unable to download webpage: timed out"}))
    with pytest.raises(DownloadError) as caught:
        await YtDlp(FAKE).probe("https://x")
    assert caught.value.code == "download_failed"


async def test_download_reports_progress_and_the_file(tmp_path: Path) -> None:
    seen: list[float] = []
    path = await YtDlp(FAKE).download("https://example.com/v", tmp_path, seen.append)
    assert path == tmp_path / "source.mkv"
    assert path.read_bytes() == b"video"
    assert seen == sorted(seen)
    assert any(0 < fraction < 1 for fraction in seen), seen
    assert seen[-1] == 1.0


async def test_probe_counts_the_files_of_a_download(monkeypatch: pytest.MonkeyPatch) -> None:
    assert (await YtDlp(FAKE).probe("https://example.com/v")).parts == 1
    both = {"requested_formats": [{"format_id": "136"}, {"format_id": "140"}]}
    monkeypatch.setenv("FAKE_YTDLP", json.dumps({"info": both}))
    assert (await YtDlp(FAKE).probe("https://example.com/v")).parts == 2


async def test_a_single_file_fills_the_whole_bar(tmp_path: Path) -> None:
    seen: list[float] = []
    await YtDlp(FAKE).download("https://example.com/song.mp3", tmp_path, seen.append, parts=1)
    assert max(fraction for fraction in seen if fraction < 1) >= 0.9


async def test_video_and_audio_share_the_bar(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("FAKE_YTDLP", json.dumps({"parts": 2}))
    seen: list[float] = []
    await YtDlp(FAKE).download("https://example.com/v", tmp_path, seen.append, parts=2)
    assert [round(fraction, 2) for fraction in seen] == [0.25, 0.5, 0.75, 0.99, 1.0]


async def test_download_too_big(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(
        "FAKE_YTDLP", json.dumps({"fail": "File is larger than max-filesize (3 GB > 2 GB)"})
    )
    with pytest.raises(DownloadError) as caught:
        await YtDlp(FAKE).download("https://x", tmp_path, lambda p: None)
    assert caught.value.code == "too_big"


@pytest.mark.parametrize(
    ("title", "clean"),
    [
        ("Pandeireta (Videoclip Oficial)", "Pandeireta"),
        ("Mar de Vigo [Official Music Video]", "Mar de Vigo"),
        ("Song (Lyrics)", "Song"),
        ("Canción ft. Outra Artista", "Canción"),
        ("Tema (feat. X) [HD]", "Tema"),
        ("Ai, meu amor (en directo)", "Ai, meu amor"),
        ("(Official Video)", "(Official Video)"),
        ("Normal title", "Normal title"),
        # File names, as direct links and uploads give them.
        ("2_laverca", "laverca"),
        ("06. O mundo do motor", "O mundo do motor"),
        ("01 - un aire", "un aire"),
        ("mar_de_vigo", "mar de vigo"),
        ("1999", "1999"),
        ("99 Luftballons", "99 Luftballons"),
        ("Nena_Remix (Official Video)", "Nena Remix"),
    ],
)
def test_clean_title_cases(title: str, clean: str) -> None:
    assert clean_title(title) == clean


def test_clean_artist_and_split() -> None:
    assert clean_artist("Banda - Topic") == "Banda"
    assert clean_artist("BandaVEVO") == "Banda"
    assert clean_artist("Ana, Brais") == "Ana"
    assert clean_artist(None) is None
    assert split_artist("Banda - Canción") == ("Banda", "Canción")
    assert split_artist("Só un título") == (None, "Só un título")


def test_links_bring_their_video_up_to_1080p() -> None:
    # The MP4 export draws on the video as it came (the package master), not on the player's 720p.
    assert FORMAT.startswith("bv*[height<=1080]+ba/b[height<=1080]")
