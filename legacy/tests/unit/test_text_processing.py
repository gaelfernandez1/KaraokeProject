from karaoke.domain.text_processing import normalize_manual_lyrics


class TestNormalizeManualLyrics:
    def test_strips_leading_and_trailing_whitespace(self):
        result = normalize_manual_lyrics("  hello  \n  world  ")
        lines = result.splitlines()
        assert lines[0] == "hello"
        assert lines[1] == "world"

    def test_removes_blank_lines(self):
        result = normalize_manual_lyrics("hello\n\nworld")
        assert result == "hello\nworld"

    def test_removes_tag_annotations(self):
        result = normalize_manual_lyrics("[Verse 1]\nhello\n[Chorus]\nworld")
        assert "[Verse 1]" not in result
        assert "[Chorus]" not in result
        assert "hello" in result
        assert "world" in result

    def test_preserves_plain_content(self):
        result = normalize_manual_lyrics("hello world")
        assert result == "hello world"

    def test_empty_string_returns_empty(self):
        assert normalize_manual_lyrics("") == ""

    def test_only_tags_returns_empty(self):
        result = normalize_manual_lyrics("[Verse 1]\n[Chorus]\n[Bridge]")
        assert result == ""

    def test_inline_tag_stripped_leaving_remaining_text(self):
        result = normalize_manual_lyrics("[intro] hello world")
        assert "[intro]" not in result
        assert "hello world" in result

    def test_multiple_blank_lines_collapsed_to_none(self):
        result = normalize_manual_lyrics("a\n\n\n\nb")
        assert result == "a\nb"

    def test_single_line_no_newline(self):
        result = normalize_manual_lyrics("solo")
        assert result == "solo"

    def test_fixture_file(self, sample_lyrics_text):
        # fixture: "Hello world\nThis is a test\n[Chorus]\nGoodbye my friend"
        result = normalize_manual_lyrics(sample_lyrics_text)
        assert "[Chorus]" not in result
        lines = result.splitlines()
        assert len(lines) == 3  # tag stripped, 3 content lines remain
