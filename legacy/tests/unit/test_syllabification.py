import pytest

from karaoke.domain import syllabification
from karaoke.domain.syllabification import SUPPORTED_LANGS, syllabify, syllabify_text


@pytest.fixture(autouse=True)
def _clear_cache():
    # The dict cache is module-level state shared across tests; reset it so the
    # instantiation-counting test stays deterministic regardless of test order.
    syllabification._dict_cache.clear()
    yield
    syllabification._dict_cache.clear()


class TestSyllabify:
    def test_galician_word(self):
        assert syllabify("canto", "gl") == ["can", "to"]

    def test_spanish_word(self):
        assert syllabify("palabra", "es") == ["pa", "la", "bra"]

    def test_english_word(self):
        assert syllabify("beautiful", "en") == ["beau", "ti", "ful"]

    def test_galician_is_default_supported(self):
        assert "gl" in SUPPORTED_LANGS

    def test_unknown_language_returns_list_and_warns(self, mocker):
        # Spy on the logger rather than use caplog: configure_logging() clears the
        # root handlers, which removes pytest's capture handler if an app-creating
        # test ran first, making caplog flaky in the full suite.
        warn = mocker.spy(syllabification.logger, "warning")
        result = syllabify("hola", "zh")
        assert isinstance(result, list)
        assert result  # non-empty
        assert warn.call_count == 1
        assert "zh" in warn.call_args.args

    def test_dict_instantiated_only_once_per_language(self, mocker):
        fake_ctor = mocker.patch("karaoke.domain.syllabification.pyphen.Pyphen")
        fake_ctor.return_value.inserted.return_value = "can-to"

        syllabify("canto", "es")
        syllabify("canto", "es")

        assert fake_ctor.call_count == 1


class TestSyllabifyText:
    def test_joins_syllables_with_hyphen_and_words_with_space(self):
        assert syllabify_text("canto bonito", "gl") == "can-to bo-ni-to"
