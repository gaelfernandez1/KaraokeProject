import json
from pathlib import Path

import pytest

from karaoke_bench.paths import BenchPaths
from karaoke_bench.reference import Reference, RefLine, RefWord, dump_reference
from karaoke_bench.repeats import build_repeats, collapse_repeats
from karaoke_bench.sets import load_set


def test_lines_sung_again_right_away_are_written_once() -> None:
    lines = ["a", "b", "a", "b", "c"]

    assert collapse_repeats(lines, set(), marked=False) == "a\nb\nc"
    assert collapse_repeats(lines, set(), marked=True) == "a\nb (x2)\nc"


def test_the_longest_repeated_block_and_how_many_times() -> None:
    assert collapse_repeats(["a", "a", "a", "b"], set(), marked=True) == "a (x3)\nb"
    lines = ["a", "b", "c", "d"] * 2 + ["e"]
    assert collapse_repeats(lines, set(), marked=True) == "a\nb\nc\nd (x2)\ne"


def test_repeats_match_without_case_or_punctuation() -> None:
    assert collapse_repeats(["Oh, yeah", "oh yeah!", "fin"], set(), marked=True) == (
        "Oh, yeah (x2)\nfin"
    )


def test_stanza_breaks_stay_where_the_last_copy_had_them() -> None:
    lines = ["a", "b", "a", "b", "c", "d"]

    assert collapse_repeats(lines, {1, 3}, marked=True) == "a\nb (x2)\n\nc\nd"


def _jamendo_song(paths: BenchPaths, name: str, texts: list[str]) -> Path:
    song = paths.data / "jamendo" / name
    song.mkdir(parents=True)
    (song / "audio.mp3").write_bytes(b"not really audio")
    (song / "meta.toml").write_text(
        'title = "Song"\nartist = "Band"\nlanguage = "gl"\nlicense = "BY"\n', encoding="utf-8"
    )
    lines = [
        RefLine(
            text=text,
            start=2.0 * i,
            end=2.0 * i + 1,
            words=[RefWord(text=text, start=2.0 * i, end=2.0 * i + 1)],
        )
        for i, text in enumerate(texts)
    ]
    ref = Reference(song_id=name, language="gl", duration=30.0, timing="manual", lines=lines)
    dump_reference(ref, song / "reference.json")
    return song


def test_build_repeats_writes_both_versions_of_songs_with_repeats(tmp_path: Path) -> None:
    paths = BenchPaths(tmp_path / "bench")
    source = _jamendo_song(paths, "song", ["ola", "ola", "mar", "adeus"])
    _jamendo_song(paths, "plain", ["ola", "mar"])
    upstream = paths.data / "jamendo" / "_upstream"
    upstream.mkdir()
    texts = ["ola\n", "ola\n", "mar\n\n", "adeus\n"]
    (upstream / "song.json").write_text(json.dumps({"lines": [{"text": t} for t in texts]}))
    recipe = tmp_path / "repeats.toml"
    recipe.write_text('version = 1\ngroups = ["repeats-marked", "repeats-unmarked"]\n')

    assert build_repeats(paths, recipe) == ["marked-song", "unmarked-song"]

    marked, unmarked = load_set("repeats", paths)
    assert (marked.group, unmarked.group) == ("repeats-marked", "repeats-unmarked")
    assert marked.lyrics_text() == "ola (x2)\nmar\n\nadeus\n"
    assert unmarked.lyrics_text() == "ola\nmar\n\nadeus\n"
    # The same audio file, so the separation already done for the song is reused.
    assert marked.audio.read_bytes() == (source / "audio.mp3").read_bytes()
    assert len(marked.load_reference().lines) == 4  # type: ignore[union-attr]


def test_build_repeats_refuses_an_unknown_group(tmp_path: Path) -> None:
    paths = BenchPaths(tmp_path / "bench")
    _jamendo_song(paths, "song", ["ola", "ola"])
    recipe = tmp_path / "repeats.toml"
    recipe.write_text('version = 1\ngroups = ["repeats-sideways"]\n')

    with pytest.raises(ValueError, match="repeats-sideways"):
        build_repeats(paths, recipe)


def test_an_echo_in_parentheses_is_not_a_repeat() -> None:
    lines = ["Ich bin nicht dagegen", "(Ich bin nicht dagegen)", "fin"]

    assert collapse_repeats(lines, set(), marked=True) == "\n".join(lines)


def test_build_repeats_drops_songs_that_no_longer_qualify(tmp_path: Path) -> None:
    paths = BenchPaths(tmp_path / "bench")
    _jamendo_song(paths, "song", ["ola", "ola"])
    recipe = tmp_path / "repeats.toml"
    recipe.write_text('version = 1\ngroups = ["repeats-unmarked"]\n')
    build_repeats(paths, recipe)
    stale = paths.data / "repeats" / "unmarked-old"
    stale.mkdir()
    (stale / "meta.toml").write_text('language = "gl"\n')

    assert build_repeats(paths, recipe) == ["unmarked-song"]
    assert [song.song_id for song in load_set("repeats", paths)] == ["unmarked-song"]
