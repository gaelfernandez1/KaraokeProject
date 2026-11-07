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
    text = "Ola\n\nA\nB\n(x2)\nC\n"

    assert _texts(parse_lyrics(text)) == ["Ola", "A", "B", "A", "B", "C"]


def test_header_repeat_mark_repeats_its_section() -> None:
    text = "[Coro x2]\nA\nB\n[Verso]\nC\n"

    assert _texts(parse_lyrics(text)) == ["A", "B", "A", "B", "C"]


def test_empty_chorus_header_repeats_previous_chorus() -> None:
    text = "[Estribillo]\nA\nB\n\n[Verso 2]\nC\n\n[Estribillo]\n\n[Final]\nD\n"

    lines = parse_lyrics(text)

    assert _texts(lines) == ["A", "B", "C", "A", "B", "D"]
    assert lines[3].section == "Estribillo"


def test_crlf_bom_and_punctuation_lines() -> None:
    assert _texts(parse_lyrics("\ufeffA\r\n...\r\n♪\r\nB")) == ["A", "B"]


def test_inline_square_brackets_are_dropped() -> None:
    assert _texts(parse_lyrics("Vou [?] contigo\n")) == ["Vou contigo"]


def test_x2_alone_after_a_blank_line_repeats_the_stanza_before_it() -> None:
    assert _texts(parse_lyrics("A\nB\n\nx2\nC\n")) == ["A", "B", "A", "B", "C"]


def test_bis_ending_a_sung_line_is_part_of_the_lyrics() -> None:
    assert _texts(parse_lyrics("Quero un bis\n")) == ["Quero un bis"]


def test_bis_alone_or_in_parentheses_repeats() -> None:
    assert _texts(parse_lyrics("Ola (bis)\n\nMar\nbis\n")) == ["Ola", "Ola", "Mar", "Mar"]


def test_invisible_characters_from_web_pages_are_ignored() -> None:
    text = "[Estribillo]\u200b\nA\n\n[Verso]\nB\n\n\ufeff[Estribillo]\n"

    assert _texts(parse_lyrics(text)) == ["A", "B", "A"]


def test_unusual_line_breaks_split_lines() -> None:
    assert _texts(parse_lyrics("A\rB\u2028C")) == ["A", "B", "C"]


def test_repeat_mark_after_a_section_label_repeats_the_section() -> None:
    text = "[Estribillo]\nA\n\n[Verso]\nB\n\n[Estribillo] x2\n\n[Final]\nC\n"
    assert _texts(parse_lyrics(text)) == ["A", "B", "A", "A", "C"]
    text = "[Estribillo]\nA\n\n[Estribillo] (x2)\n"
    assert _texts(parse_lyrics(text)) == ["A", "A", "A"]
    assert _texts(parse_lyrics("[Coro]\nA\n\n[Coro] (bis)\n")) == ["A", "A", "A"]


def test_number_first_repeat_marks_from_portuguese_sites() -> None:
    assert _texts(parse_lyrics("Linha um (2x)\nFim\n")) == ["Linha um", "Linha um", "Fim"]
    assert _texts(parse_lyrics("Linha um 2x\nFim\n")) == ["Linha um", "Linha um", "Fim"]
    assert _texts(parse_lyrics("[Refrão 2x]\nA\n[Verso]\nB\n")) == ["A", "A", "B"]
    assert _texts(parse_lyrics("[Refrão]\nA\n\n[Refrão] 2x\n")) == ["A", "A", "A"]


def test_a_name_like_x6_at_the_end_of_a_line_is_lyrics() -> None:
    assert _texts(parse_lyrics("Baixo do BMW X6\nFin\n")) == ["Baixo do BMW X6", "Fin"]
    assert _texts(parse_lyrics("Isto é x0\nFin\n")) == ["Isto é x0", "Fin"]


def test_accents_typed_apart_are_composed() -> None:
    [line] = parse_lyrics("collín che\n")
    assert line.text == "collín che"


def test_a_named_chorus_takes_the_singer_of_its_new_label() -> None:
    text = "[Estribillo: Ana]\nA\n\n[Verso: Brais]\nB\n\n[Estribillo: Uxía]\n"
    lines = parse_lyrics(text)
    assert [(line.text, line.singer) for line in lines] == [
        ("A", "Ana"),
        ("B", "Brais"),
        ("A", "Uxía"),
    ]
