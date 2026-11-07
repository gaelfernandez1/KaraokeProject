"""Lyrics pasted straight from a web page: what the page adds is not sung.

The songs here are made up; each test copies the shape a real site leaves in the clipboard.
"""

import time

from karaoke_engine.align.lyrics import LyricLine, parse_lyrics
from karaoke_engine.align.pasted import strip_page_text

GENIUS_PAGE = """\
[Intro]
Ola, que tal a noite
Vimos cantar á praia

[Verso 1: Ana]
Non sei se quedar
Ou marchar contigo
Hai tempo que agardo (Yeah)
You might also like
Ana & Brais - Mar (Traducción al Español)
Genius Traducciones al Español
Outra canción
Brais & Uxía
Ana - Vento (English Translation)
Genius English Translations
[Retrouso: Ana]
Foi un verán perdido
E non me esquezo

[Outro: Brais]
Foi un verán
"""


def _texts(lines: list[LyricLine]) -> list[str]:
    return [line.text for line in lines]


def test_genius_song_recommendations_are_not_sung() -> None:
    lines = parse_lyrics(GENIUS_PAGE)

    assert _texts(lines) == [
        "Ola, que tal a noite",
        "Vimos cantar á praia",
        "Non sei se quedar",
        "Ou marchar contigo",
        "Hai tempo que agardo",
        "Yeah",
        "Foi un verán perdido",
        "E non me esquezo",
        "Foi un verán",
    ]
    assert [(line.section, line.singer) for line in lines[6:]] == [
        ("Retrouso", "Ana"),
        ("Retrouso", "Ana"),
        ("Outro", "Brais"),
    ]


def test_the_recommendations_leave_a_stanza_break() -> None:
    # Genius puts them where the blank line between two stanzas was.
    text = "A\nB\nYou might also like\nMar\nAna\nVento\nBrais\nLúa\nUxía\nC\nD\nx2\n"

    assert _texts(parse_lyrics(text)) == ["A", "B", "C", "D", "C", "D"]


def test_lyrics_after_the_three_recommendations_are_kept() -> None:
    text = (
        "Non sei se quedar\nYou might also like\n"
        "Mar\nAna\nVento\nBrais\nLúa\nUxía\n"
        "Segue a canción\n"
    )

    assert _texts(parse_lyrics(text)) == ["Non sei se quedar", "Segue a canción"]


def test_a_marker_without_recommendations_drops_only_itself() -> None:
    assert _texts(parse_lyrics("A\nYou might also like\n\nB\nC\n")) == ["A", "B", "C"]
    lines = parse_lyrics("Vai o vento (Yeah)You might also like[Coro: Ana]\nMar\n")
    assert _texts(lines) == ["Vai o vento", "Yeah", "Mar"]
    assert (lines[2].section, lines[2].singer) == ("Coro", "Ana")


def test_genius_page_header_and_footer() -> None:
    glued = "12 ContributorsTranslationsEnglishCanción Lyrics\n[Intro]\nA\n\n[Verso]\nB5Embed"
    assert _texts(parse_lyrics(glued)) == ["A", "B"]
    apart = (
        "12 Contributors\nTranslations\nEnglish\nEspañol\nCanción Lyrics\n"
        "“Canción” é o primeiro sinxelo do disco… Read More \n"
        "[Intro]\nA\nEmbed\n"
    )
    assert _texts(parse_lyrics(apart)) == ["A"]


def test_ticket_adverts_are_not_sung() -> None:
    assert _texts(parse_lyrics("A\nSee Ana Live\nGet tickets as low as $45\nB\n")) == ["A", "B"]
    assert _texts(parse_lyrics("A\nSee Ana LiveGet tickets as low as $45\nB\n")) == ["A", "B"]


def test_translation_links_are_not_sung_anywhere() -> None:
    text = "A\nAna - Mar (Tradução em Português)\nGenius Brasil Traduções\nB\n"

    assert _texts(parse_lyrics(text)) == ["A", "B"]


def test_credits_and_footers_of_lyrics_sites() -> None:
    musixmatch = "A\nB\n\nWriter(s): Ana Pérez, Brais Vila\nLyrics powered by www.musixmatch.com\n"
    google = "A\nB\nFuente: Musixmatch\nCompositores: Ana Pérez / Brais Vila\n"
    google += "Letra de Mar © Sony Music Publishing\n"
    letras = "A\nB\n\nComposição: Ana Pérez. Essa informação está errada? Nos avise.\n"
    letras += "Enviada por Uxía e traduzida por Brais. Legendado por Ana.\n"
    letras += "Esta letra ainda não foi revisada.\n"
    azlyrics = "A\nB\n\nSubmit Corrections\nThanks to Uxía for correcting these lyrics\n"
    for page in (musixmatch, google, letras, azlyrics):
        assert _texts(parse_lyrics(page)) == ["A", "B"], page


