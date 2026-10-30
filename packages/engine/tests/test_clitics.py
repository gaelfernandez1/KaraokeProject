import pytest

from karaoke_contracts import Line, Part, Word
from karaoke_engine.align.clitics import join_clitics, join_enclitic


@pytest.mark.parametrize(
    ("verb", "pronoun", "joined"),
    [
        ("Deixou", "che", "Deixouche"),
        ("Dixen", "che", "Díxenche"),
        ("prometo", "lle", "prométolle"),
        ("quero", "te", "quérote"),
        ("deixa", "che", "déixache"),
        ("buscando", "che", "buscándoche"),
        ("dará", "che", "darache"),  # the stress moves to the second to last: no accent
        ("dá", "lle", "dálle"),  # a one-syllable verb keeps its accent
        ("saín", "che", "saínche"),  # the accent marks a hiatus: it stays
        ("vou", "che", "vouche"),
        ("dixo", "llelo", "díxollelo"),
        ("jaño", "che", "jáñoche"),  # dialectal spelling (gheada) stays as written
    ],
)
def test_join_enclitic(verb: str, pronoun: str, joined: str) -> None:
    assert join_enclitic(verb, pronoun) == joined


def _line(*words: tuple[str, float, float, list[tuple[str, float, float]]]) -> Line:
    built = [
        Word(
            text=t,
            start=s,
            end=e,
            confidence=0.9,
            parts=[Part(text=p, start=a, end=b) for p, a, b in parts],
        )
        for t, s, e, parts in words
    ]
    return Line(id="l1", start=built[0].start, end=built[-1].end, words=built)


def _texts(line: Line) -> list[str]:
    return [w.text for w in line.words]


def test_pronoun_after_a_verb_joins_it_and_keeps_its_timing() -> None:
    line = _line(
        ("Collín", 5.0, 5.4, [("Co", 5.0, 5.2), ("llín", 5.2, 5.4)]),
        ("che", 5.5, 5.6, []),
        ("flores", 5.8, 6.4, []),
    )

    (joined,) = join_clitics([line])

    # "collín" loses its accent: with "che" its stress falls on the second to last syllable.
    assert _texts(joined) == ["Collinche", "flores"]
    word = joined.words[0]
    assert (word.start, word.end) == (5.0, 5.6)
    assert [(p.text, p.start, p.end) for p in word.parts] == [
        ("Co", 5.0, 5.2),
        ("llin", 5.2, 5.4),
        ("che", 5.5, 5.6),
    ]


def test_accent_lands_in_the_right_part() -> None:
    line = _line(("Dixen", 1.0, 1.4, [("Di", 1.0, 1.2), ("xen", 1.2, 1.4)]), ("lle", 1.5, 1.7, []))

    (joined,) = join_clitics([line])

    assert [p.text for p in joined.words[0].parts] == ["Dí", "xen", "lle"]


def test_one_syllable_verb_becomes_two_parts() -> None:
    line = _line(("vou", 1.0, 1.3, []), ("che", 1.3, 1.5, []), ("dicir", 1.6, 2.0, []))

    (joined,) = join_clitics([line])

    assert _texts(joined) == ["vouche", "dicir"]
    assert [p.text for p in joined.words[0].parts] == ["vou", "che"]


@pytest.mark.parametrize(
    "text",
    [
        "non che digo",  # negation: the pronoun goes before the verb
        "que che quero",
        "xa che dixen",
        "como che dixen",  # "como" is a verb form too, but here it means "as"
        "o mar che leva",  # after a noun
        "vive nos meus soños",  # "nos" can be "in the"
        "dixen, che",  # punctuation in between
        "eu che digo",
    ],
)
def test_pronoun_stays_apart(text: str) -> None:
    words = text.split()
    line = _line(*((w, i, i + 0.5, []) for i, w in enumerate(words)))

    assert _texts(join_clitics([line])[0]) == words
