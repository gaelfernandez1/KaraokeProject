import json
from pathlib import Path
from typing import Any

import pytest

from karaoke_contracts import KaraokeDoc, load_doc
from karaoke_server.hook import hook_of

REPO = Path(__file__).resolve().parents[3]
CASES = json.loads((REPO / "fixtures" / "hook-cases.json").read_text(encoding="utf-8"))


def doc_with(lines: list[list[str]]) -> KaraokeDoc:
    def line(i: int, spec: list[str]) -> dict[str, Any]:
        text, role = spec[0], (spec[1] if len(spec) > 1 else "lead")
        words = [{"text": w, "start": i, "end": i + 0.5} for w in text.split(" ")]
        return {"id": f"l{i}", "start": i, "end": i + 0.5, "role": role, "words": words}

    return KaraokeDoc.model_validate(
        {
            "id": "x",
            "title": "x",
            "language": "gl",
            "duration": 100,
            "audio": {"instrumental": "i.m4a"},
            "lines": [line(i, spec) for i, spec in enumerate(lines)],
            "provenance": {"lyrics_source": "user", "engine_version": "t"},
        }
    )


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda c: c["name"])
def test_hook_cases_match_typescript(case: dict[str, Any]) -> None:
    assert hook_of(doc_with(case["lines"])) == case["expected"]


@pytest.mark.parametrize("case", CASES["packages"], ids=lambda c: c["package"])
def test_hook_of_example_packages(case: dict[str, Any]) -> None:
    doc = load_doc(REPO / "fixtures" / "packages" / case["package"] / "karaoke.json")
    assert hook_of(doc) == case["expected"]


def test_every_example_package_has_a_case() -> None:
    names = {p.name for p in (REPO / "fixtures" / "packages").iterdir()}
    assert {c["package"] for c in CASES["packages"]} == names
