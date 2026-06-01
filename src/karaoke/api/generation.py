import logging
import os

import yt_dlp
from flask import Blueprint, abort, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from karaoke.workers.celery_tasks import (
    process_automatic_karaoke,
    process_instrumental_only,
    process_manual_lyrics_karaoke,
)

logger = logging.getLogger(__name__)

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


def descargar_video_youtube(url: str, directorio_saida: str = DIRECTORIO_ENTRADA) -> str:
    """Funcion para descargar un video de YT e devolve a ruta do mp4 descargado"""

    # YouTube serves modern video/audio as separate DASH streams; a single
    # progressive mp4 rarely exists above 360p. So pick the best video+audio
    # under 1080p and let yt-dlp merge them, remuxing to mp4 so the rest of the
    # pipeline (which assumes a .mp4 path) keeps working.
    opcions_ydl = {
        "outtmpl": os.path.join(directorio_saida, "%(title)s.%(ext)s"),
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "extract_flat": False,
        "concurrent_fragment_downloads": 1,
    }
    with yt_dlp.YoutubeDL(opcions_ydl) as ydl:
        info = ydl.extract_info(url, download=True)
        # After a merge/remux prepare_filename returns the pre-merge container,
        # so prefer the real path yt-dlp records in requested_downloads.
        downloads = info.get("requested_downloads")
        if downloads:
            return downloads[0]["filepath"]
        return ydl.prepare_filename(info)


@bp.route("/", methods=["GET"])
def inicio():
    return render_template("index.html")


# asincronia
@bp.route("/generate", methods=["POST"])
def xerar_karaoke():
    ruta_video = None
    arquivo_subido = request.files.get("video_file")
    if arquivo_subido and arquivo_subido.filename and archivo_permitido(arquivo_subido.filename):
        nome_ficheiro = secure_filename(arquivo_subido.filename)
        ruta_video = os.path.join(DIRECTORIO_ENTRADA, nome_ficheiro)
        arquivo_subido.save(ruta_video)
    else:
        url_youtube = request.form.get("youtube_url", "").strip()
        if not url_youtube:
            return "Debes mandar ou un mp4 ou un link de Youtube", 400
        try:
            ruta_video = descargar_video_youtube(url_youtube)
        except Exception:
            logger.exception("Error descargando vídeo de YouTube")
            abort(500)

    enable_diarization = request.form.get("enable_diarization") == "true"
    hf_token = request.form.get("hf_token", "").strip() if enable_diarization else None
    whisper_model = request.form.get(
        "whisper_model", "small"
    ).strip()  # para poder elixir modelo de whisper na interface

    source_type = "upload" if arquivo_subido else "youtube"
    source_url = url_youtube if not arquivo_subido else None

    task = process_automatic_karaoke.delay(
        ruta_video, enable_diarization, hf_token, whisper_model, source_type, source_url, True
    )

    session["current_task_id"] = task.id
    session["task_type"] = "automatic"

    return redirect(url_for("tasks.mostrar_progreso", task_id=task.id))


@bp.route("/manual_lyrics_form", methods=["GET"])
def formulario_letras_manuales():
    return render_template("manual_lyrics_form.html")


@bp.route("/process_manual_lyrics", methods=["POST"])
def procesar_letras_manuales():
    ruta_video = None
    arquivo_subido = request.files.get("video_file")
    if arquivo_subido and arquivo_subido.filename and archivo_permitido(arquivo_subido.filename):
        nome_ficheiro = secure_filename(arquivo_subido.filename)
        ruta_video = os.path.join(DIRECTORIO_ENTRADA, nome_ficheiro)
        arquivo_subido.save(ruta_video)
    else:
        url_youtube = request.form.get("youtube_url", "").strip()
        if not url_youtube:
            return "Tes que subir un mp4 ou un link de Youtube", 400
        try:
            ruta_video = descargar_video_youtube(url_youtube)
        except Exception:
            logger.exception("Erro descargando vídeo de YouTube para letras manuais")
            abort(500)

    letra_manual = request.form.get("manual_lyrics", "").strip()
    if not letra_manual:
        return "Falta o texto da letra.", 400

    enable_diarization = request.form.get("enable_diarization") == "true"
    hf_token = request.form.get("hf_token", "").strip() if enable_diarization else None
    whisper_model = request.form.get(
        "whisper_model", "small"
    ).strip()  # o mesmo, para elegir modelo de whisper

    source_type = "upload" if arquivo_subido else "youtube"
    source_url = url_youtube if not arquivo_subido else None

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
    )

    session["current_task_id"] = task.id
    session["task_type"] = "manual_lyrics"

    return redirect(url_for("tasks.mostrar_progreso", task_id=task.id))


@bp.route("/generate_instrumental", methods=["POST"])
def xerar_instrumental():
    ruta_video = None
    arquivo_subido = request.files.get("video_file")
    if (
        arquivo_subido
        and arquivo_subido.filename
        and archivo_instrumental_permitido(arquivo_subido.filename)
    ):
        nome_ficheiro = secure_filename(arquivo_subido.filename)
        ruta_video = os.path.join(DIRECTORIO_ENTRADA, nome_ficheiro)
        arquivo_subido.save(ruta_video)
    else:
        url_youtube = request.form.get("youtube_url", "").strip()
        if not url_youtube:
            return "Tes que mandar un mp4/mp3 ou un link de YouTube", 400
        try:
            ruta_video = descargar_video_youtube(url_youtube)
        except Exception:
            logger.exception("Erro descargando vídeo de YouTube para instrumental")
            abort(500)

    source_type = "upload" if arquivo_subido else "youtube"
    source_url = url_youtube if not arquivo_subido else None

    task = process_instrumental_only.delay(ruta_video, source_type, source_url, True)

    session["current_task_id"] = task.id
    session["task_type"] = "instrumental"

    return redirect(url_for("tasks.mostrar_progreso", task_id=task.id))
