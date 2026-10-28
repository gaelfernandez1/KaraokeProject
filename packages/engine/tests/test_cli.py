import json
from pathlib import Path

import pytest

from karaoke_engine.cli import main


def test_demo_then_validate_succeeds(
    bare_package: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["demo", str(bare_package)]) == 0
    assert (bare_package / "vocals.wav").is_file()

    assert main(["validate", str(bare_package)]) == 0
    assert "OK" in capsys.readouterr().out


def test_validate_reports_issues_and_fails(
    bare_package: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    doc_path = bare_package / "karaoke.json"
    data = json.loads(doc_path.read_text(encoding="utf-8"))
    data["lines"][0]["words"][3]["end"] = 9.0
    doc_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    assert main(["validate", str(doc_path)]) == 1
    assert "lines[0].words[3]" in capsys.readouterr().out


def test_validate_single_json_skips_media_checks(bare_package: Path) -> None:
    assert main(["validate", str(bare_package / "karaoke.json")]) == 0
