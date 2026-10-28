import pytest

from karaoke.infra.utils import (
    clean_abnormal_segments,
    sanitize_filename,
    seconds_to_timecode,
    time_str_to_sec,
)


class TestSecondsToTimecode:
    def test_zero(self):
        assert seconds_to_timecode(0) == "00:00:00,000"

    def test_one_second(self):
        assert seconds_to_timecode(1.0) == "00:00:01,000"

    def test_fractional_seconds(self):
        assert seconds_to_timecode(1.5) == "00:00:01,500"

    def test_minutes(self):
        assert seconds_to_timecode(90.0) == "00:01:30,000"

    def test_hours(self):
        assert seconds_to_timecode(3661.0) == "01:01:01,000"

    def test_milliseconds(self):
        assert seconds_to_timecode(0.123) == "00:00:00,123"

    def test_roundtrip(self):
        assert seconds_to_timecode(time_str_to_sec("01:23:45,678")) == "01:23:45,678"


class TestTimeStrToSec:
    def test_basic(self):
        assert time_str_to_sec("00:00:01,000") == pytest.approx(1.0)

    def test_zero(self):
        assert time_str_to_sec("00:00:00,000") == pytest.approx(0.0)

    def test_with_hours(self):
        assert time_str_to_sec("01:00:00,000") == pytest.approx(3600.0)

    def test_fractional(self):
        assert time_str_to_sec("00:00:01,500") == pytest.approx(1.5)

    def test_minutes_and_seconds(self):
        assert time_str_to_sec("00:01:30,000") == pytest.approx(90.0)


class TestSanitizeFilename:
    def test_spaces_become_underscores(self):
        assert sanitize_filename("hello world.mp4") == "hello_world.mp4"

    def test_accented_chars_stripped(self):
        result = sanitize_filename("canción.mp4")
        assert result == "cancion.mp4"

    def test_special_chars_removed(self):
        result = sanitize_filename("file!@#.mp4")
        assert "!" not in result
        assert "@" not in result
        assert "#" not in result

    def test_double_underscores_collapsed(self):
        result = sanitize_filename("hello  world.mp4")
        assert "__" not in result

    def test_empty_string(self):
        assert sanitize_filename("") == ""

    def test_already_clean_unchanged(self):
        assert sanitize_filename("clean_file.mp4") == "clean_file.mp4"

    def test_leading_trailing_underscores_stripped(self):
        result = sanitize_filename("_hello_")
        assert not result.startswith("_")
        assert not result.endswith("_")


class TestCleanAbnormalSegments:
    def test_empty_list_returns_empty(self):
        assert clean_abnormal_segments([]) == []

    def test_short_segment_unchanged(self):
        segs = [{"start": 0.0, "end": 1.0, "word": "hello"}]
        result = clean_abnormal_segments(segs)
        assert result[0]["end"] == 1.0

    def test_long_segment_clamped_to_start_plus_3s(self):
        segs = [{"start": 0.0, "end": 10.0, "word": "hello"}]
        result = clean_abnormal_segments(segs)
        assert result[0]["end"] == pytest.approx(3.0)

    def test_exactly_3s_duration_unchanged(self):
        segs = [{"start": 1.0, "end": 4.0, "word": "hello"}]
        result = clean_abnormal_segments(segs)
        assert result[0]["end"] == 4.0

    def test_custom_max_duration(self):
        segs = [{"start": 0.0, "end": 5.0, "word": "hello"}]
        result = clean_abnormal_segments(segs, max_word_duration=2.0)
        assert result[0]["end"] == pytest.approx(2.0)

    def test_start_offset_preserved_on_long_segment(self):
        segs = [{"start": 5.0, "end": 20.0, "word": "word"}]
        result = clean_abnormal_segments(segs)
        assert result[0]["start"] == 5.0
        assert result[0]["end"] == pytest.approx(8.0)  # 5.0 + 3.0

    def test_mixed_segments(self):
        segs = [
            {"start": 0.0, "end": 0.5, "word": "a"},
            {"start": 0.6, "end": 10.0, "word": "b"},
        ]
        result = clean_abnormal_segments(segs)
        assert result[0]["end"] == 0.5  # short: unchanged
        assert result[1]["end"] == pytest.approx(3.6)  # 0.6 + 3.0

    def test_word_field_preserved(self):
        segs = [{"start": 0.0, "end": 5.0, "word": "test"}]
        result = clean_abnormal_segments(segs)
        assert result[0]["word"] == "test"
