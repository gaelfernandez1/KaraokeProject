import os
import yt_dlp
from flask import Blueprint, request, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename

from karaoke.workers.celery_tasks import process_automatic_karaoke, process_manual_lyrics_karaoke, process_instrumental_only

bp = Blueprint('generation', __name__)

DIRECTORIO_ENTRADA = "input"
DIRECTORIO_SAIDA = "output"
EXTENSIONES_PERMITIDAS = {"mp4"}
EXTENSIONES_AUDIO_PERMITIDAS = {"wav", "mp3"}
EXTENSIONES_INSTRUMENTAL_PERMITIDAS = {"mp4", "mp3"}


# PAra comprobar si o archivo ten unha extension permitida
def archivo_permitido(nome_arquivo: str) -> bool:
    return "." in nome_arquivo and nome_arquivo.rsplit(".", 1)[1].lower() in EXTENSIONES_PERMITIDAS



def archivo_instrumental_permitido(nome_arquivo: str) -> bool:
    return "." in nome_arquivo and nome_arquivo.rsplit(".", 1)[1].lower() in EXTENSIONES_INSTRUMENTAL_PERMITIDAS


def descargar_video_youtube(url: str, directorio_saida: str = DIRECTORIO_ENTRADA) -> str:
    """ Funcion para descargar un video de YT e devolve a ruta do mp4 descargado """

    opcions_ydl = {
        'outtmpl': os.path.join(directorio_saida, '%(title)s.%(ext)s'),
        'format': 'best[height<=720][ext=mp4]/best[height<=1080][ext=mp4]/best[ext=mp4]/best',
        'noplaylist': True,
        'extract_flat': False,
        'concurrent_fragment_downloads': 1,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        'extractor_args': {
            'youtube': {
                'skip': ['hls', 'dash'],
                'player_client': ['android', 'web']
            }
        }
    }
    with yt_dlp.YoutubeDL(opcions_ydl) as ydl:
        info = ydl.extract_info(url, download=True)
        nome_ficheiro = ydl.prepare_filename(info)
        return nome_ficheiro


@bp.route("/", methods=["GET"])
def inicio():
    return render_template("index.html")


#asincronia
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
        except Exception as e:
            return f"Error descargando vídeo: {e}", 500

    enable_diarization = request.form.get("enable_diarization") == "true"
    hf_token = request.form.get("hf_token", "").strip() if enable_diarization else None
    whisper_model = request.form.get("whisper_model", "small").strip()  #para poder elixir modelo de whisper na interface

    source_type = "upload" if arquivo_subido else "youtube"
    source_url = url_youtube if not arquivo_subido else None

    task = process_automatic_karaoke.delay(
        ruta_video, enable_diarization, hf_token, whisper_model, source_type, source_url, True
    )

    session['current_task_id'] = task.id
    session['task_type'] = 'automatic'

    return redirect(url_for('tasks.mostrar_progreso', task_id=task.id))


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
        except Exception as e:
            return f"Erro descargando vídeo: {e}", 500

    letra_manual = request.form.get("manual_lyrics", "").strip()
    if not letra_manual:
        return "Falta o texto da letra.", 400

    enable_diarization = request.form.get("enable_diarization") == "true"
    hf_token = request.form.get("hf_token", "").strip() if enable_diarization else None
    whisper_model = request.form.get("whisper_model", "small").strip() #o mesmo, para elegir modelo de whisper

    source_type = "upload" if arquivo_subido else "youtube"
    source_url = url_youtube if not arquivo_subido else None

    task = process_manual_lyrics_karaoke.delay(
        ruta_video, letra_manual, None, enable_diarization, hf_token, whisper_model,
        source_type, source_url, True
    )

    session['current_task_id'] = task.id
    session['task_type'] = 'manual_lyrics'

    return redirect(url_for('tasks.mostrar_progreso', task_id=task.id))


@bp.route("/generate_instrumental", methods=["POST"])
def xerar_instrumental():
    ruta_video = None
    arquivo_subido = request.files.get("video_file")
    if arquivo_subido and arquivo_subido.filename and archivo_instrumental_permitido(arquivo_subido.filename):
        nome_ficheiro = secure_filename(arquivo_subido.filename)
        ruta_video = os.path.join(DIRECTORIO_ENTRADA, nome_ficheiro)
        arquivo_subido.save(ruta_video)
    else:
        url_youtube = request.form.get("youtube_url", "").strip()
        if not url_youtube:
            return "Tes que mandar un mp4/mp3 ou un link de YouTube", 400
        try:
            ruta_video = descargar_video_youtube(url_youtube)
        except Exception as e:
            return f"Erro descargando vídeo: {e}", 500

    source_type = "upload" if arquivo_subido else "youtube"
    source_url = url_youtube if not arquivo_subido else None

    task = process_instrumental_only.delay(ruta_video, source_type, source_url, True)

    session['current_task_id'] = task.id
    session['task_type'] = 'instrumental'

    return redirect(url_for('tasks.mostrar_progreso', task_id=task.id))
