from pathlib import Path
from typing import Any

import pytest

from karaoke_contracts import Issue, KaraokeDoc, validate_doc, validate_package


def issues_for(data: dict[str, Any]) -> list[Issue]:
    return validate_doc(KaraokeDoc.model_validate(data))


def test_word_outside_line_is_reported(demo_data: dict[str, Any]) -> None:
    line = demo_data["lines"][0]
    line["words"][-1]["end"] = line["end"] + 0.01

    issues = issues_for(demo_data)

    assert [i.path for i in issues] == ["lines[0].words[3]"]


def test_rounding_within_1ms_is_accepted(demo_data: dict[str, Any]) -> None:
    line = demo_data["lines"][0]
    line["words"][-1]["end"] = line["end"] + 0.0005

    assert issues_for(demo_data) == []


def test_reversed_span_is_reported(demo_data: dict[str, Any]) -> None:
    word = demo_data["lines"][1]["words"][1]
    word["start"], word["end"] = word["end"], word["start"]

    issues = issues_for(demo_data)

    assert "lines[1].words[1]" in [i.path for i in issues]


def test_overlapping_lines_are_allowed(demo_data: dict[str, Any]) -> None:
    duet_line = demo_data["lines"][2]
    duet_line["start"] = 11.0
    duet_line["words"][0]["start"] = 11.0

    assert issues_for(demo_data) == []


def test_lines_must_be_in_start_order(demo_data: dict[str, Any]) -> None:
    lines = demo_data["lines"]
    lines[0], lines[1] = lines[1], lines[0]

    issues = issues_for(demo_data)

    assert [i.path for i in issues] == ["lines[1]"]


def test_words_must_be_in_start_order(demo_data: dict[str, Any]) -> None:
    words = demo_data["lines"][1]["words"]
    words[1], words[2] = words[2], words[1]

    issues = issues_for(demo_data)

    assert "lines[1].words[2]" in [i.path for i in issues]


def test_parts_must_spell_the_word(demo_data: dict[str, Any]) -> None:
    ola = demo_data["lines"][0]["words"][0]
    ola["parts"][1]["text"] = "la"

    issues = issues_for(demo_data)

    assert [i.path for i in issues] == ["lines[0].words[0].parts"]


def test_part_outside_word_is_reported(demo_data: dict[str, Any]) -> None:
    ola = demo_data["lines"][0]["words"][0]
    ola["parts"][1]["end"] = ola["end"] + 0.2

    issues = issues_for(demo_data)

    assert [i.path for i in issues] == ["lines[0].words[0].parts[1]"]


def test_unknown_singer_is_reported(demo_data: dict[str, Any]) -> None:
    demo_data["lines"][3]["singer"] = "s9"

    issues = issues_for(demo_data)

    assert [i.path for i in issues] == ["lines[3].singer"]


def test_duplicate_ids_are_reported(demo_data: dict[str, Any]) -> None:
    demo_data["lines"][1]["id"] = demo_data["lines"][0]["id"]
    demo_data["singers"][1]["id"] = demo_data["singers"][0]["id"]

    paths = [i.path for i in issues_for(demo_data)]

    assert "lines[1].id" in paths
    assert "singers[1].id" in paths


def test_times_beyond_duration_are_reported(demo_data: dict[str, Any]) -> None:
    demo_data["duration"] = 20.0

    paths = [i.path for i in issues_for(demo_data)]

    assert "lines[3]" in paths
    assert all(p.startswith("lines[3]") for p in paths)


def test_demo_package_with_media_is_valid(demo_package: Path) -> None:
    assert validate_package(demo_package) == []


@pytest.mark.parametrize("ref", ["../escape.wav", "/etc/escape.wav", "sub/../../escape.wav"])
def test_media_path_outside_package_is_rejected(demo_package: Path, ref: str) -> None:
    (demo_package.parent / "escape.wav").write_bytes(b"")
    doc_path = demo_package / "karaoke.json"
    doc_path.write_text(
        doc_path.read_text(encoding="utf-8").replace('"instrumental.wav"', f'"{ref}"'),
        encoding="utf-8",
    )

    issues = validate_package(demo_package)

    assert [i.path for i in issues] == ["audio.instrumental"]


def test_missing_media_is_reported(demo_package: Path) -> None:
    (demo_package / "vocals.wav").unlink()

    issues = validate_package(demo_package)

    assert [i.path for i in issues] == ["audio.vocals"]


def test_missing_document_is_reported(tmp_path: Path) -> None:
    issues = validate_package(tmp_path)

    assert [i.path for i in issues] == ["karaoke.json"]


def test_schema_errors_are_reported_not_raised(demo_package: Path) -> None:
    doc_path = demo_package / "karaoke.json"
    doc_path.write_text(
        doc_path.read_text(encoding="utf-8").replace('"1.0.0"', '"2.0.0"'), encoding="utf-8"
    )

    issues = validate_package(demo_package)

    assert [i.path for i in issues] == ["schema_version"]
