from karaoke.infra.metadata_utils import (
    clean_youtube_url,
    extract_title_from_filename,
    format_duration,
    format_file_size,
)


class TestExtractTitleFromFilename:
    def test_basic_underscored_filename(self):
        assert extract_title_from_filename("my_song.mp4") == "My Song"

    def test_strips_karaoke_prefix_with_id(self):
        result = extract_title_from_filename("karaoke_abc123_my_song.mp4")
        assert result == "My Song"

    def test_strips_karaoke_manual_prefix_with_id(self):
        result = extract_title_from_filename("karaoke_manual_abc_my_song.mp4")
        assert result == "My Song"

    def test_strips_normalized_suffix(self):
        result = extract_title_from_filename("my_song_normalized.mp4")
        assert "normalized" not in result.lower()

    def test_capitalizes_each_word(self):
        assert extract_title_from_filename("hello_world.mp4") == "Hello World"

    def test_strips_instrumental_prefix_with_id(self):
        result = extract_title_from_filename("instrumental_abc_my_song.mp4")
        assert result == "My Song"

    def test_strips_vocal_prefix_with_id(self):
        result = extract_title_from_filename("vocal_abc_my_song.mp4")
        assert result == "My Song"

    def test_extension_removed(self):
        result = extract_title_from_filename("song.mp4")
        assert ".mp4" not in result


class TestCleanYoutubeUrl:
    def test_clean_url_unchanged(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert clean_youtube_url(url) == url

    def test_youtu_be_normalized_to_full_url(self):
        result = clean_youtube_url("https://youtu.be/dQw4w9WgXcQ")
        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_extra_query_params_stripped(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL123&t=42"
        assert clean_youtube_url(url) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_non_youtube_url_returned_unchanged(self):
        url = "https://vimeo.com/12345"
        assert clean_youtube_url(url) == url

    def test_empty_string_returned_unchanged(self):
        assert clean_youtube_url("") == ""

    def test_arbitrary_string_returned_unchanged(self):
        assert clean_youtube_url("not_a_url") == "not_a_url"


class TestFormatFileSize:
    def test_zero_bytes(self):
        assert format_file_size(0) == "0 B"

    def test_small_bytes(self):
        assert format_file_size(500) == "500.0 B"

    def test_one_kilobyte(self):
        assert format_file_size(1024) == "1.0 KB"

    def test_one_megabyte(self):
        assert format_file_size(1024 * 1024) == "1.0 MB"

    def test_one_gigabyte(self):
        assert format_file_size(1024**3) == "1.0 GB"

    def test_partial_kilobyte(self):
        assert format_file_size(1536) == "1.5 KB"


class TestFormatDuration:
    def test_none_returns_desconecida(self):
        # Hardcoded Galician string in the source; test locks it in.
        assert format_duration(None) == "Descoñecida"

    def test_zero_seconds(self):
        assert format_duration(0.0) == "00:00"

    def test_45_seconds(self):
        assert format_duration(45.0) == "00:45"

    def test_90_seconds(self):
        assert format_duration(90.0) == "01:30"

    def test_hours_shown_when_present(self):
        assert format_duration(3661.0) == "01:01:01"

    def test_no_hours_when_under_one_hour(self):
        result = format_duration(3599.0)
        assert ":" in result
        assert result.count(":") == 1  # MM:SS only
