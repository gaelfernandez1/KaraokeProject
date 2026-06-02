import os

from flask import Blueprint, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from karaoke.infra.task_ownership import record_task_owner
from karaoke.workers.celery_tasks import (
    process_automatic_karaoke,
    process_instrumental_only,
    process_manual_lyrics_karaoke,
)

bp = Blueprint("generation", __name__)

DIRECTORIO_ENTRADA = "input"
DIRECTORIO_SAIDA = "output"
EXTENSIONES_PERMITIDAS = {"mp4"}
EXTENSIONES_AUDIO_PERMITIDAS = {"wav", "mp3"}
EXTENSIONES_INSTRUMENTAL_PERMITIDAS = {"mp4", "mp3"}


# PAra comprobar si o archivo ten unha extension permitida
def archivo_permitido(nome_arquivo: str) -> bool:
    return "." in nome_arquivo and nome_arquivo.rsplit(".", 1)[1].lower() in EXTENSIONES_PERMITIDAS


def archivo_instrumental_permitido(nome_arquivo: str) -> bool:
    return (
        "." in nome_arquivo
        and nome_arquivo.rsplit(".", 1)[1].lower() in EXTENSIONES_INSTRUMENTAL_PERMITIDAS
    )


# Uploads are saved here and read by the worker via the shared input volume.
# YouTube links are not downloaded here anymore: the web image carries no ffmpeg,
# so the worker downloads + merges them from source_url when the task runs.
def _save_upload(arquivo_subido) -> str:
    nome_ficheiro = secure_filename(arquivo_subido.filename)
    ruta_video = os.path.join(DIRECTORIO_ENTRADA, nome_ficheiro)
    arquivo_subido.save(ruta_video)
    return ruta_video


@bp.route("/", methods=["GET"])
def inicio():
    return render_template("index.html")


# asincronia
@bp.route("/generate", methods=["POST"])
@login_required
def xerar_karaoke():
    arquivo_subido = request.files.get("video_file")
    if arquivo_subido and arquivo_subido.filename and archivo_permitido(arquivo_subido.filename):
        ruta_video = _save_upload(arquivo_subido)
        source_type = "upload"
        source_url = None
    else:
        url_youtube = request.form.get("youtube_url", "").strip()
        if not url_youtube:
            return "Debes mandar ou un mp4 ou un link de Youtube", 400
        ruta_video = ""  # the worker downloads from source_url
        source_type = "youtube"
        source_url = url_youtube

    enable_diarization = request.form.get("enable_diarization") == "true"
    hf_token = request.form.get("hf_token", "").strip() if enable_diarization else None
    whisper_model = request.form.get(
        "whisper_model", "small"
    ).strip()  # para poder elixir modelo de whisper na interface

    task = process_automatic_karaoke.delay(
        ruta_video,
        enable_diarization,
        hf_token,
        whisper_model,
        source_type,
        source_url,
        True,
        current_user.id,
    )

    record_task_owner(task.id, current_user.id)
    session["current_task_id"] = task.id
    session["task_type"] = "automatic"

    return redirect(url_for("tasks.mostrar_progreso", task_id=task.id))


@bp.route("/manual_lyrics_form", methods=["GET"])
def formulario_letras_manuales():
    return render_template("manual_lyrics_form.html")


@bp.route("/process_manual_lyrics", methods=["POST"])
@login_required
def procesar_letras_manuales():
    arquivo_subido = request.files.get("video_file")
    if arquivo_subido and arquivo_subido.filename and archivo_permitido(arquivo_subido.filename):
        ruta_video = _save_upload(arquivo_subido)
        source_type = "upload"
        source_url = None
    else:
        url_youtube = request.form.get("youtube_url", "").strip()
        if not url_youtube:
            return "Tes que subir un mp4 ou un link de Youtube", 400
        ruta_video = ""  # the worker downloads from source_url
        source_type = "youtube"
        source_url = url_youtube

    letra_manual = request.form.get("manual_lyrics", "").strip()
    if not letra_manual:
        return "Falta o texto da letra.", 400

    enable_diarization = request.form.get("enable_diarization") == "true"
    hf_token = request.form.get("hf_token", "").strip() if enable_diarization else None
    whisper_model = request.form.get(
        "whisper_model", "small"
    ).strip()  # o mesmo, para elegir modelo de whisper

    task = process_manual_lyrics_karaoke.delay(
        ruta_video,
        letra_manual,
        None,
        enable_diarization,
        hf_token,
        whisper_model,
        source_type,
        source_url,
        True,
        current_user.id,
    )

    record_task_owner(task.id, current_user.id)
    session["current_task_id"] = task.id
    session["task_type"] = "manual_lyrics"

    return redirect(url_for("tasks.mostrar_progreso", task_id=task.id))


@bp.route("/generate_instrumental", methods=["POST"])
@login_required
def xerar_instrumental():
    arquivo_subido = request.files.get("video_file")
    if (
        arquivo_subido
        and arquivo_subido.filename
        and archivo_instrumental_permitido(arquivo_subido.filename)
    ):
        ruta_video = _save_upload(arquivo_subido)
        source_type = "upload"
        source_url = None
    else:
        url_youtube = request.form.get("youtube_url", "").strip()
        if not url_youtube:
            return "Tes que mandar un mp4/mp3 ou un link de YouTube", 400
        ruta_video = ""  # the worker downloads from source_url
        source_type = "youtube"
        source_url = url_youtube

    task = process_instrumental_only.delay(
        ruta_video, source_type, source_url, True, current_user.id
    )

    record_task_owner(task.id, current_user.id)
    session["current_task_id"] = task.id
    session["task_type"] = "instrumental"

    return redirect(url_for("tasks.mostrar_progreso", task_id=task.id))
