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
