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


def test_validate_missing_file_fails_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["validate", str(tmp_path / "nope.json")]) == 1
    assert "nope.json" in capsys.readouterr().out


def test_demo_without_document_fails_cleanly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["demo", str(tmp_path)]) == 1
    assert "karaoke.json" in capsys.readouterr().err


def test_demo_refuses_non_wav_media(bare_package: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc_path = bare_package / "karaoke.json"
    doc_path.write_text(
        doc_path.read_text(encoding="utf-8").replace('"vocals.wav"', '"vocals.m4a"'),
        encoding="utf-8",
    )

    assert main(["demo", str(bare_package)]) == 1
    assert ".wav" in capsys.readouterr().err


def test_demo_never_writes_outside_the_package(bare_package: Path) -> None:
    outside = bare_package.parent / "precious.wav"
    outside.write_bytes(b"keep me")
    (bare_package / "vocals.wav").symlink_to(outside)

    assert main(["demo", str(bare_package)]) == 1
    assert outside.read_bytes() == b"keep me"
