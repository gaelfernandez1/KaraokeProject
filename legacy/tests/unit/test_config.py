from karaoke.config import Settings


class TestAllowedEmailsParsing:
    def test_comma_separated_normalized_lowercase(self):
        settings = Settings(allowed_emails="Alice@Example.com, bob@y.com ,")
        assert settings.allowed_emails == ["alice@example.com", "bob@y.com"]

    def test_empty_string_is_empty_list(self):
        assert Settings(allowed_emails="").allowed_emails == []

    def test_list_input_is_normalized(self):
        settings = Settings(allowed_emails=["A@X.com", " b@y.com "])
        assert settings.allowed_emails == ["a@x.com", "b@y.com"]
