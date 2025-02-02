from flask import Flask, request, send_file
import os
import uuid

from main import create, create_with_manual_lyrics
import yt_dlp

app = Flask(__name__)

def normalize_query(text: str) -> str:
    """
    Limpia y normaliza la cadena para mejorar la búsqueda de letras.
    - Quita espacios en extremos
    - Elimina paréntesis [..] y (..)
    - Sustituye múltiples espacios por uno
    - Pasa a minúsculas (opcional)
    """
    import re
    text = text.strip()
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.lower().strip()
    return text

def download_youtube_video(url, output_dir="input"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'format': 'mp4/bestaudio/bestvideo',
        'noplaylist': True  # Para que no descargue playlists accidentalmente
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        downloaded_filename = ydl.prepare_filename(info)
        return downloaded_filename


@app.route("/", methods=["GET"])
def index():
    """
    Muestra la página principal con dos opciones:
    1) Generar karaoke con transcripción de Whisper
    2) Generar karaoke con letra manual
    """
    return """
    <html>
      <body>
        <h1>Karaoke Multilenguaje</h1>
        
        <h2>Opción A: Karaoke con Transcripción Automática (Whisper)</h2>
        <form action="/generate" method="post">
          <label>URL de YouTube:</label>
          <input type="text" name="youtube_url" required>
          <button type="submit">Procesar con Whisper</button>
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
    Endpoint que recibe 'youtube_url', descarga el video,
    genera el karaoke con Whisper y devuelve el archivo resultante.
    """
    youtube_url = request.form.get("youtube_url")
    if not youtube_url:
        return "Falta parámetro 'youtube_url'", 400

    # 1) Descargar el video
    try:
        video_path = download_youtube_video(youtube_url)
    except Exception as e:
        return f"Error descargando el video: {e}", 500

    # 2) Crear el karaoke con Whisper
    try:
        output_filename = create(video_path)
        if not output_filename:
            return "Error generando karaoke", 500
    except Exception as e:
        return f"Error procesando karaoke: {e}", 500

    # 3) Devolver el archivo resultante
    result_path = os.path.join("output", output_filename)
    if not os.path.exists(result_path):
        return "No se encontró el archivo de salida", 500

    return send_file(result_path, as_attachment=True)


@app.route("/manual_lyrics_form", methods=["GET"])
def manual_lyrics_form():
    """
    Formulario para que el usuario introduzca manualmente la letra
    y la URL de YouTube.
    """
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
        import traceback
        traceback.print_exc()  # mostrará más info en la consola
        return f"Error descargando el video: {e}", 500

    try:
        output_filename = create_with_manual_lyrics(video_path, lyrics_text)
        if not output_filename:
            return "Error generando karaoke con letra manual", 500
    except Exception as e:
        import traceback
        print("=== ERROR DETECTADO ===")
        traceback.print_exc()  # imprime traceback COMPLETO en la consola
        return f"Error procesando karaoke: {e}", 500

    result_path = os.path.join("output", output_filename)
    if not os.path.exists(result_path):
        return "No se encontró el archivo de salida", 500

    return send_file(result_path, as_attachment=True)



@app.route("/lyrics_form", methods=["GET"])
def lyrics_form():
    """
    (En desarrollo) Búsqueda de la letra por título y artista
    """
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
    """
    Pendiente de implementación de la lógica de búsqueda de letras en portales.
    """
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
    app.run(debug=True)
