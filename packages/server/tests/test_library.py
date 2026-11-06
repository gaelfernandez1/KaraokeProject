import json
import os
import time
from pathlib import Path

import pytest

from karaoke_contracts import load_doc
from karaoke_server.config import Settings
from karaoke_server.db import Database
from karaoke_server.library import InvalidDocError, Library

from .conftest import write_package


@pytest.fixture
def library(settings: Settings, db: Database) -> Library:
    return Library(settings, db)


def test_list_reads_package_folders(settings: Settings, library: Library) -> None:
    write_package(settings.library_dir / "mar-de-vigo")
    write_package(settings.library_dir / "outra", title="Outra")
    (settings.library_dir / "empty").mkdir()
    (settings.library_dir / ".make-abc").mkdir()
    songs = library.list()
    assert {s.id for s in songs} == {"mar-de-vigo", "outra"}
    song = next(s for s in songs if s.id == "outra")
    assert song.title == "Outra"
    assert song.language == "gl"
    assert song.duration == 32.0
    assert song.has_video is False
    assert song.lyrics_source == "user"
    assert song.hook


def test_newest_songs_come_first(settings: Settings, library: Library, db: Database) -> None:
    write_package(settings.library_dir / "old")
    write_package(settings.library_dir / "new")
    db.execute("INSERT INTO songs (id, created_at) VALUES ('old', '2026-01-01T00:00:00Z')")
    db.execute("INSERT INTO songs (id, created_at) VALUES ('new', '2026-10-31T00:00:00Z')")
    assert [s.id for s in library.list()] == ["new", "old"]


def test_summary_is_cached_until_the_doc_changes(settings: Settings, library: Library) -> None:
    folder = write_package(settings.library_dir / "song")
    assert library.summary("song").title == "Mar de Vigo"  # type: ignore[union-attr]
    doc = json.loads((folder / "karaoke.json").read_text(encoding="utf-8"))
    doc["title"] = "Changed"
    (folder / "karaoke.json").write_text(json.dumps(doc), encoding="utf-8")
    later = time.time() + 5
    os.utime(folder / "karaoke.json", (later, later))
    assert library.summary("song").title == "Changed"  # type: ignore[union-attr]


def test_unknown_or_bad_ids_have_no_song(library: Library) -> None:
    assert library.summary("nope") is None
    assert library.doc("../etc") is None
    assert library.folder("UPPER") is None


@pytest.mark.parametrize(
    "rel",
    [
        "../x.wav",
        "/etc/passwd",
        ".make-1/a.wav",
        "karaoke.original.json",
        "karaoke.json",
        "evil.py",
        "link.wav",
        "sub/../../x.wav",
        "",
    ],
)
def test_media_path_refuses_escapes(settings: Settings, library: Library, rel: str) -> None:
    folder = write_package(settings.library_dir / "song")
    (folder / ".make-1").mkdir()
    (folder / ".make-1" / "a.wav").write_bytes(b"x")
    (folder / "evil.py").write_text("x")
    (folder / "link.wav").symlink_to("/etc/passwd")
    assert library.media_path("song", rel) is None


def test_media_path_serves_package_files(settings: Settings, library: Library) -> None:
    folder = write_package(settings.library_dir / "song")
    (folder / "exports").mkdir()
    (folder / "exports" / "song-16x9.mp4").write_bytes(b"mp4")
    assert library.media_path("song", "instrumental.wav") == folder / "instrumental.wav"
    assert library.media_path("song", "exports/song-16x9.mp4") == folder / "exports/song-16x9.mp4"


def test_save_doc_validates_marks_edited_and_keeps_the_original_once(
    settings: Settings, library: Library
) -> None:
    folder = write_package(settings.library_dir / "song")
    original = (folder / "karaoke.json").read_bytes()
    doc = library.doc("song")
    assert doc is not None
    first = doc.model_copy(update={"title": "Corrected", "id": "whatever"})
    saved = library.save_doc("song", first)
    assert saved.edited is True
    assert saved.id == "song"
    assert load_doc(folder / "karaoke.json").title == "Corrected"
    assert (folder / "karaoke.original.json").read_bytes() == original
    library.save_doc("song", saved.model_copy(update={"title": "Again"}))
    assert (folder / "karaoke.original.json").read_bytes() == original
    assert library.summary("song").edited is True  # type: ignore[union-attr]


def test_save_doc_rejects_invalid_times(settings: Settings, library: Library) -> None:
    folder = write_package(settings.library_dir / "song")
    before = (folder / "karaoke.json").read_bytes()
    doc = library.doc("song")
    assert doc is not None
    line = doc.lines[0].model_copy(update={"start": 999.0, "end": 1000.0})
    with pytest.raises(InvalidDocError) as caught:
        library.save_doc("song", doc.model_copy(update={"lines": [line, *doc.lines[1:]]}))
    assert caught.value.issues
    assert (folder / "karaoke.json").read_bytes() == before


