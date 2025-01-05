from flask import Flask, request, render_template, url_for, send_from_directory
import os
import subprocess
import whisper
import textwrap
from markupsafe import Markup

app = Flask(__name__)

UPLOAD_FOLDER = "./uploads"
OUTPUT_FOLDER = "./outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Filtro personalizado para convertir saltos de línea a <br>
@app.template_filter("nl2br")
def nl2br(value):
    return Markup(value.replace("\n", "<br>"))

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Manejar el archivo subido
        file = request.files["file"]
        if file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            
            # Procesar el archivo
            result = procesar_archivo(filepath)
            
            # Mostrar resultados
            return render_template("result.html", result=result, filename=file.filename)
    
    return render_template("index.html")

def procesar_archivo(filepath):
    """
    Separa las pistas con Demucs y transcribe la letra con Whisper.
    """
    # Generar la ruta base de salida
    output_dir = os.path.join(OUTPUT_FOLDER, os.path.splitext(os.path.basename(filepath))[0])
    os.makedirs(output_dir, exist_ok=True)
    
    # Ejecutar Demucs
    subprocess.run(["demucs", "-o", output_dir, filepath], check=True)
    
    # Ruta a la subcarpeta generada por Demucs
    demucs_output_dir = os.path.join(output_dir, "htdemucs", os.path.splitext(os.path.basename(filepath))[0])
    print(f"Carpeta generada por Demucs: {demucs_output_dir}")  # Depuración

    # Asegurarse de que las rutas apuntan a los archivos generados
    vocals_file = os.path.join(demucs_output_dir, "vocals.wav")
    instrumental_file = os.path.join(demucs_output_dir, "other.wav")  # Ajusta si es otro archivo

    # Comprobar que los archivos existen
    if not os.path.exists(vocals_file) or not os.path.exists(instrumental_file):
        raise FileNotFoundError("No se encontraron las pistas generadas por Demucs.")

    # Transcribir la canción original con Whisper
    model = whisper.load_model("base")
    result = model.transcribe(filepath)

    # Formatear texto con saltos de línea
    text = result["text"]
    formatted_text = "\n".join(textwrap.wrap(text, width=80))

    return {
        "text": formatted_text,
        "vocals_file": os.path.relpath(vocals_file, OUTPUT_FOLDER).replace("\\", "/"),
        "instrumental_file": os.path.relpath(instrumental_file, OUTPUT_FOLDER).replace("\\", "/"),
    }



@app.route("/download/<path:filename>")
def download_file(filename):
    """
    Permite descargar un archivo generado por Demucs.
    """
    full_path = os.path.join(OUTPUT_FOLDER, filename)
    print(f"Intentando servir archivo: {full_path}")  # Depuración
    directory = os.path.dirname(full_path)
    file_name = os.path.basename(full_path)
    return send_from_directory(directory, file_name, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
