from pathlib import Path

import pytest
from pydantic import ValidationError

from karaoke_bench.reference import (
    Reference,
    RefLine,
    RefWord,
    dump_reference,
    load_reference,
    reference_from_doc,
)
from karaoke_contracts import load_doc


def _line(text: str, n_words: int, status: str = "ok", start: float = 0.0) -> RefLine:
    words = [RefWord(text=f"w{i}", start=start + i, end=start + i + 0.5) for i in range(n_words)]
    return RefLine.model_validate(
        {"text": text, "start": start, "end": start + n_words, "words": words, "status": status}
    )


def _reference(lines: list[RefLine]) -> Reference:
    return Reference(song_id="s", language="gl", duration=60.0, timing="semiautomatic", lines=lines)


def test_roundtrip_keeps_galician_text(tmp_path: Path) -> None:
    word = RefWord(text="d’aquí", start=1.0, end=1.5)
    ref = _reference([RefLine(text="Vou-te ver, d’aquí", start=0.5, end=1.5, words=[word])])
    path = tmp_path / "reference.json"

    dump_reference(ref, path)

    assert "d’aquí" in path.read_text(encoding="utf-8")
    assert load_reference(path) == ref


def test_scored_words_only_from_ok_lines() -> None:
    ref = _reference([_line("a", 2, "ok"), _line("b", 3, "wrong", 10), _line("c", 5, "unsure", 20)])

    assert len(ref.scored_words()) == 2
    assert [line.text for line in ref.scored_lines()] == ["a"]
    assert ref.scored_share() == pytest.approx(0.2)


def test_scored_share_without_words_is_zero() -> None:
    assert _reference([]).scored_share() == 0.0


def test_lyrics_text_joins_line_texts() -> None:
    ref = _reference([_line("Ola mar", 1), _line("Adeus", 1, start=5)])

    assert ref.lyrics_text() == "Ola mar\nAdeus"


def test_unknown_status_rejected() -> None:
    with pytest.raises(ValidationError):
        _line("a", 1, status="maybe")


def test_reference_from_demo_doc(demo_json: Path) -> None:
    doc = load_doc(demo_json)

    ref = reference_from_doc(doc, timing="manual")

    assert len(ref.lines) == len(doc.lines)
    assert ref.lines[0].start == 4.0
    assert all(line.status == "ok" for line in ref.lines)
    assert ref.approved
    assert ref.lines[0].words[0].text == doc.lines[0].words[0].text
