import json

from karaoke_engine.subtitles.conformance import CASES_DIR, cases


def test_conformance_files_are_current() -> None:
    expected = cases()
    on_disk = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(CASES_DIR.glob("*.json"))
    }

    assert sorted(on_disk) == sorted(expected), (
        "run: python -m karaoke_engine.subtitles.conformance --write"
    )
    for case_id, case in expected.items():
        assert on_disk[case_id] == json.loads(json.dumps(case)), case_id
