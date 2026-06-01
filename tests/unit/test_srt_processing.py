import pytest

from karaoke.domain.srt_processing import (
    group_word_segments,
    group_word_segments_automatic,
    parse_word_srt,
)


def _make_segs(n: int, word_duration: float = 0.3, gap: float = 0.05):
    segs = []
    t = 0.0
    for i in range(n):
        segs.append(
            {
                "start": t,
                "end": t + word_duration,
                "word": f"w{i}",
                "speaker": None,
                "color": None,
            }
        )
        t += word_duration + gap
    return segs


class TestParseWordSrt:
    def test_nonexistent_file_returns_empty(self):
        assert parse_word_srt("/nonexistent/nowhere.srt") == []

    def test_parses_correct_number_of_tokens(self, sample_srt_path):
        # fixture: "hello world" (2), "this is a test" (4), "goodbye" (1) = 7
        segs = parse_word_srt(sample_srt_path)
        assert len(segs) == 7

    def test_segment_has_required_keys(self, sample_srt_path):
        for seg in parse_word_srt(sample_srt_path):
            assert "start" in seg
            assert "end" in seg
            assert "word" in seg

    def test_start_strictly_before_end(self, sample_srt_path):
        for seg in parse_word_srt(sample_srt_path):
            assert seg["start"] < seg["end"]

    def test_multiword_block_distributes_time_evenly(self, sample_srt_path):
        # Block 1: 00:00:01,000 → 00:00:02,500 (1.5 s), "hello world" = 2 tokens → 0.75 s each
        segs = parse_word_srt(sample_srt_path)
        hello = next(s for s in segs if s["word"] == "hello")
        world = next(s for s in segs if s["word"] == "world")
        assert (hello["end"] - hello["start"]) == pytest.approx(0.75, abs=0.001)
        assert (world["end"] - world["start"]) == pytest.approx(0.75, abs=0.001)

    def test_speaker_format_parsed_correctly(self, sample_speakers_srt_path):
        segs = parse_word_srt(sample_speakers_srt_path)
        with_speaker = [s for s in segs if s.get("speaker") is not None]
        assert len(with_speaker) > 0
        first = with_speaker[0]
        assert first["speaker"] == "SPEAKER_00"
        assert first["color"] == "#FF5733"
        assert first["word"] == "hello"

    def test_long_block_clamped_by_clean_abnormal(self, tmp_path):
        # A 60-second block with one word should be clamped to 3 s by clean_abnormal_segments
        srt = "1\n00:00:00,000 --> 00:01:00,000\nword\n\n"
        (tmp_path / "long.srt").write_text(srt)
        segs = parse_word_srt(str(tmp_path / "long.srt"))
        assert len(segs) == 1
        assert (segs[0]["end"] - segs[0]["start"]) <= 3.0

    def test_empty_srt_file_returns_empty(self, tmp_path):
        (tmp_path / "empty.srt").write_text("")
        assert parse_word_srt(str(tmp_path / "empty.srt")) == []


class TestGroupWordSegments:
    def test_basic_grouping_produces_one_group_per_lyric_line(self):
        segs = _make_segs(3)
        result = group_word_segments("hello world\ngoodbye", segs)
        assert len(result) == 2

    def test_empty_segments_returns_empty(self):
        assert group_word_segments("hello\nworld", []) == []

    def test_empty_lyrics_returns_empty(self):
        assert group_word_segments("", _make_segs(3)) == []

    def test_line_text_matches_lyric_line(self):
        segs = _make_segs(3)
        result = group_word_segments("hello world\ngoodbye", segs)
        assert result[0]["line_text"] == "hello world"
        assert result[1]["line_text"] == "goodbye"

    def test_tag_lines_treated_as_regular_lines(self):
        # TODO(F5): group_word_segments does NOT strip [tag] annotations; they are treated
        # as ordinary lyric lines. Tag stripping must happen before calling this function.
        segs = _make_segs(4)
        result = group_word_segments("[Chorus]\nhello world\ngoodbye", segs)
        # "[Chorus]" is counted as a 1-word line, producing 3 groups from 4 segments
        assert len(result) == 3

    def test_group_start_and_end_span_assigned_tokens(self):
        segs = _make_segs(5)
        result = group_word_segments("a b c\nd e", segs)
        assert result[0]["start"] == segs[0]["start"]
        assert result[0]["end"] == segs[2]["end"]
        assert result[1]["start"] == segs[3]["start"]
        assert result[1]["end"] == segs[4]["end"]

    def test_all_segments_allocated(self):
        segs = _make_segs(6)
        result = group_word_segments("three words here\nthree more", segs)
        total = sum(len(g["words"]) for g in result)
        assert total == 6


class TestGroupWordSegmentsAutomatic:
    def test_empty_returns_empty(self):
        assert group_word_segments_automatic([]) == []

    def test_respects_max_words_per_phrase(self):
        segs = _make_segs(20)
        result = group_word_segments_automatic(segs, max_words_per_phrase=4)
        for group in result:
            assert len(group["words"]) <= 4

    def test_all_words_covered(self):
        segs = _make_segs(10)
        result = group_word_segments_automatic(segs)
        total = sum(len(g["words"]) for g in result)
        assert total == 10

    def test_sentence_ending_punctuation_triggers_group_close(self):
        segs = [
            {"start": 0.0, "end": 0.4, "word": "hello", "speaker": None, "color": None},
            {"start": 0.5, "end": 0.9, "word": "world.", "speaker": None, "color": None},
            {"start": 1.0, "end": 1.4, "word": "goodbye", "speaker": None, "color": None},
        ]
        result = group_word_segments_automatic(segs, max_words_per_phrase=10)
        assert len(result) >= 2

    def test_large_pause_triggers_group_close(self):
        segs = [
            {"start": 0.0, "end": 0.5, "word": "hello", "speaker": None, "color": None},
            {"start": 2.0, "end": 2.5, "word": "world", "speaker": None, "color": None},  # 1.5 s gap > 0.8 s
        ]
        result = group_word_segments_automatic(segs, max_words_per_phrase=10)
        assert len(result) == 2

    def test_single_word_produces_one_group(self):
        segs = [{"start": 0.0, "end": 1.0, "word": "only", "speaker": None, "color": None}]
        result = group_word_segments_automatic(segs)
        assert len(result) == 1
        assert result[0]["words"][0]["word"] == "only"
