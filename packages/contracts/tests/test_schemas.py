import json
from pathlib import Path

from karaoke_contracts.schema_export import export_schemas

COMMITTED = Path(__file__).resolve().parents[3] / "schemas"


def test_committed_schemas_are_up_to_date(tmp_path: Path) -> None:
    written = export_schemas(tmp_path)

    assert sorted(p.name for p in written) == ["karaoke.schema.json", "theme.schema.json"]
    for path in written:
        assert path.read_bytes() == (COMMITTED / path.name).read_bytes(), (
            f"{path.name} is stale: run `make contracts`"
        )


def test_karaoke_schema_marks_defaulted_fields_required(tmp_path: Path) -> None:
    export_schemas(tmp_path)
    schema = json.loads((tmp_path / "karaoke.schema.json").read_text(encoding="utf-8"))

    assert {"schema_version", "singers", "lines", "edited"} <= set(schema["required"])
    assert schema["$id"].endswith("/schemas/karaoke.schema.json")
