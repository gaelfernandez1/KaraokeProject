from collections.abc import Callable
from pathlib import Path

import pytest

from karaoke_bench.paths import BenchPaths
from karaoke_bench.sets import SetError, load_set

ToneMaker = Callable[..., Path]


def _private_song(paths: BenchPaths, song_id: str, make_tone: ToneMaker) -> None:
    song_dir = paths.data / "private" / song_id
    song_dir.mkdir(parents=True)
    make_tone("tone.wav", 1.0).rename(song_dir / "audio.wav")
    (song_dir / "meta.toml").write_text(
        'title = "Miña canción"\nlanguage = "gl"\n', encoding="utf-8"
    )


def test_load_set_private_and_single(tmp_path: Path, make_tone: ToneMaker) -> None:
    paths = BenchPaths(tmp_path / "bench")
    _private_song(paths, "x", make_tone)

    [song] = load_set("private", paths)
    [same] = load_set("private/x", paths)

    assert song == same
    assert song.language == "gl"
    assert song.title == "Miña canción"
    assert song.artist is None
    assert song.lyrics_text() is None


def test_unknown_song_id(tmp_path: Path, make_tone: ToneMaker) -> None:
    paths = BenchPaths(tmp_path / "bench")
    _private_song(paths, "x", make_tone)

    with pytest.raises(SetError, match="nope"):
        load_set("private/nope", paths)


def test_quick_requires_fetch(tmp_path: Path) -> None:
    paths = BenchPaths(tmp_path / "bench")
    paths.sets.mkdir(parents=True)
    (paths.sets / "quick.txt").write_text("# quick set\nSome_-_Song\n", encoding="utf-8")

    with pytest.raises(SetError, match="fetch"):
        load_set("quick", paths)


def test_unknown_set(tmp_path: Path) -> None:
    with pytest.raises(SetError, match="unknown set"):
        load_set("nada", BenchPaths(tmp_path))


def _with_reference(paths: BenchPaths, song_id: str, timing: str) -> None:
    from karaoke_bench.reference import Reference, dump_reference

    song_dir = paths.data / "private" / song_id
    (song_dir / "lyrics.txt").write_text("vou ao mar\n", encoding="utf-8")
    ref = Reference.model_validate(
        {
            "song_id": song_id, "language": "gl", "duration": 1.0, "timing": timing,
            "approved": False,
            "lines": [{"text": "vou ó mar", "start": 0.1, "end": 0.9, "words": []}],
        }
    )  # fmt: skip
    dump_reference(ref, song_dir / "reference.json")


@pytest.mark.usefixtures("ffmpeg")
def test_text_corrected_in_a_semiautomatic_reference_wins(
    tmp_path: Path, make_tone: ToneMaker
) -> None:
    # The review page saves text fixes in reference.json, not in the lyrics file it drafted from.
    paths = BenchPaths(tmp_path / "bench")
    _private_song(paths, "x", make_tone)
    _with_reference(paths, "x", "semiautomatic")

    [song] = load_set("private/x", paths)

    assert song.lyrics_text() == "vou ó mar"


@pytest.mark.usefixtures("ffmpeg")
def test_lyrics_file_wins_over_a_manual_reference(tmp_path: Path, make_tone: ToneMaker) -> None:
    # JamendoLyrics word texts are lowercase without accents; the lyrics file is the display text.
    paths = BenchPaths(tmp_path / "bench")
    _private_song(paths, "x", make_tone)
    _with_reference(paths, "x", "manual")

    [song] = load_set("private/x", paths)

    assert song.lyrics_text() == "vou ao mar\n"
