# app.py
from flask import Flask, request, send_file, render_template
import os
import yt_dlp
import json

# Importamos las funciones de main.py
from main import create, create_with_manual_lyrics

app = Flask(__name__)

def normalize_query(text: str) -> str:
    import re
    text = text.strip()
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.lower().strip()
    return text

def download_youtube_video(url, output_dir="input"):
    """Descarga un video de YouTube como mp4 usando yt_dlp."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'format': 'bestvideo[height>=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        print("Título:", info.get("title"))
        if "requested_formats" in info:
            print("Formatos solicitados (requested_formats):")
            for fmt in info["requested_formats"]:
                print("  format_id: {}, ext: {}, resolution: {}, format note: {}".format(
                    fmt.get("format_id"), fmt.get("ext"), fmt.get("resolution"), fmt.get("format_note")
                ))
        else:
            print("Formato seleccionado:", info.get("format"))
        downloaded_filename = ydl.prepare_filename(info)
        return downloaded_filename



@app.route("/", methods=["GET"])
def index():
    # Renderiza la plantilla 'index.html'
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    youtube_url = request.form.get("youtube_url")
    if not youtube_url:
        return "Falta parámetro 'youtube_url'", 400

    try:
        video_path = download_youtube_video(youtube_url)
    except Exception as e:
        return f"Error descargando el video: {e}", 500

    try:
        output_filename = create(video_path)
        if not output_filename:
            return "Error generando karaoke", 500
    except Exception as e:
        return f"Error procesando karaoke: {e}", 500

    result_path = os.path.join("output", output_filename)
    if not os.path.exists(result_path):
        return "No se encontró el archivo de salida", 500

    return send_file(result_path, as_attachment=True)

@app.route("/manual_lyrics_form", methods=["GET"])
def manual_lyrics_form():
    # Renderiza la plantilla 'manual_lyrics_form.html'
    return render_template("manual_lyrics_form.html")

@app.route("/process_manual_lyrics", methods=["POST"])
def process_manual_lyrics():
    youtube_url = request.form.get("youtube_url", "").strip()
    lyrics_text = request.form.get("manual_lyrics", "").strip()

    if not youtube_url or not lyrics_text:
        return "Faltan datos: URL de YouTube y/o letra.", 400

    try:
        video_path = download_youtube_video(youtube_url)
    except Exception as e:
        return f"Error descargando el video: {e}", 500

    try:
        # Llamamos a la función con forced alignment
        output_filename = create_with_manual_lyrics(video_path, lyrics_text, language="es")
        if not output_filename:
            return "Error generando karaoke con letra manual", 500
    except Exception as e:
        return f"Error procesando karaoke: {e}", 500

    result_path = os.path.join("output", output_filename)
    if not os.path.exists(result_path):
        return "No se encontró el archivo de salida", 500

    return send_file(result_path, as_attachment=True)

@app.route("/lyrics_form", methods=["GET"])
def lyrics_form():
    # Renderiza la plantilla 'lyrics_form.html'
    return render_template("lyrics_form.html")

@app.route("/search_lyrics", methods=["POST"])
def search_lyrics():
    song_title = request.form.get("song_title", "").strip()
    artist = request.form.get("artist", "").strip()

    clean_song_title = normalize_query(song_title)
    clean_artist = normalize_query(artist)

    return f"""
    <p>Título original: {song_title}</p>
    <p>Artista original: {artist}</p>
    <hr>
    <p>Título normalizado: {clean_song_title}</p>
    <p>Artista normalizado: {clean_artist}</p>
    <br>
    <p>Aquí, en el futuro, implementaremos la búsqueda real de la letra.</p>
    """

if __name__ == "__main__":
    # Puedes usar debug=True en desarrollo
    app.run(debug=True, host="0.0.0.0", port=5000)