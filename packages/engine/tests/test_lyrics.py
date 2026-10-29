from karaoke_engine.align.lyrics import LyricLine, parse_lyrics


def _texts(lines: list[LyricLine]) -> list[str]:
    return [line.text for line in lines]


def test_plain_lines_keep_their_text_and_words() -> None:
    [line] = parse_lyrics("Díxenche, ¡vente!\n")

    assert line.text == "Díxenche, ¡vente!"
    assert line.words == ("Díxenche,", "¡vente!")
    assert (line.section, line.singer, line.backing) == (None, None, False)


def test_header_sets_section_and_singer() -> None:
    lines = parse_lyrics("[Verso 1: Ana]\nOla\n\n[Estribillo]\nMar\n")

    assert [(line.section, line.singer) for line in lines] == [
        ("Verso 1", "Ana"),
        ("Estribillo", None),
    ]


def test_parenthesised_part_becomes_backing_line() -> None:
    lines = parse_lyrics("Vou contigo (contigo, contigo)\n")

    assert _texts(lines) == ["Vou contigo", "contigo, contigo"]
    assert [line.backing for line in lines] == [False, True]


def test_backing_part_before_the_lead_keeps_its_order() -> None:
    lines = parse_lyrics("(Oh) vai o vento\n")

    assert _texts(lines) == ["Oh", "vai o vento"]
    assert [line.backing for line in lines] == [True, False]


def test_line_in_parentheses_is_backing() -> None:
    [line] = parse_lyrics("(La la la)\n")

    assert line.text == "La la la"
    assert line.backing


def test_x2_repeats_line() -> None:
    assert _texts(parse_lyrics("Volta x2\nFin\n")) == ["Volta", "Volta", "Fin"]


def test_other_repeat_marks() -> None:
    text = "Uno (x3)\nDos (bis)\nTres \u00d72\n"

    assert _texts(parse_lyrics(text)) == ["Uno"] * 3 + ["Dos"] * 2 + ["Tres"] * 2


def test_x2_alone_repeats_stanza() -> None:
    text = "Intro\n\nA\nB\n(x2)\nC\n"

    assert _texts(parse_lyrics(text)) == ["Intro", "A", "B", "A", "B", "C"]


def test_header_repeat_mark_repeats_its_section() -> None:
    text = "[Coro x2]\nA\nB\n[Verso]\nC\n"

    assert _texts(parse_lyrics(text)) == ["A", "B", "A", "B", "C"]


def test_empty_chorus_header_repeats_previous_chorus() -> None:
    text = "[Estribillo]\nA\nB\n\n[Verso 2]\nC\n\n[Estribillo]\n\n[Final]\nD\n"

    lines = parse_lyrics(text)

    assert _texts(lines) == ["A", "B", "C", "A", "B", "D"]
    assert lines[3].section == "Estribillo"


def test_crlf_bom_and_punctuation_lines() -> None:
    assert _texts(parse_lyrics("﻿A\r\n...\r\n♪\r\nB")) == ["A", "B"]


def test_inline_square_brackets_are_dropped() -> None:
    assert _texts(parse_lyrics("Vou [?] contigo\n")) == ["Vou contigo"]
