import pytest

from karaoke.infra.db import repository as repo


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


class TestSaveSong:
    def test_returns_positive_integer_id(self, db_session):
        song_id = repo.save_song(db_session, _sample_song())
        assert isinstance(song_id, int)
        assert song_id > 0

    def test_saved_song_retrievable_by_id(self, db_session):
        song_id = repo.save_song(db_session, _sample_song(title="My Song"))
        song = repo.get_song_by_id(db_session, song_id)
        assert song is not None
        assert song.title == "My Song"

    def test_whisper_model_field_persisted(self, db_session):
        repo.save_song(db_session, _sample_song(whisper_model="large-v3"))
        songs = repo.get_all_songs(db_session)
        assert songs[0].whisper_model == "large-v3"

    def test_null_source_url_saved(self, db_session):
        repo.save_song(db_session, _sample_song(source_url=None))
        songs = repo.get_all_songs(db_session)
        assert songs[0].source_url is None

    def test_user_id_defaults_to_none(self, db_session):
        repo.save_song(db_session, _sample_song())
        songs = repo.get_all_songs(db_session)
        assert songs[0].user_id is None

    def test_created_at_autopopulated(self, db_session):
        repo.save_song(db_session, _sample_song())
        songs = repo.get_all_songs(db_session)
        assert songs[0].created_at is not None


class TestGetAllSongs:
    def test_empty_db_returns_empty_list(self, db_session):
        assert repo.get_all_songs(db_session) == []

    def test_returns_all_saved_songs(self, db_session):
        repo.save_song(db_session, _sample_song(title="Song A"))
        repo.save_song(db_session, _sample_song(title="Song B"))
        songs = repo.get_all_songs(db_session)
        assert len(songs) == 2

    def test_ordered_newest_first(self, db_session):
        repo.save_song(db_session, _sample_song(title="First"))
        repo.save_song(db_session, _sample_song(title="Second"))
        songs = repo.get_all_songs(db_session)
        assert songs[0].title == "Second"


class TestGetSongById:
    def test_nonexistent_id_returns_none(self, db_session):
        assert repo.get_song_by_id(db_session, 9999) is None

    def test_returns_correct_song(self, db_session):
        song_id = repo.save_song(db_session, _sample_song(title="Unique"))
        song = repo.get_song_by_id(db_session, song_id)
        assert song is not None
        assert song.title == "Unique"


class TestGetSongByFilename:
    def test_returns_matching_song(self, db_session):
        repo.save_song(db_session, _sample_song(karaoke_filename="karaoke_abc.mp4"))
        song = repo.get_song_by_filename(db_session, "karaoke_abc.mp4")
        assert song is not None

    def test_no_match_returns_none(self, db_session):
        assert repo.get_song_by_filename(db_session, "missing.mp4") is None


class TestGetSongOwningFile:
    def test_finds_by_karaoke_filename(self, db_session):
        repo.save_song(db_session, _sample_song(karaoke_filename="karaoke_x.mp4"))
        assert repo.get_song_owning_file(db_session, "karaoke_x.mp4") is not None

    def test_finds_by_video_only_filename(self, db_session):
        repo.save_song(db_session, _sample_song(video_only_filename="karaoke_x_video_only.mp4"))
        assert repo.get_song_owning_file(db_session, "karaoke_x_video_only.mp4") is not None

    def test_finds_by_vocal_filename(self, db_session):
        repo.save_song(db_session, _sample_song(vocal_filename="vocal_x.wav"))
        assert repo.get_song_owning_file(db_session, "vocal_x.wav") is not None

    def test_finds_by_instrumental_filename(self, db_session):
        repo.save_song(db_session, _sample_song(instrumental_filename="instrumental_x.wav"))
        assert repo.get_song_owning_file(db_session, "instrumental_x.wav") is not None

    def test_no_match_returns_none(self, db_session):
        repo.save_song(db_session, _sample_song())
        assert repo.get_song_owning_file(db_session, "nope.mp4") is None


class TestUpdateLastPlayed:
    def test_sets_last_played(self, db_session):
        song_id = repo.save_song(db_session, _sample_song())
        assert repo.get_song_by_id(db_session, song_id).last_played is None
        repo.update_last_played(db_session, song_id)
        assert repo.get_song_by_id(db_session, song_id).last_played is not None

    def test_nonexistent_id_is_noop(self, db_session):
        repo.update_last_played(db_session, 9999)


class TestDeleteSong:
    def test_deletes_existing_song(self, db_session):
        song_id = repo.save_song(db_session, _sample_song())
        assert repo.delete_song(db_session, song_id) is True
        assert repo.get_song_by_id(db_session, song_id) is None

    def test_nonexistent_song_returns_false(self, db_session):
        assert repo.delete_song(db_session, 9999) is False


class TestSearchSongs:
    def test_finds_matching_title(self, db_session):
        repo.save_song(db_session, _sample_song(title="Rolling Stones"))
        assert len(repo.get_songs_by_search(db_session, "Rolling")) == 1

    def test_no_match_returns_empty(self, db_session):
        repo.save_song(db_session, _sample_song(title="Beatles"))
        assert repo.get_songs_by_search(db_session, "zzznomatch") == []

    def test_partial_match(self, db_session):
        repo.save_song(db_session, _sample_song(title="Rolling Stones"))
        assert len(repo.get_songs_by_search(db_session, "Rol")) == 1

    def test_case_insensitive(self, db_session):
        repo.save_song(db_session, _sample_song(title="Rolling Stones"))
        assert len(repo.get_songs_by_search(db_session, "rolling")) == 1


class TestDatabaseStats:
    def test_empty_db_zero_counts(self, db_session):
        stats = repo.get_database_stats(db_session)
        assert stats == {
            "total_songs": 0,
            "automatic_songs": 0,
            "manual_songs": 0,
            "instrumental_songs": 0,
            "total_size": 0,
        }

    def test_counts_by_processing_type(self, db_session):
        repo.save_song(db_session, _sample_song(processing_type="automatic", file_size=100))
        repo.save_song(db_session, _sample_song(processing_type="manual_lyrics", file_size=200))
        repo.save_song(db_session, _sample_song(processing_type="instrumental", file_size=300))
        stats = repo.get_database_stats(db_session)
        assert stats["total_songs"] == 3
        assert stats["automatic_songs"] == 1
        assert stats["manual_songs"] == 1
        assert stats["instrumental_songs"] == 1
        assert stats["total_size"] == 600


class TestToDict:
    def test_dates_serialized_as_strings(self, db_session):
        song_id = repo.save_song(db_session, _sample_song())
        repo.update_last_played(db_session, song_id)
        d = repo.get_song_by_id(db_session, song_id).to_dict()
        assert isinstance(d["created_at"], str)
        assert isinstance(d["last_played"], str)

    def test_includes_storage_key(self, db_session):
        song_id = repo.save_song(
            db_session, _sample_song(storage_key="karaoke/task-1/karaoke_test.mp4")
        )
        d = repo.get_song_by_id(db_session, song_id).to_dict()
        assert d["storage_key"] == "karaoke/task-1/karaoke_test.mp4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
