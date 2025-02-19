from flask import Flask, request, send_file
import os

import yt_dlp

# Importamos la lógica principal (demucs, moviepy) desde main.py:
from main import create, create_with_manual_lyrics

app = Flask(__name__)

def normalize_query(text: str) -> str:
    """
    Limpia y normaliza la cadena para búsqueda.
    """
    import re
    text = text.strip()
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.lower().strip()
    return text

def download_youtube_video(url, output_dir="input"):
    """
    Descarga con yt-dlp.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'format': 'mp4/bestaudio/bestvideo',
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        downloaded_filename = ydl.prepare_filename(info)
        return downloaded_filename

@app.route("/", methods=["GET"])
def index():
    """
    Página principal con 2 opciones:
      - Karaoke con transcripción (WhisperX)
      - Letra Manual
    """
    return """
    <html>
      <body>
        <h1>Karaoke Multilenguaje (Contenedor A)</h1>
        
        <h2>Opción A: Karaoke con Transcripción Automática (WhisperX)</h2>
        <form action="/generate" method="post">
          <label>URL de YouTube:</label>
          <input type="text" name="youtube_url" required>
          <button type="submit">Procesar con WhisperX</button>
        </form>

        <hr>

        <h2>Opción B: Letra Manual</h2>
        <p>Introduce la URL de YouTube y la letra manualmente.</p>
        <a href="/manual_lyrics_form">Usar Letra Manual</a>
        
        <hr>

        <h2>(Opcional) Búsqueda de Letra por Título/Artista</h2>
        <p>(En desarrollo) <a href="/lyrics_form">Buscar Letra</a></p>
      </body>
    </html>
    """

@app.route("/generate", methods=["POST"])
def generate():
    """
    Recibe 'youtube_url', descarga el video,
    llama create(...) que internamente invoca WhisperX a través del endpoint.
    """
    youtube_url = request.form.get("youtube_url")
    if not youtube_url:
        return "Falta parámetro 'youtube_url'", 400

    try:
        video_path = download_youtube_video(youtube_url)
    except Exception as e:
        return f"Error descargando el video: {e}", 500

    try:
        # Llamamos create(...) => separa con demucs => vocals.wav => 
        # llama al endpoint whisperx => compone karaoke final
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
    return """
    <html>
      <body>
        <h1>Karaoke con Letra Manual</h1>
        <form action="/process_manual_lyrics" method="post">
          <label>URL de YouTube:</label><br>
          <input type="text" name="youtube_url" required><br><br>

          <label>Letra (texto plano):</label><br>
          <textarea name="manual_lyrics" rows="10" cols="60"></textarea><br><br>

          <button type="submit">Procesar con Letra Manual</button>
        </form>
      </body>
    </html>
    """

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
        # Usa la versión manual (no llama whisperx).
        output_filename = create_with_manual_lyrics(video_path, lyrics_text)
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
    return """
    <html>
      <body>
        <h1>Búsqueda de Letra (futuro)</h1>
        <form action="/search_lyrics" method="post">
          <label>Título de la canción:</label>
          <input type="text" name="song_title" required>
          <br><br>
          <label>Artista (opcional):</label>
          <input type="text" name="artist">
          <br><br>
          <button type="submit">Buscar Letra</button>
        </form>
      </body>
    </html>
    """

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
    # Importante: host="0.0.0.0" para que Docker redirija
    app.run(debug=True, host="0.0.0.0", port=5000)
