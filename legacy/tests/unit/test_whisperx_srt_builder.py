from whisperx_service.srt_builder import build_word_srt, sec2tc


class TestSec2tc:
    def test_formats_seconds_as_srt_timecode(self):
        assert sec2tc(0) == "00:00:00,000"
        assert sec2tc(1.5) == "00:00:01,500"
        assert sec2tc(3661.25) == "01:01:01,250"


class TestBuildWordSrt:
    def test_builds_blocks_for_aligned_words(self):
        segments = [
            {"word": "ola", "start": 0.0, "end": 0.5},
            {"word": "mundo", "start": 0.5, "end": 1.0},
        ]
        srt = build_word_srt(segments)
        assert srt == (
            "1\n00:00:00,000 --> 00:00:00,500\nola\n\n2\n00:00:00,500 --> 00:00:01,000\nmundo\n\n"
        )

    def test_skips_word_without_start_timestamp(self):
        # whisperx leaves words it cannot force-align without start/end keys;
        # the builder must skip them instead of raising KeyError.
        segments = [
            {"word": "ola", "start": 0.0, "end": 0.5},
            {"word": "sen"},  # unaligned: no start/end
            {"word": "mundo", "start": 1.0, "end": 1.5},
        ]
        srt = build_word_srt(segments)
        assert "ola" in srt
        assert "mundo" in srt
        assert "sen" not in srt
        # surviving blocks are renumbered contiguously
        assert "1\n00:00:00,000" in srt
        assert "2\n00:00:01,000" in srt

    def test_skips_word_with_none_timestamp(self):
        segments = [
            {"word": "ola", "start": 0.0, "end": 0.5},
            {"word": "nada", "start": None, "end": None},
        ]
        srt = build_word_srt(segments)
        assert "nada" not in srt
        assert "ola" in srt

    def test_prefixes_speaker_color_when_available(self):
        segments = [{"word": "ola", "start": 0.0, "end": 0.5, "speaker": "SPEAKER_00"}]
        srt = build_word_srt(segments, {"SPEAKER_00": "#FF0000"})
        assert "SPEAKER_00|#FF0000|ola" in srt

    def test_empty_when_no_words_align(self):
        assert build_word_srt([{"word": "a"}, {"word": "b", "start": None}]) == ""