def test_save_doc_rejects_media_outside_the_package(settings: Settings, library: Library) -> None:
    write_package(settings.library_dir / "song")
    doc = library.doc("song")
    assert doc is not None
    audio = doc.audio.model_copy(update={"instrumental": "../other/instrumental.wav"})
    with pytest.raises(InvalidDocError):
        library.save_doc("song", doc.model_copy(update={"audio": audio}))


def test_delete_moves_to_trash(settings: Settings, library: Library) -> None:
    write_package(settings.library_dir / "song")
    assert library.delete("song") is True
    assert library.summary("song") is None
    assert not (settings.library_dir / "song").exists()
    assert [p.name.startswith("song-") for p in settings.trash_dir.iterdir()] == [True]
    assert library.delete("song") is False


def test_adopt_renames_on_collision_and_rewrites_the_id(
    settings: Settings, library: Library, tmp_path: Path, db: Database
) -> None:
    write_package(settings.library_dir / "mar-de-vigo")
    made = write_package(settings.jobs_dir / "j1" / "out", title="Mar de Vigo")
    song_id = library.adopt(made, "Mar de Vigo", job_id="j1")
    assert song_id == "mar-de-vigo-2"
    assert load_doc(settings.library_dir / song_id / "karaoke.json").id == song_id
    assert not made.exists()
    assert db.query("SELECT job_id FROM songs WHERE id = ?", (song_id,))[0]["job_id"] == "j1"


def test_adopt_falls_back_to_a_plain_id(settings: Settings, library: Library) -> None:
    made = write_package(settings.jobs_dir / "j1" / "out", title="¡¡!!")
    assert library.adopt(made, "¡¡!!", job_id="j1") == "karaoke"


def test_import_copies_a_valid_package(
    settings: Settings, library: Library, tmp_path: Path
) -> None:
    src = write_package(tmp_path / "Some Folder", title="Imported song")
    song_id = library.import_package(src)
    assert song_id == "imported-song"
    assert (src / "karaoke.json").exists()
    assert library.summary(song_id) is not None


def test_import_copies_the_package_files_only_never_links(library: Library, tmp_path: Path) -> None:
    # A package from someone else, with links to the owner's files and extra files: once in the
    # library, anything with a media extension would be served to every phone at home.
    secret = tmp_path / "secret.txt"
    secret.write_text("private", encoding="utf-8")
    pictures = tmp_path / "Pictures"
    pictures.mkdir()
    (pictures / "private.jpg").write_bytes(b"jpg")
    src = write_package(tmp_path / "pkg", title="Shared")
    (src / "bonus.mp3").symlink_to(secret)
    (src / "gallery").symlink_to(pictures, target_is_directory=True)
    (src / "extra.mp3").write_bytes(b"not referenced")
    (src / "LICENSE").write_text("CC BY 4.0", encoding="utf-8")

    folder = library.folder(library.import_package(src))

    assert folder is not None
    names = {p.name for p in folder.iterdir()}
    assert names.isdisjoint({"bonus.mp3", "gallery", "extra.mp3"})
    assert {"karaoke.json", "LICENSE"} <= names
    assert not any(p.is_symlink() for p in folder.rglob("*"))


def test_import_rejects_invalid_package(library: Library, tmp_path: Path) -> None:
    src = write_package(tmp_path / "bad")
    (src / "instrumental.wav").unlink()
    with pytest.raises(InvalidDocError):
        library.import_package(src)


def test_purge_trash_keeps_recent(settings: Settings, library: Library) -> None:
    old = settings.trash_dir / "old-1"
    new = settings.trash_dir / "new-1"
    old.mkdir()
    new.mkdir()
    long_ago = time.time() - 31 * 86400
    os.utime(old, (long_ago, long_ago))
    assert library.purge_trash(days=30) == 1
    assert not old.exists()
    assert new.exists()


def test_an_old_song_deleted_today_stays_in_the_trash(settings: Settings, library: Library) -> None:
    folder = write_package(settings.library_dir / "song")
    made_long_ago = time.time() - 90 * 86400
    for path in (*folder.iterdir(), folder):
        os.utime(path, (made_long_ago, made_long_ago))
    library.delete("song")
    assert library.purge_trash(days=30) == 0
    assert len(list(settings.trash_dir.iterdir())) == 1


@pytest.mark.usefixtures("db")
def test_the_server_empties_old_trash_when_it_starts(settings: Settings) -> None:
    from karaoke_server.app import build_services, create_app
    from karaoke_server.network import NetworkState

    from .live import live_server

    old = settings.trash_dir / f"song-{int(time.time()) - 31 * 86400}"
    old.mkdir(parents=True)
    services = build_services(settings, network_state=NetworkState(None, None, None, None))
    with live_server(create_app(settings, services=services)):
        pass
    assert not old.exists()