def test_video_description_around_the_lyrics() -> None:
    text = (
        "Ana - Mar (Video Oficial)\nDirixido por Uxía Vila\n\nLetra:\nA\nB\n\n"
        "Prod: Brais Beats\nMix & Master: Estudio Lúa\nInstagram: @ana\n"
        "Escoita Mar en https://example.com/mar\n#Ana #Mar\n"
        "℗ 2026 Selo Galego\n"
    )

    assert _texts(parse_lyrics(text)) == ["A", "B"]


def test_section_labels_without_brackets() -> None:
    text = "CORO:\nA\nB\n\nVerso 2 (Ana):\nC\n\nCoro\n\nPuente:\nD\n"

    lines = parse_lyrics(text)

    assert _texts(lines) == ["A", "B", "C", "A", "B", "D"]
    assert (lines[2].section, lines[2].singer) == ("Verso 2", "Ana")
    assert lines[5].section == "Puente"


def test_labels_in_parentheses_braces_or_asterisks() -> None:
    text = "(Estribillo)\nA\n\n**Verso**\nB\n\n{Chorus}\nC\n\n(Estribillo x2)\n"

    assert _texts(parse_lyrics(text)) == ["A", "B", "C", "A", "A"]


def test_instructions_to_repeat_the_chorus() -> None:
    assert _texts(parse_lyrics("[Estribillo]\nA\n\n[Verso]\nB\n\nRepetir estribillo\n")) == [
        "A", "B", "A",
    ]  # fmt: skip
    assert _texts(parse_lyrics("[Chorus]\nA\n\n[Verse]\nB\n\n(Repeat chorus x2)\n")) == [
        "A", "B", "A", "A",
    ]  # fmt: skip
    # The site calls it «coro» the second time.
    assert _texts(parse_lyrics("[Estribillo]\nA\n\n[Verso]\nB\n\nRepite el coro\n")) == [
        "A", "B", "A",
    ]  # fmt: skip


def test_a_label_followed_by_the_first_line() -> None:
    lines = parse_lyrics("Coro: Eu canto contigo\nOutra liña\n")

    assert _texts(lines) == ["Eu canto contigo", "Outra liña"]
    assert [line.section for line in lines] == ["Coro", "Coro"]


def test_stage_directions_are_not_sung() -> None:
    text = "Vai o vento (risas)\n(Instrumental)\n(Hablado) Mira isto\n(Oh) mar\n"

    lines = parse_lyrics(text)

    assert _texts(lines) == ["Vai o vento", "Mira isto", "Oh", "mar"]
    assert [line.backing for line in lines] == [False, False, True, False]


def test_who_sings_written_before_the_line() -> None:
    lines = parse_lyrics("Ela: Vente comigo\nÉl: Non podo\nOs dous: Imos\n")

    assert _texts(lines) == ["Vente comigo", "Non podo", "Imos"]
    assert [line.singer for line in lines] == ["Ela", "Él", "Os dous"]


def test_subtitle_and_transcript_timings() -> None:
    srt = "1\n00:00:12,340 --> 00:00:15,000\nA\n\n2\n00:00:15,100 --> 00:00:17,000\nB\n"
    assert _texts(parse_lyrics(srt)) == ["A", "B"]
    assert _texts(parse_lyrics("0:12\nA\n1:05\nB\n")) == ["A", "B"]
    lrc = "[ti:Mar]\n[ar:Ana]\n[00:12.34]A\n[00:15.00] <00:15.00>B <00:15.60>C\n"
    lines = parse_lyrics(lrc)
    assert _texts(lines) == ["A", "B C"]
    assert [line.singer for line in lines] == [None, None]


def test_verse_numbers_alone_are_not_sung() -> None:
    assert _texts(parse_lyrics("1.\nA\n\n2)\nB\n")) == ["A", "B"]


def test_lines_that_only_look_like_page_text_are_sung() -> None:
    text = (
        "Solo\nPonte guapa\nFinal feliz\nLetra de amor\nSee you live\n"
        "Quero un bis\nBaixo do BMW X6\nUn verán ao ritmo do Show\n"
        "Coro de vellos: cantan\nEu fun ao Instagram e non estabas\n"
    )

    assert _texts(parse_lyrics(text)) == text.splitlines()


def test_title_and_artist_above_the_lyrics() -> None:
    def sung(text: str) -> list[str]:
        return _texts(parse_lyrics(strip_page_text(text, title="Mar", artist="Ana")))

    assert sung("Mar\nAna\n\nA\nB\n") == ["A", "B"]
    assert sung("Letra de Mar - Ana\nA\nB\n") == ["A", "B"]
    assert sung("Mar\n[Intro]\nA\n") == ["A"]
    # A song that opens with its title sings it.
    assert sung("Mar\nVai o vento\n") == ["Mar", "Vai o vento"]


def test_stripping_twice_changes_nothing() -> None:
    once = strip_page_text(GENIUS_PAGE)

    assert strip_page_text(once) == once


def test_a_line_built_to_stall_the_hashtag_check_is_read_at_once() -> None:
    row = "#" + "!#" * 26 + " x"

    started = time.perf_counter()
    lines = parse_lyrics(f"{row}\n#Ana #Mar\n")
    seconds = time.perf_counter() - started

    assert seconds < 0.5
    assert _texts(lines) == [row]
