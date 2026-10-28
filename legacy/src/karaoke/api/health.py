import logging

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from karaoke.infra.db import get_engine

logger = logging.getLogger(__name__)

bp = Blueprint("health", __name__)


@bp.route("/health")
def health():
    checks = {"redis": _check_redis(), "database": _check_database()}
    healthy = all(checks.values())
    payload = {"status": "ok" if healthy else "degraded", "checks": checks}
    return jsonify(payload), 200 if healthy else 503


def _check_redis() -> bool:
    import redis  # noqa: PLC0415

    try:
        settings = current_app.config["APP_SETTINGS"]
        client = redis.from_url(settings.redis_url, socket_connect_timeout=2)
        client.ping()
        return True
    except Exception:
        logger.warning("health check: redis unreachable", exc_info=True)
        return False


def _check_database() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.warning("health check: database unreachable", exc_info=True)
        return False
