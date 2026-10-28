import logging
import os

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from karaoke.infra.db import session_scope
from karaoke.infra.db.repository import (
    delete_song,
    get_all_songs,
    get_database_stats,
    get_song_by_id,
    get_songs_by_search,
    update_last_played,
)
from karaoke.infra.metadata_utils import format_duration, format_file_size

logger = logging.getLogger(__name__)

bp = Blueprint("library", __name__)

DIRECTORIO_SAIDA = "output"


def _delete_song_artifacts(settings, song) -> None:
    """Remove a song's files from the active backend (R2 objects or local files)."""
    filenames = [
        song.karaoke_filename,
        song.video_only_filename,
        song.vocal_filename,
        song.instrumental_filename,
    ]
    if settings.storage_backend == "r2":
        if not song.storage_key:
            return
        from karaoke.infra.storage import derive_key, get_storage

        storage = get_storage(settings)
        for name in filenames:
            if not name:
                continue
            try:
                storage.delete(derive_key(song.storage_key, name))
            except Exception:
                logger.warning(f"Erro borrando do storage: {name}")
        return

    for name in filenames:
        if not name:
            continue
        path = os.path.join(DIRECTORIO_SAIDA, name)
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Arquivo borrado: {path}")
        except Exception:
            logger.warning(f"Erro borrando arquivo {path}")


@bp.route("/library")
@login_required
def biblioteca_cancions():
    try:
        with session_scope() as session:
            songs = [s.to_dict() for s in get_all_songs(session, user_id=current_user.id)]
            stats = get_database_stats(session, user_id=current_user.id)

        for song in songs:
            song["formatted_file_size"] = format_file_size(song["file_size"] or 0)
            song["formatted_duration"] = format_duration(song["duration"])

        return render_template("library.html", songs=songs, stats=stats)
    except Exception:
        logger.exception("erro cargando biblioteca")
        abort(500)


@bp.route("/library/search")
@login_required
def buscar_cancions():
    query = request.args.get("q", "").strip()
    if not query:
        return redirect(url_for("library.biblioteca_cancions"))

    try:
        with session_scope() as session:
            songs = [
                s.to_dict() for s in get_songs_by_search(session, query, user_id=current_user.id)
            ]

        for song in songs:
            song["formatted_file_size"] = format_file_size(song["file_size"] or 0)
            song["formatted_duration"] = format_duration(song["duration"])

        return render_template("library.html", songs=songs, search_query=query)
    except Exception:
        logger.exception("Error buscando cancións")
        abort(500)


@bp.route("/library/play/<int:song_id>")
@login_required
def reproducir_dende_biblioteca(song_id):
    settings = current_app.config["APP_SETTINGS"]
    try:
        with session_scope() as session:
            song = get_song_by_id(session, song_id)
            if not song:
                return "Canción non encontrada", 404
            if song.user_id != current_user.id:
                abort(403)

            karaoke_filename = song.karaoke_filename
            if settings.storage_backend == "r2":
                available = song.storage_key is not None
            else:
                available = os.path.exists(os.path.join(DIRECTORIO_SAIDA, karaoke_filename))
            if not available:
                return "Arquivo de video non encontrado", 404

            update_last_played(session, song_id)

        return redirect(url_for("player.reproductor_karaoke", filename=karaoke_filename))

    except Exception:
        logger.exception(f"Error reproducindo canción {song_id}")
        abort(500)


@bp.route("/library/delete/<int:song_id>", methods=["POST"])
@login_required
def borrar_cancion_biblioteca(song_id):
    settings = current_app.config["APP_SETTINGS"]
    try:
        with session_scope() as session:
            song = get_song_by_id(session, song_id)
            if not song:
                return "Canción non encontrada na bib", 404
            if song.user_id != current_user.id:
                abort(403)

            title = song.title
            _delete_song_artifacts(settings, song)

            deleted = delete_song(session, song_id)

        if deleted:
            logger.info(f"Canción {title} borrada da biblioteca (ID: {song_id})")
            return redirect(url_for("library.biblioteca_cancions"))
        else:
            return "error borrando canción", 500

    except Exception:
        logger.exception(f"Erro borrando canción {song_id}")
        abort(500)
