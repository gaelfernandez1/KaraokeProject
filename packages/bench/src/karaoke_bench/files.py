"""Small file helpers shared by the bench."""

import os
from pathlib import Path


def write_text_atomic(path: Path, text: str) -> None:
    """Writes through a temporary file, so an interrupted run never leaves half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
