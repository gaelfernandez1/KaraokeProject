import logging
import os

from flask import Blueprint, abort, render_template, send_file
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

bp = Blueprint('player', __name__)

DIRECTORIO_SAIDA = "output"


@bp.route("/player/<filename>")
def reproductor_karaoke(filename):

    ruta_video = os.path.join(DIRECTORIO_SAIDA, filename)
    if not os.path.exists(ruta_video):
        return "Arquivo non encontrado", 404

    if filename.startswith("karaoke_manual_"):
        nome_base = filename.replace("karaoke_manual_", "").replace(".mp4", "")
    elif filename.startswith("karaoke_"):
        nome_base = filename.replace("karaoke_", "").replace(".mp4", "")
    else:
        nome_base = filename.replace(".mp4", "")

    return render_template("player.html",
                         video_filename=filename,
                         base_name=nome_base)


@bp.route("/serve_video/<filename>")
def servir_video(filename):
    safe_name = secure_filename(filename)
    if not safe_name:
        return "Arquivo non encontrado", 404
    abs_dir = os.path.abspath(DIRECTORIO_SAIDA)
    ruta_archivo = os.path.abspath(os.path.join(DIRECTORIO_SAIDA, safe_name))
    if os.path.commonpath([ruta_archivo, abs_dir]) != abs_dir:
        return "Arquivo non encontrado", 404
    if not os.path.exists(ruta_archivo):
        return "Arquivo non encontrado", 404
    return send_file(ruta_archivo, mimetype='video/mp4')


@bp.route("/serve_audio/<filename>")
def servir_audio(filename):
    safe_name = secure_filename(filename)
    if not safe_name:
        return "Arquivo non encontrado", 404
    abs_dir = os.path.abspath(DIRECTORIO_SAIDA)
    ruta_archivo = os.path.abspath(os.path.join(DIRECTORIO_SAIDA, safe_name))
    if os.path.commonpath([ruta_archivo, abs_dir]) != abs_dir:
        return "Arquivo non encontrado", 404
    if not os.path.exists(ruta_archivo):
        return "Arquivo non encontrado", 404
    return send_file(ruta_archivo, mimetype='audio/wav')


@bp.route("/download/<filename>")
def descargar_archivo(filename):
    safe_name = secure_filename(filename)
    if not safe_name:
        return "Arquivo non encontrado", 404
    abs_dir = os.path.abspath(DIRECTORIO_SAIDA)
    ruta_arquivo = os.path.abspath(os.path.join(DIRECTORIO_SAIDA, safe_name))
    if os.path.commonpath([ruta_arquivo, abs_dir]) != abs_dir:
        return "Arquivo non encontrado", 404
    if not os.path.exists(ruta_arquivo):
        return "Arquivo non encontrado", 404

    tamano_ficheiro = os.path.getsize(ruta_arquivo)
    nome_descarga_seguro = safe_name

    try:
        response = send_file(ruta_arquivo, as_attachment=True, download_name=nome_descarga_seguro)

        if filename.endswith('.mp4'):
            response.headers["Content-Type"] = "video/mp4"
        elif filename.endswith('.wav'):
            response.headers["Content-Type"] = "audio/wav"

        response.headers["Content-Length"] = str(tamano_ficheiro)
        return response
    except Exception:
        logger.exception(f"Erro enviando archivo {safe_name}")
        abort(500)
