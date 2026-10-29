"""Song sets: the public JamendoLyrics songs, the Galician set and the user's private songs."""

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from karaoke_bench.paths import BenchPaths
from karaoke_bench.reference import Reference, load_reference

LANGUAGES = ("en", "es", "fr", "de")


class SetError(ValueError):
    pass


@dataclass(frozen=True)
class Song:
    set_name: str
    song_id: str
    title: str
    artist: str | None
    language: str
    audio: Path
    reference: Path | None
    lyrics: Path | None

    def load_reference(self) -> Reference | None:
        return load_reference(self.reference) if self.reference else None

    def lyrics_text(self) -> str | None:
        """The lyrics a user would paste: the lyrics file, or the reference's line texts.

        A semiautomatic reference wins over the lyrics file: it was drafted from that file and
        then corrected by ear, and the review page saves text fixes only in the reference.
        """
        ref = self.load_reference()
        if ref is not None and ref.timing == "semiautomatic":
            return ref.lyrics_text()
        if self.lyrics:
            return self.lyrics.read_text(encoding="utf-8")
        return ref.lyrics_text() if ref else None


def load_set(name: str, paths: BenchPaths) -> list[Song]:
    """Songs of a set: jamendo, jamendo-<lang>, quick, gl (any manifest set), private, or set/id."""
    if "/" in name:
        set_name, song_id = name.split("/", 1)
        songs = [song for song in load_set(set_name, paths) if song.song_id == song_id]
        if not songs:
            raise SetError(f"no song '{song_id}' in set '{set_name}'")
        return songs
    if name == "jamendo":
        return _jamendo(paths)
    if name.startswith("jamendo-") and name.removeprefix("jamendo-") in LANGUAGES:
        lang = name.removeprefix("jamendo-")
        return [song for song in _jamendo(paths) if song.language == lang]
    if name == "quick":
        return _quick(paths)
    if name == "private":
        return _private(paths)
    if (paths.sets / name / "manifest.toml").is_file():
        return _manifest_set(name, paths)
    raise SetError(
        f"unknown set '{name}' (try jamendo, jamendo-<{'|'.join(LANGUAGES)}>, quick, gl, private)"
    )


def read_meta(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def write_meta(path: Path, values: dict[str, str | None]) -> None:
    """Flat TOML of strings; JSON string escapes are valid TOML basic strings."""
    lines = [
        f"{key} = {json.dumps(value, ensure_ascii=False)}"
        for key, value in values.items()
        if value is not None
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _jamendo(paths: BenchPaths) -> list[Song]:
    root = paths.data / "jamendo"
    songs = [
        _song_from_dir("jamendo", d) for d in sorted(root.glob("*")) if (d / "meta.toml").is_file()
    ]
    if not songs:
        raise SetError(
            "the jamendo set is not downloaded; run `karaoke-bench fetch --set jamendo` first"
        )
    return songs


def _quick(paths: BenchPaths) -> list[Song]:
    listed = paths.sets / "quick.txt"
    ids = [
        line.strip()
        for line in listed.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    songs = []
    for song_id in ids:
        song_dir = paths.data / "jamendo" / song_id
        if not (song_dir / "meta.toml").is_file():
            raise SetError(
                f"'{song_id}' is not downloaded; run `karaoke-bench fetch --set jamendo` first"
            )
        songs.append(_song_from_dir("jamendo", song_dir))
    return songs


def _private(paths: BenchPaths) -> list[Song]:
    root = paths.data / "private"
    return [
        _song_from_dir("private", d) for d in sorted(root.glob("*")) if (d / "meta.toml").is_file()
    ]


def _song_from_dir(set_name: str, song_dir: Path) -> Song:
    meta = read_meta(song_dir / "meta.toml")
    return Song(
        set_name=set_name,
        song_id=song_dir.name,
        title=meta.get("title", song_dir.name),
        artist=meta.get("artist"),
        language=meta["language"],
        audio=_audio_in(song_dir, set_name),
        reference=_optional(song_dir / "reference.json"),
        lyrics=_optional(song_dir / "lyrics.txt"),
    )


def _manifest_set(name: str, paths: BenchPaths) -> list[Song]:
    with (paths.sets / name / "manifest.toml").open("rb") as handle:
        entries = tomllib.load(handle).get("songs", [])
    songs = []
    for entry in entries:
        song_id = entry["id"]
        versioned = paths.sets / name / song_id
        songs.append(
            Song(
                set_name=name,
                song_id=song_id,
                title=entry["title"],
                artist=entry.get("artist"),
                language=entry["language"],
                audio=_audio_in(paths.data / name / song_id, name),
                reference=_optional(versioned / "reference.json"),
                lyrics=_optional(versioned / "lyrics.txt"),
            )
        )
    return songs


def _audio_in(song_dir: Path, set_name: str) -> Path:
    found = sorted(song_dir.glob("audio.*"))
    if not found:
        hint = (
            "put the song there as audio.<ext>"
            if set_name == "private"
            else f"run `karaoke-bench fetch --set {set_name}` first"
        )
        raise SetError(f"no audio in {song_dir}; {hint}")
    return found[0]


def _optional(path: Path) -> Path | None:
    return path if path.is_file() else None
