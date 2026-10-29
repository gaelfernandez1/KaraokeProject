from karaoke_bench.textnorm import fold, lyrics_lines, match_key, normalize, tokens


def test_normalize_keeps_accents_and_inner_apostrophes() -> None:
    assert normalize("¿Quén é?  Vou-te ver, d’aquí!") == "quén é vou te ver d'aquí"


def test_normalize_drops_labels_and_repeats_but_keeps_backing_vocals() -> None:
    assert normalize("[Estribillo]\nOla (ola) mar x2") == "ola ola mar"


def test_normalize_drops_other_repeat_marks() -> None:
    assert normalize("Adeus \u00d73\nVai (bis)\nMar (x2)\nRío bis") == "adeus vai mar río"


def test_normalize_handles_quotes_and_outer_apostrophes() -> None:
    assert normalize("«Meu» 'amor' “lindo”") == "meu amor lindo"


def test_normalize_e_and_accented_e_stay_distinct() -> None:
    assert tokens("É e é") == ["é", "e", "é"]


def test_normalize_composes_unicode() -> None:
    decomposed = "é"
    assert normalize(decomposed) == "é"


def test_fold_strips_diacritics() -> None:
    assert [fold(t) for t in ["quén", "ñ", "ç", "línea"]] == ["quen", "n", "c", "linea"]


def test_match_key_joins_hyphenated_and_drops_punctuation_only() -> None:
    assert match_key("Vou-te,") == "voute"
    assert match_key("—") == ""


def test_lyrics_lines_cleans_pasted_lyrics() -> None:
    text = "﻿[Verso 1]\r\nOla mar x2\r\n\r\n(eh) adeus «meu» amor\n[Estribillo]\n"
    assert lyrics_lines(text) == ["Ola mar", "(eh) adeus «meu» amor"]


def test_lyrics_lines_drops_lines_left_empty() -> None:
    assert lyrics_lines("Ola\n(x2)\n  \nAdeus") == ["Ola", "Adeus"]
