import pytest

from karaoke_engine.align.syllables import syllables


@pytest.mark.parametrize(
    ("word", "parts"),
    [
        ("camiñando", ["ca", "mi", "ñan", "do"]),
        ("queixo", ["quei", "xo"]),
        ("esperándoche", ["es", "pe", "rán", "do", "che"]),
        ("corazón,", ["co", "ra", "zón,"]),
        ("chorar", ["cho", "rar"]),
        ("aire", ["ai", "re"]),
        ("río", ["rí", "o"]),
        ("país", ["pa", "ís"]),
        ("¡vente!", ["¡ven", "te!"]),
        ("Unha", ["U", "nha"]),
        ("ollos", ["o", "llos"]),
        ("guerra", ["gue", "rra"]),
    ],
)
def test_galician_syllables(word: str, parts: list[str]) -> None:
    assert syllables(word, "gl") == parts


def test_spanish_clusters_stay_together() -> None:
    assert syllables("transporte", "es") == ["trans", "por", "te"]
    assert syllables("construir", "es") == ["cons", "truir"]


def test_parts_always_spell_the_word() -> None:
    for word in ["¿Pensar?", "dixestes...", "Vou-te", "d'aquí", "AMORRER,"]:
        parts = syllables(word, "gl")
        assert parts is None or "".join(parts) == word


@pytest.mark.parametrize(("word", "language"), [("ma", "gl"), ("de", "en"), ("2024", "gl")])
def test_no_parts(word: str, language: str) -> None:
    assert syllables(word, language) is None


def test_qu_ending_a_word_keeps_its_vowel() -> None:
    assert syllables("caqui", "gl") == ["ca", "qui"]
    assert syllables("tegu", "gl") == ["te", "gu"]
