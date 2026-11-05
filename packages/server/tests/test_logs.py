import json
import logging
from pathlib import Path

from karaoke_server.logs import setup_logging


def test_log_lines_are_json(tmp_path: Path) -> None:
    setup_logging(tmp_path)
    logging.getLogger("karaoke_server.test").info("job %s started", "j1", extra={"job": "j1"})
    for handler in logging.getLogger().handlers:
        handler.flush()
    line = (tmp_path / "server.log").read_text(encoding="utf-8").strip().splitlines()[-1]
    record = json.loads(line)
    assert record["message"] == "job j1 started"
    assert record["level"] == "INFO"
    assert record["logger"] == "karaoke_server.test"
    assert record["job"] == "j1"
    assert "time" in record
