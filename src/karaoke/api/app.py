import os
import pathlib
from flask import Flask

from karaoke.infra.gpu_utils import print_system_summary
from karaoke.infra.database import init_database
from karaoke.security import setup_security

_ROOT = pathlib.Path(__file__).parents[3]


def create_app() -> Flask:
    flask_app = Flask(
        __name__,
        template_folder=str(_ROOT / "templates"),
        static_folder=str(_ROOT / "static"),
    )

    from karaoke.api.generation import bp as generation_bp
    from karaoke.api.library import bp as library_bp
    from karaoke.api.player import bp as player_bp
    from karaoke.api.tasks import bp as tasks_bp

    flask_app.register_blueprint(generation_bp)
    flask_app.register_blueprint(library_bp)
    flask_app.register_blueprint(player_bp)
    flask_app.register_blueprint(tasks_bp)

    return flask_app


print_system_summary()
init_database()
os.makedirs("input", exist_ok=True)
os.makedirs("output", exist_ok=True)

app = create_app()
limiter = setup_security(app)

if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
        host="0.0.0.0",
        port=5000,
    )
