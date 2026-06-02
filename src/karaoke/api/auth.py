import logging

import resend
from flask import Blueprint, current_app, redirect, render_template, request, url_for
from flask_login import login_user, logout_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from karaoke.infra.db import session_scope
from karaoke.infra.db.repository import create_user, get_user_by_email

logger = logging.getLogger(__name__)

bp = Blueprint("auth", __name__, url_prefix="/auth")

_SALT = "magic-login"
_MAX_AGE_SECONDS = 15 * 60


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.secret_key, salt=_SALT)


def _send_magic_link(email: str, link: str) -> None:
    settings = current_app.config["APP_SETTINGS"]
    if not settings.resend_api_key:
        logger.warning("resend_api_key not configured; skipping magic-link email")
        return
    resend.api_key = settings.resend_api_key
    resend.Emails.send(
        {
            "from": settings.resend_from_email,
            "to": [email],
            "subject": "O teu acceso a KaraokeIA",
            "html": (
                f'<p><a href="{link}">Entra en KaraokeIA</a></p>'
                "<p>O enlace caduca en 15 minutos.</p>"
            ),
        }
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    if email:
        settings = current_app.config["APP_SETTINGS"]
        token = _serializer().dumps(email)
        link = f"{settings.app_base_url.rstrip('/')}/auth/verify/{token}"
        try:
            _send_magic_link(email, link)
        except Exception:
            # Never surface send failures (or whether the address exists) to the client.
            logger.exception("Failed to send magic-link email")
    # Generic confirmation regardless of whether the email exists or the send worked.
    return render_template("login.html", sent=True)


@bp.route("/verify/<token>")
def verify(token: str):
    try:
        email = _serializer().loads(token, max_age=_MAX_AGE_SECONDS)
    except (SignatureExpired, BadSignature):
        logger.info("Rejected an invalid or expired magic-link token")
        return render_template("login.html", error=True)

    with session_scope() as session:
        user = get_user_by_email(session, email) or create_user(session, email)
        login_user(user, remember=True)
        user_id = user.id

    logger.info("Magic link verified", extra={"user_id": user_id})
    return redirect(url_for("generation.inicio"))


@bp.route("/logout")
def logout():
    logout_user()
    return redirect("/")
