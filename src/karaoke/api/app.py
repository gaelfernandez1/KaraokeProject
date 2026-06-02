import logging
import os
import pathlib
import uuid

from flask import Flask, g
from pydantic import ValidationError

from karaoke.api.errors import register_error_handlers
from karaoke.config import Settings
from karaoke.infra.db import init_db
from karaoke.infra.gpu_utils import print_system_summary
from karaoke.logging_config import _request_id_var, configure_logging
from karaoke.security import setup_security

_ROOT = pathlib.Path(__file__).parents[3]

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    try:
        settings = Settings()
    except ValidationError as exc:
        raise RuntimeError(f"Configuration error: {exc}") from exc

    if settings.storage_backend == "r2":
        missing = [
            f
            for f in ["r2_account_id", "r2_bucket", "r2_access_key_id", "r2_secret_access_key"]
            if not getattr(settings, f)
        ]
        if missing:
            raise RuntimeError(f"storage_backend=r2 requires: {', '.join(missing)}")

    configure_logging(settings.log_level)

    flask_app = Flask(
        __name__,
        template_folder=str(_ROOT / "templates"),
        static_folder=str(_ROOT / "static"),
    )
    flask_app.config["MAX_CONTENT_LENGTH"] = settings.max_file_size_mb * 1024 * 1024
    flask_app.config["APP_SETTINGS"] = settings

    from karaoke.api.generation import bp as generation_bp
    from karaoke.api.health import bp as health_bp
    from karaoke.api.library import bp as library_bp
    from karaoke.api.player import bp as player_bp
    from karaoke.api.tasks import bp as tasks_bp

    flask_app.register_blueprint(generation_bp)
    flask_app.register_blueprint(health_bp)
    flask_app.register_blueprint(library_bp)
    flask_app.register_blueprint(player_bp)
    flask_app.register_blueprint(tasks_bp)

    register_error_handlers(flask_app)

    @flask_app.before_request
    def inject_request_id():
        request_id = str(uuid.uuid4())
        g.request_id = request_id
        _request_id_var.set(request_id)

    @flask_app.after_request
    def attach_request_id(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        return response

    return flask_app


print_system_summary()
init_db()
os.makedirs("input", exist_ok=True)
os.makedirs("output", exist_ok=True)

app = create_app()
_settings: Settings = app.config["APP_SETTINGS"]
limiter = setup_security(app)

if __name__ == "__main__":
    app.run(
        debug=_settings.flask_debug,
        host="0.0.0.0",
        port=5000,
    )
