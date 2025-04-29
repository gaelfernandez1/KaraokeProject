# app.py
import os
import re
import yt_dlp
from flask import Flask, request, send_file, render_template
from werkzeug.utils import secure_filename

from main import create, create_with_manual_lyrics

# ------------------------------------------------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------------------------------------------------
app = Flask(__name__)

# Directorios
INPUT_DIR = "input"
OUTPUT_DIR = "output"
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Extensións permitidas para a subida
ALLOWED_EXTENSIONS = {"mp4"}


def allowed_file(filename: str) -> bool:
    """Comproba que a extensión do ficheiro estea na lista branca."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def normalize_query(text: str) -> str:
    """
    Normaliza un texto para búsquedas:
      - Elimina parénteses e corchetes co seu contido
      - Sanea espazos e pasa a minúsculas
    """
    text = text.strip()
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower().strip()


def download_youtube_video(url: str, output_dir: str = INPUT_DIR) -> str:
    """
    Descarga un vídeo de YouTube (mellor calidade MP4 ≥720p) ao directorio dado.
    Devolve a ruta local do ficheiro mp4 descargado.
    """
    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'format': 'bestvideo[height>=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return filename


# ------------------------------------------------------------------------------------
# RUTAS
# ------------------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Páxina principal con formulario para URL e/ou subida de MP4."""
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    """
    Xera karaoke automático:
      - Acepta subida de MP4 ou URL de YouTube
      - Chama a create(video_path)
      - Devolve o MP4 xerado
    """
    # 1) ¿Subiuse un MP4?
    video_path = None
    upload = request.files.get("video_file")
    if upload and upload.filename and allowed_file(upload.filename):
        filename = secure_filename(upload.filename)
        video_path = os.path.join(INPUT_DIR, filename)
        upload.save(video_path)
        app.logger.info(f"[generate] Ficheiro subido gardado en: {video_path}")
    else:
        # 2) Fallback a URL de YouTube
        youtube_url = request.form.get("youtube_url", "").strip()
        if not youtube_url:
            return "Debes subir un MP4 ou proporcionar unha URL de YouTube.", 400
        try:
            video_path = download_youtube_video(youtube_url)
            app.logger.info(f"[generate] Vídeo descargado en: {video_path}")
        except Exception as e:
            app.logger.error(f"[generate] Erro descargando vídeo: {e}")
            return f"Erro descargando vídeo: {e}", 500

    # 3) Chamada ao xerador
    try:
        output_name = create(video_path)
        if not output_name:
            raise RuntimeError("create() devolveu cadea baleira")
    except Exception as e:
        app.logger.exception("[generate] Erro en create()")
        return f"Erro xerando karaoke: {e}", 500

    # 4) Envío do resultado
    out_path = os.path.join(OUTPUT_DIR, output_name)
    if not os.path.exists(out_path):
        app.logger.error(f"[generate] Non existe saída: {out_path}")
        return "Non se atopou o arquivo de saída", 500

    return send_file(out_path, as_attachment=True)


@app.route("/manual_lyrics_form", methods=["GET"])
def manual_lyrics_form():
    """Formulario para karaoke con letra manual."""
    return render_template("manual_lyrics_form.html")


@app.route("/process_manual_lyrics", methods=["POST"])
def process_manual_lyrics():
    """
    Xera karaoke con letra manual (forced alignment):
      - Acepta subida de MP4 ou URL de YouTube
      - Le o textarea 'manual_lyrics'
      - Chama a create_with_manual_lyrics(video_path, lyrics, lang)
    """
    # 1) Vídeo: arquivo ou URL
    video_path = None
    upload = request.files.get("video_file")
    if upload and upload.filename and allowed_file(upload.filename):
        filename = secure_filename(upload.filename)
        video_path = os.path.join(INPUT_DIR, filename)
        upload.save(video_path)
        app.logger.info(f"[process_manual_lyrics] Ficheiro subido gardado en: {video_path}")
    else:
        youtube_url = request.form.get("youtube_url", "").strip()
        if not youtube_url:
            return "Debes subir un MP4 ou proporcionar unha URL de YouTube.", 400
        try:
            video_path = download_youtube_video(youtube_url)
            app.logger.info(f"[process_manual_lyrics] Vídeo descargado en: {video_path}")
        except Exception as e:
            app.logger.error(f"[process_manual_lyrics] Erro descargando vídeo: {e}")
            return f"Erro descargando vídeo: {e}", 500

    # 2) Letra manual
    lyrics = request.form.get("manual_lyrics", "").strip()
    if not lyrics:
        return "Falta o texto da letra.", 400

    # 3) Xerar karaoke forced alignment
    try:
        output_name = create_with_manual_lyrics(video_path, lyrics, language="es")
        if not output_name:
            raise RuntimeError("create_with_manual_lyrics devolveu cadea baleira")
    except Exception as e:
        app.logger.exception("[process_manual_lyrics] Erro en create_with_manual_lyrics()")
        return f"Erro xerando karaoke con letra manual: {e}", 500

    # 4) Envío do resultado
    out_path = os.path.join(OUTPUT_DIR, output_name)
    if not os.path.exists(out_path):
        app.logger.error(f"[process_manual_lyrics] Non existe saída: {out_path}")
        return "Non se atopou o arquivo de saída", 500

    return send_file(out_path, as_attachment=True)


@app.route("/lyrics_form", methods=["GET"])
def lyrics_form():
    """Formulario preliminar para busca de letra por título/artista."""
    return render_template("lyrics_form.html")


@app.route("/search_lyrics", methods=["POST"])
def search_lyrics():
    """
    Demo de normalización de título e artista.
    No futuro substituír por busca real.
    """
    song_title = request.form.get("song_title", "").strip()
    artist = request.form.get("artist", "").strip()
    clean_title = normalize_query(song_title)
    clean_artist = normalize_query(artist)

    return (
        f"<p>Título orixinal: {song_title}</p>\n"
        f"<p>Artista orixinal: {artist}</p>\n"
        "<hr/>\n"
        f"<p>Título normalizado: {clean_title}</p>\n"
        f"<p>Artista normalizado: {clean_artist}</p>\n"
        "<br/>\n"
        "<p>Aquí, no futuro, implementaremos a busca real da letra.</p>"
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
