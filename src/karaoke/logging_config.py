import logging
import sys
import contextvars
from pythonjsonlogger import jsonlogger

# Context vars for structured log fields injected per-task and per-request
_task_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("task_id", default="")
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


class _JsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)
        # Rename to canonical field names
        log_record["timestamp"] = log_record.pop("asctime", None) or record.created
        log_record["level"] = log_record.pop("levelname", record.levelname)
        log_record["logger_name"] = log_record.pop("name", record.name)
        # Inject context vars; caller-supplied extra= takes precedence via setdefault
        task_id = _task_id_var.get("")
        if task_id:
            log_record.setdefault("task_id", task_id)
        request_id = _request_id_var.get("")
        if request_id:
            log_record.setdefault("request_id", request_id)


def configure_logging(level: str = "INFO") -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)
