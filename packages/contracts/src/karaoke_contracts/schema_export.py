"""Writes the JSON Schemas in schemas/ from the pydantic models (run via `make contracts`)."""

import json
import sys
from pathlib import Path

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema

from karaoke_contracts.doc import KaraokeDoc
from karaoke_contracts.theme import Theme

SCHEMA_BASE_ID = "https://github.com/gaelfernandez1/KaraokeProject/schemas/"
MODELS: dict[str, type[BaseModel]] = {"karaoke": KaraokeDoc, "theme": Theme}


class _ModelTitlesOnly(GenerateJsonSchema):
    """Keeps titles on models but not on fields, so TS generators emit clean interfaces."""

    def field_title_should_be_set(self, schema: object) -> bool:
        return False


def export_schemas(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, model in MODELS.items():
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{SCHEMA_BASE_ID}{name}.schema.json",
            **model.model_json_schema(mode="serialization", schema_generator=_ModelTitlesOnly),
        }
        path = out_dir / f"{name}.schema.json"
        path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("schemas")
    for path in export_schemas(out_dir):
        print(path)


if __name__ == "__main__":
    main()
