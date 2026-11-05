"""Logging: one JSON object per line in logs/server.log (rotated), readable lines on the console."""

import json
import logging
import logging.handlers
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Attributes every LogRecord has; anything else came in through `extra=` and is kept.
_STANDARD = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "taskName"}
# Names of the handlers set up here, so setting up again replaces them instead of adding more.
_OURS = ("karaoke-file", "karaoke-console")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD:
                entry[key] = value
        if record.exc_info:
            entry["error"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def setup_logging(logs_dir: Path, verbose: bool = False) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    for handler in list(root.handlers):
        if handler.name in _OURS:
            root.removeHandler(handler)
            handler.close()
    to_file = logging.handlers.RotatingFileHandler(
        logs_dir / "server.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    to_file.setFormatter(JsonFormatter())
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    to_file.name, console.name = _OURS
    root.addHandler(to_file)
    root.addHandler(console)
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    # It tells about every part of every upload.
    logging.getLogger("python_multipart").setLevel(logging.WARNING)
