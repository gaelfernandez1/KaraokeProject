import pytest

from karaoke_engine.align.numbers import number_words
from karaoke_engine.align.spoken import spoken


@pytest.mark.parametrize(
    ("n", "words"),
    [
        (0, "cero"),
        (1, "un"),
        (2, "dous"),
        (16, "dezaseis"),
        (21, "vinte e un"),
        (99, "noventa e nove"),
        (100, "cen"),
        (101, "cento un"),
        (120, "cento vinte"),
        (500, "cincocentos"),
        (1990, "mil novecentos noventa"),
        (2024, "dous mil vinte e catro"),
    ],
)
def test_galician_numbers(n: int, words: str) -> None:
    assert number_words(n, "gl") == words


@pytest.mark.parametrize(
    ("n", "words"),
    [(21, "veintiuno"), (16, "dieciséis"), (100, "cien"), (2024, "dos mil veinticuatro")],
)
def test_spanish_numbers(n: int, words: str) -> None:
    assert number_words(n, "es") == words


def test_portuguese_numbers() -> None:
    assert number_words(2, "pt") == "dois"
    assert number_words(21, "pt") == "vinte e um"


def test_english_numbers() -> None:
    assert number_words(42, "en") == "forty two"
    assert number_words(1990, "en") == "one thousand nine hundred ninety"


def test_unknown_language_or_range() -> None:
    assert number_words(3, "de") is None
    assert number_words(12345, "gl") is None


def test_spoken_spells_numbers_and_drops_punctuation() -> None:
    assert spoken("2024,", "gl") == "dous mil vinte e catro"
    assert spoken("¡Vente!", "gl") == "vente"


def test_spoken_symbols_by_language() -> None:
    assert spoken("Rock&Roll", "en") == "rock and roll"
    assert spoken("100%", "es") == "cien por ciento"


def test_spoken_keeps_inner_apostrophes() -> None:
    assert spoken("d’aquí", "gl") == "d'aquí"
    assert spoken("'cause", "en") == "cause"


def test_spoken_can_be_empty() -> None:
    assert spoken("…", "gl") == ""


def test_spoken_keeps_digits_without_a_speller() -> None:
    assert spoken("99", "de") == "99"
