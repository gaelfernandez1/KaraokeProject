from flask import Flask, request, send_file, jsonify
import os
import uuid

from main import create
import yt_dlp

app = Flask(__name__)

def download_youtube_video(url, output_dir="input"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'format': 'mp4/bestaudio/bestvideo'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        downloaded_filename = ydl.prepare_filename(info)
        return downloaded_filename

@app.route("/", methods=["GET"])
def index():
    return """
    <html>
      <body>
        <h1>Generar Karaoke</h1>
        <form action="/generate" method="post">
          <label>URL de YouTube:</label>
          <input type="text" name="youtube_url">
          <button type="submit">Procesar</button>
        </form>
      </body>
    </html>
    """

@app.route("/generate", methods=["POST"])
def generate():
    """
    Endpoint que recibe 'youtube_url', descarga el video,
    genera el karaoke y devuelve el archivo resultante.
    """
    youtube_url = request.form.get("youtube_url")
    if not youtube_url:
        return "Falta parámetro 'youtube_url'", 400

    # 1) Descargar el video
    try:
        video_path = download_youtube_video(youtube_url)
    except Exception as e:
        return f"Error descargando el video: {e}", 500

    # 2) Crear el karaoke (usa tu función de main.py)
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

    # Podrías usar send_file para enviarlo directamente
    return send_file(result_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
