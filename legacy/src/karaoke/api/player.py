import logging
import os

from flask import Blueprint, abort, current_app, redirect, render_template, send_file
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

bp = Blueprint("player", __name__)

DIRECTORIO_SAIDA = "output"


def _require_owns_file(filename: str) -> None:
    """403 unless the current user owns the song that any of whose artifacts is filename."""
    from karaoke.infra.db import session_scope  # noqa: PLC0415
    from karaoke.infra.db.repository import get_song_owning_file  # noqa: PLC0415

    with session_scope() as session:
        song = get_song_owning_file(session, filename)
        if song is None or song.user_id != current_user.id:
            abort(403)


def _signed_url_for(settings, filename: str) -> str | None:
    """Signed URL for any artifact of the song that owns filename, or None.

    Every output of a song is stored under the same karaoke/{task_id}/ prefix, so
    we locate the song by the requested filename and rebuild the key from its
    stored storage_key. Returns None when the song or its storage_key is missing.
    """
    from karaoke.infra.db import session_scope  # noqa: PLC0415
    from karaoke.infra.db.repository import get_song_owning_file  # noqa: PLC0415
    from karaoke.infra.storage import derive_key, get_storage  # noqa: PLC0415

    with session_scope() as session:
        song = get_song_owning_file(session, filename)
        if song is None or song.storage_key is None:
            return None
        key = derive_key(song.storage_key, filename)
    return get_storage(settings).get_signed_url(key)


def _local_path(filename: str) -> str | None:
    """Sanitised absolute path inside the output dir, or None if it escapes/missing."""
    safe_name = secure_filename(filename)
    if not safe_name:
        return None
    abs_dir = os.path.abspath(DIRECTORIO_SAIDA)
    ruta = os.path.abspath(os.path.join(DIRECTORIO_SAIDA, safe_name))
    if os.path.commonpath([ruta, abs_dir]) != abs_dir:
        return None
    if not os.path.exists(ruta):
        return None
    return ruta


@bp.route("/player/<filename>")
@login_required
def reproductor_karaoke(filename):
    _require_owns_file(filename)
    settings = current_app.config["APP_SETTINGS"]
    if settings.storage_backend == "r2":
        if _signed_url_for(settings, filename) is None:
            return "Arquivo non encontrado", 404
    elif not os.path.exists(os.path.join(DIRECTORIO_SAIDA, filename)):
        return "Arquivo non encontrado", 404

    if filename.startswith("karaoke_manual_"):
        nome_base = filename.replace("karaoke_manual_", "").replace(".mp4", "")
    elif filename.startswith("karaoke_"):
        nome_base = filename.replace("karaoke_", "").replace(".mp4", "")
    else:
        nome_base = filename.replace(".mp4", "")

    return render_template("player.html", video_filename=filename, base_name=nome_base)


@bp.route("/serve_video/<filename>")
@login_required
def servir_video(filename):
    _require_owns_file(filename)
    settings = current_app.config["APP_SETTINGS"]
    if settings.storage_backend == "r2":
        url = _signed_url_for(settings, filename)
        if url is None:
            abort(404)
        return redirect(url, 302)

    ruta_archivo = _local_path(filename)
    if ruta_archivo is None:
        return "Arquivo non encontrado", 404
    return send_file(ruta_archivo, mimetype="video/mp4")


@bp.route("/serve_audio/<filename>")
@login_required
def servir_audio(filename):
    _require_owns_file(filename)
    settings = current_app.config["APP_SETTINGS"]
    if settings.storage_backend == "r2":
        url = _signed_url_for(settings, filename)
        if url is None:
            abort(404)
        return redirect(url, 302)

    ruta_archivo = _local_path(filename)
    if ruta_archivo is None:
        return "Arquivo non encontrado", 404
    return send_file(ruta_archivo, mimetype="audio/wav")


@bp.route("/download/<filename>")
@login_required
def descargar_archivo(filename):
    _require_owns_file(filename)
    settings = current_app.config["APP_SETTINGS"]
    if settings.storage_backend == "r2":
        url = _signed_url_for(settings, filename)
        if url is None:
            abort(404)
        return redirect(url, 302)

    ruta_arquivo = _local_path(filename)
    if ruta_arquivo is None:
        return "Arquivo non encontrado", 404

    safe_name = secure_filename(filename)
    tamano_ficheiro = os.path.getsize(ruta_arquivo)

    try:
        response = send_file(ruta_arquivo, as_attachment=True, download_name=safe_name)

        if filename.endswith(".mp4"):
            response.headers["Content-Type"] = "video/mp4"
        elif filename.endswith(".wav"):
            response.headers["Content-Type"] = "audio/wav"

        response.headers["Content-Length"] = str(tamano_ficheiro)
        return response
    except Exception:
        logger.exception(f"Erro enviando archivo {safe_name}")
        abort(500)
