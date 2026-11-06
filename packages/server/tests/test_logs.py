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


def test_access_log_hides_tokens_and_pairing_codes() -> None:
    from karaoke_server.logs import RedactSecrets

    record = logging.makeLogRecord(
        {
            "name": "uvicorn.access",
            "msg": '%s - "%s %s HTTP/%s" %d',
            "args": ("1.2.3.4:5", "GET", "/api/parties/ABCD/events?token=s3cret&x=1", "1.1", 200),
        }
    )
    assert RedactSecrets().filter(record)
    message = record.getMessage()
    assert "s3cret" not in message
    assert "token=…" in message
    assert "x=1" in message
    pairing = logging.makeLogRecord(
        {"name": "uvicorn.access", "msg": "%s", "args": ("/vincular?code=BCDFGHJK",)}
    )
    RedactSecrets().filter(pairing)
    assert "BCDFGHJK" not in pairing.getMessage()
