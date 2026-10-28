import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from karaoke_bench.audio import file_sha256
from karaoke_bench.fetch import (
    FetchError,
    convert_jamendo_song,
    fetch_jamendo,
    fetch_manifest_set,
)
from karaoke_bench.paths import BenchPaths
from karaoke_bench.reference import load_reference
from karaoke_bench.sets import load_set

DATA = Path(__file__).parent / "data" / "jamendo"
ToneMaker = Callable[..., Path]


def test_convert_jamendo_assigns_words_to_nearest_line() -> None:
    ref = convert_jamendo_song(
        "Test_-_Cancion",
        "es",
        7.0,
        (DATA / "Test_-_Cancion.words.txt").read_text(),
        (DATA / "Test_-_Cancion.csv").read_text(),
        json.loads((DATA / "Test_-_Cancion.json").read_text()),
    )

    assert [line.text for line in ref.lines] == ["Ola, mar", "Línea azul", "¡Adeus!"]
    assert [[w.text for w in line.words] for line in ref.lines] == [
        ["ola", "mar"],
        ["linea", "azul"],
        ["adeus"],
    ]
    assert ref.lines[2].words[0].start == 5.8
    assert ref.timing == "manual"
    assert ref.approved
    assert all(line.status == "ok" for line in ref.lines)


def test_convert_jamendo_rejects_mismatched_word_counts() -> None:
    with pytest.raises(FetchError):
        convert_jamendo_song(
            "x", "es", 7.0, "ola\nmar", "word_start,word_end,line_end\n1,2,nan\n", {"lines": []}
        )


def _fake_downloader(tone: Path) -> Callable[[str, Path], None]:
    def download(url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        name = url.rsplit("/", 1)[-1]
        if name.endswith(".mp3"):
            shutil.copy(tone, dest)
        elif name.endswith(".words.txt"):
            shutil.copy(DATA / name, dest)
        else:
            shutil.copy(DATA / name, dest)

    return download


@pytest.mark.usefixtures("ffmpeg")
def test_fetch_jamendo_with_fake_downloader(tmp_path: Path, make_tone: ToneMaker) -> None:
    paths = BenchPaths(tmp_path / "bench")
    paths.sets.mkdir(parents=True)
    shutil.copy(
        Path(__file__).resolve().parents[3] / "bench" / "sets" / "jamendo.toml",
        paths.sets / "jamendo.toml",
    )

    ids = fetch_jamendo(paths, download=_fake_downloader(make_tone("tone.wav", 7.0)))

    song_dir = paths.data / "jamendo" / "Test_-_Cancion"
    assert ids == ["Test_-_Cancion"]
    assert (song_dir / "audio.mp3").is_file()
    assert load_reference(song_dir / "reference.json").duration == pytest.approx(7.0, abs=0.01)
    [song] = load_set("jamendo-es", paths)
    assert song.title == "Canción de proba"
    assert song.language == "es"
    assert song.lyrics_text() == "Ola, mar\nLínea azul\n¡Adeus!"


def _manifest(paths: BenchPaths, sha: str) -> None:
    (paths.sets / "gl").mkdir(parents=True)
    (paths.sets / "gl" / "manifest.toml").write_text(
        f"""
[[songs]]
id = "proba"
title = "Proba"
artist = "Alguén"
language = "gl"
style = "folk"
license = "CC BY-SA 4.0"
license_url = "https://creativecommons.org/licenses/by-sa/4.0/"
source = "https://example.org/proba"
audio_url = "https://example.org/proba.ogg"
sha256 = "{sha}"
""",
        encoding="utf-8",
    )


def test_manifest_sha_mismatch_raises(tmp_path: Path, make_tone: ToneMaker) -> None:
    paths = BenchPaths(tmp_path / "bench")
    _manifest(paths, "0" * 64)
    tone = make_tone("tone.wav", 1.0)

    with pytest.raises(FetchError):
        fetch_manifest_set("gl", paths, download=lambda url, dest: shutil.copy(tone, dest))

    assert not list((paths.data / "gl").rglob("audio.*"))


def test_manifest_set_downloads_and_loads(tmp_path: Path, make_tone: ToneMaker) -> None:
    paths = BenchPaths(tmp_path / "bench")
    tone = make_tone("tone.wav", 1.0)
    _manifest(paths, file_sha256(tone))
    (paths.sets / "gl" / "proba").mkdir()
    (paths.sets / "gl" / "proba" / "lyrics.txt").write_text("Ola mar\n", encoding="utf-8")

    ids = fetch_manifest_set("gl", paths, download=lambda url, dest: shutil.copy(tone, dest))

    [song] = load_set("gl/proba", paths)
    assert ids == ["proba"]
    assert song.audio == paths.data / "gl" / "proba" / "audio.ogg"
    assert song.lyrics_text() == "Ola mar\n"
    assert song.reference is None


def test_dataset_url_quotes_non_ascii_paths() -> None:
    from karaoke_bench.fetch import dataset_url

    url = dataset_url({"repo": "a/b", "revision": "abc"}, "subsets/de/mp3/Straße & Co.mp3")

    assert url.isascii()
    assert url == (
        "https://huggingface.co/datasets/a/b/resolve/abc/subsets/de/mp3/Stra%C3%9Fe%20%26%20Co.mp3"
    )
