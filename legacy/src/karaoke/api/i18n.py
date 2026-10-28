import pathlib

from flask import Blueprint, Flask, redirect, request, session
from flask_babel import Babel, get_locale

# UI languages offered to the user. Galician is primary; Spanish and English
# are the fallbacks documented in CLAUDE.md.
LANGUAGES = ["gl", "es", "en"]
_DEFAULT_LOCALE = "gl"

# Translations live at the repo root, next to templates/ and static/, not under
# the api package (which is where Flask.root_path points by default).
_ROOT = pathlib.Path(__file__).parents[3]

bp = Blueprint("i18n", __name__)


def _select_locale() -> str:
    lang = session.get("lang")
    if lang in LANGUAGES:
        return lang
    return request.accept_languages.best_match(LANGUAGES) or _DEFAULT_LOCALE


def configure_babel(app: Flask) -> Babel:
    app.config["BABEL_DEFAULT_LOCALE"] = _DEFAULT_LOCALE
    app.config.setdefault("BABEL_TRANSLATION_DIRECTORIES", str(_ROOT / "translations"))

    # Flask-Babel 3.0+ takes locale_selector as a kwarg; the 2.x
    # @babel.localeselector decorator no longer exists.
    babel = Babel(app, default_locale=_DEFAULT_LOCALE, locale_selector=_select_locale)

    @app.context_processor
    def _inject_i18n():
        return {"current_locale": str(get_locale() or _DEFAULT_LOCALE), "languages": LANGUAGES}

    return babel


@bp.route("/set-language/<lang>")
def set_language(lang: str):
    if lang in LANGUAGES:
        session["lang"] = lang
    return redirect(request.referrer or "/")
