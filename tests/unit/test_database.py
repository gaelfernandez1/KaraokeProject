import sqlite3

import pytest

import karaoke.infra.database as db_module


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DATABASE_PATH", db_path)
    db_module.init_database()
    return db_path


def _sample_song(**overrides):
    base = {
        "title": "Test Song",
        "original_filename": "test.mp4",
        "karaoke_filename": "karaoke_test.mp4",
        "video_only_filename": "karaoke_test_video_only.mp4",
        "vocal_filename": "vocal_test.wav",
        "instrumental_filename": "instrumental_test.wav",
        "source_type": "upload",
        "source_url": None,
        "processing_type": "automatic",
        "manual_lyrics": None,
        "language": "gl",
        "enable_diarization": False,
        "whisper_model": "small",
        "file_size": 1024,
        "duration": 180.0,
    }
    base.update(overrides)
    return base


class TestInitDatabase:
    def test_creates_songs_table(self, tmp_db):
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='songs'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_idempotent_second_call(self, tmp_db):
        # Should not raise even when table already exists
        db_module.init_database()


class TestSaveSong:
    def test_returns_positive_integer_id(self, tmp_db):
        song_id = db_module.save_song_to_database(_sample_song())
        assert isinstance(song_id, int)
        assert song_id > 0

    def test_saved_song_retrievable_by_id(self, tmp_db):
        song_id = db_module.save_song_to_database(_sample_song(title="My Song"))
        song = db_module.get_song_by_id(song_id)
        assert song is not None
        assert song["title"] == "My Song"

    def test_whisper_model_field_persisted(self, tmp_db):
        db_module.save_song_to_database(_sample_song(whisper_model="large-v3"))
        songs = db_module.get_all_songs()
        assert songs[0]["whisper_model"] == "large-v3"

    def test_null_source_url_saved(self, tmp_db):
        db_module.save_song_to_database(_sample_song(source_url=None))
        songs = db_module.get_all_songs()
        assert songs[0]["source_url"] is None


class TestGetAllSongs:
    def test_empty_db_returns_empty_list(self, tmp_db):
        assert db_module.get_all_songs() == []

    def test_returns_all_saved_songs(self, tmp_db):
        db_module.save_song_to_database(_sample_song(title="Song A"))
        db_module.save_song_to_database(_sample_song(title="Song B"))
        songs = db_module.get_all_songs()
        assert len(songs) == 2

    def test_ordered_by_created_at_desc(self, tmp_db):
        db_module.save_song_to_database(_sample_song(title="First"))
        db_module.save_song_to_database(_sample_song(title="Second"))
        songs = db_module.get_all_songs()
        # Most recent is first
        assert songs[0]["title"] == "Second"


class TestGetSongById:
    def test_nonexistent_id_returns_none(self, tmp_db):
        assert db_module.get_song_by_id(9999) is None

    def test_returns_correct_song(self, tmp_db):
        song_id = db_module.save_song_to_database(_sample_song(title="Unique"))
        song = db_module.get_song_by_id(song_id)
        assert song is not None
        assert song["title"] == "Unique"


class TestDeleteSong:
    def test_deletes_existing_song(self, tmp_db):
        song_id = db_module.save_song_to_database(_sample_song())
        assert db_module.delete_song(song_id) is True
        assert db_module.get_song_by_id(song_id) is None

    def test_nonexistent_song_returns_false(self, tmp_db):
        assert db_module.delete_song(9999) is False


class TestSearchSongs:
    def test_finds_matching_title(self, tmp_db):
        db_module.save_song_to_database(_sample_song(title="Rolling Stones"))
        results = db_module.get_songs_by_search("Rolling")
        assert len(results) == 1

    def test_no_match_returns_empty(self, tmp_db):
        db_module.save_song_to_database(_sample_song(title="Beatles"))
        results = db_module.get_songs_by_search("zzznomatch")
        assert results == []

    def test_partial_match(self, tmp_db):
        db_module.save_song_to_database(_sample_song(title="Rolling Stones"))
        results = db_module.get_songs_by_search("Rol")
        assert len(results) == 1

    def test_case_insensitive_sqlite_like(self, tmp_db):
        db_module.save_song_to_database(_sample_song(title="Rolling Stones"))
        results = db_module.get_songs_by_search("rolling")
        assert len(results) == 1
