import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from karaoke_contracts import KaraokeDoc, dump_doc, load_doc, validate_doc


def test_demo_fixture_loads_and_has_no_issues(demo_json: Path) -> None:
    doc = load_doc(demo_json)

    assert doc.language == "gl"
    assert validate_doc(doc) == []


def test_dump_keeps_galician_text(demo_json: Path, tmp_path: Path) -> None:
    text = "Ñ á ç ’ «»"
    doc = load_doc(demo_json).model_copy(update={"title": text})
    out = tmp_path / "karaoke.json"

    dump_doc(doc, out)

    raw = out.read_text(encoding="utf-8")
    assert text in raw
    assert "\\u00" not in raw
    assert load_doc(out) == doc


def test_newer_minor_with_extra_field_is_accepted(demo_data: dict[str, Any]) -> None:
    demo_data["schema_version"] = "1.3.0"
    demo_data["foo"] = {"bar": 1}

    doc = KaraokeDoc.model_validate(demo_data)

    assert validate_doc(doc) == []


def test_major_2_is_rejected(demo_data: dict[str, Any]) -> None:
    demo_data["schema_version"] = "2.0.0"

    with pytest.raises(ValidationError):
        KaraokeDoc.model_validate(demo_data)


@pytest.mark.parametrize("token", ["Infinity", "NaN", "-Infinity"])
def test_non_finite_numbers_are_rejected(demo_json: Path, token: str) -> None:
    raw = demo_json.read_text(encoding="utf-8").replace('"duration": 32.0', f'"duration": {token}')

    with pytest.raises(ValidationError):
        KaraokeDoc.model_validate_json(raw)


def test_unknown_fields_survive_a_round_trip(demo_data: dict[str, Any], tmp_path: Path) -> None:
    # A newer minor version may add fields; an older reader must not drop them on save.
    demo_data["schema_version"] = "1.3.0"
    demo_data["mood"] = "morriña"
    demo_data["lines"][0]["words"][0]["emphasis"] = True
    out = tmp_path / "karaoke.json"

    dump_doc(KaraokeDoc.model_validate(demo_data), out)

    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["mood"] == "morriña"
    assert saved["lines"][0]["words"][0]["emphasis"] is True


def test_a_1_0_document_reads_with_lead_lines(demo_data: dict[str, Any]) -> None:
    demo_data["schema_version"] = "1.0.0"
    for line in demo_data["lines"]:
        line.pop("role", None)

    doc = KaraokeDoc.model_validate(demo_data)

    assert {line.role for line in doc.lines} == {"lead"}


def test_backing_line_may_overlap_its_lead_line(demo_data: dict[str, Any]) -> None:
    from karaoke_contracts import validate_doc

    lead = demo_data["lines"][0]
    word = {"text": "(ola)", "start": lead["start"] + 0.1, "end": lead["start"] + 0.5}
    backing = {"id": "b1", "start": word["start"], "end": word["end"], "singer": lead["singer"],
               "role": "backing", "words": [word]}  # fmt: skip
    demo_data["lines"].insert(1, backing)

    doc = KaraokeDoc.model_validate(demo_data)

    assert doc.lines[1].role == "backing"
    assert validate_doc(doc) == []


def test_unknown_role_is_rejected(demo_data: dict[str, Any]) -> None:
    demo_data["lines"][0]["role"] = "chorus"

    with pytest.raises(ValidationError):
        KaraokeDoc.model_validate(demo_data)


def test_new_documents_are_version_1_1() -> None:
    from karaoke_contracts import SCHEMA_VERSION

    assert SCHEMA_VERSION == "1.1.0"
