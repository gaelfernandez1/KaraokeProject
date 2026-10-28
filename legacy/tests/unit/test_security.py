from karaoke.security import sanitize_filename, validate_file_size


class TestValidateFileSize:
    def test_under_limit_allowed(self):
        assert validate_file_size(50, max_size_mb=100) is True

    def test_at_limit_allowed(self):
        assert validate_file_size(100, max_size_mb=100) is True

    def test_over_limit_rejected(self):
        assert validate_file_size(101, max_size_mb=100) is False

    def test_default_limit_100mb(self):
        assert validate_file_size(99) is True
        assert validate_file_size(101) is False

    def test_zero_allowed(self):
        assert validate_file_size(0) is True


class TestSanitizeFilenameFromSecurity:
    def test_removes_angle_brackets(self):
        result = sanitize_filename("file<name>.txt")
        assert "<" not in result
        assert ">" not in result

    def test_removes_colon(self):
        assert ":" not in sanitize_filename("C:/path/file.txt")

    def test_removes_quote_and_backslash(self):
        result = sanitize_filename('fi"le\\name.txt')
        assert '"' not in result
        assert "\\" not in result

    def test_removes_pipe_question_asterisk(self):
        result = sanitize_filename("file|name?.*.txt")
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result

    def test_truncates_to_255_chars(self):
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 255

    def test_normal_filename_preserved(self):
        assert sanitize_filename("normal_file.mp4") == "normal_file.mp4"
