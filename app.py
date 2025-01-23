from flask import Flask, request, render_template, send_from_directory
import os

app = Flask(__name__)

UPLOAD_FOLDER = "./uploads"
OUTPUT_FOLDER = "./outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def encontrar_archivos(output_dir):
    """
    Busca los archivos 'vocals.wav' e 'accompaniment.wav' dentro del directorio generado por Spleeter.
    """
    vocals_path = None
    instrumental_path = None

    for root, _, files in os.walk(output_dir):
        if "vocals.wav" in files:
            vocals_path = os.path.join(root, "vocals.wav")
        if "accompaniment.wav" in files:
            instrumental_path = os.path.join(root, "accompaniment.wav")

    if not vocals_path or not instrumental_path:
        raise FileNotFoundError("No se encontraron las pistas generadas por Spleeter.")

    return vocals_path, instrumental_path

def separar_pistas(filepath):
    """
    Separa las pistas de audio de una canción usando Spleeter.
    """
    from spleeter.separator import Separator
    separator = Separator('spleeter:2stems')  # Inicializar el separador solo cuando se necesite

    output_dir = os.path.join(OUTPUT_FOLDER, os.path.splitext(os.path.basename(filepath))[0])
    os.makedirs(output_dir, exist_ok=True)

    # Ejecutar la separación
    separator.separate_to_file(filepath, output_dir)

    # Buscar los archivos generados
    return encontrar_archivos(output_dir)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Manejar la carga del archivo
        file = request.files.get("file")
        if file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)

            try:
                # Procesar el archivo con Spleeter
                vocals_path, instrumental_path = separar_pistas(filepath)
                
                # Mostrar resultados
                return render_template(
                    "result.html",
                    vocals_file=os.path.relpath(vocals_path, OUTPUT_FOLDER).replace("\\", "/"),
                    instrumental_file=os.path.relpath(instrumental_path, OUTPUT_FOLDER).replace("\\", "/"),
                )
            except Exception as e:
                return f"Error al procesar el archivo: {e}"

    return render_template("index.html")

@app.route("/download/<path:filename>")
def download_file(filename):
    """
    Permite descargar un archivo generado por Spleeter.
    """
    full_path = os.path.join(OUTPUT_FOLDER, filename)
    directory = os.path.dirname(full_path)
    file_name = os.path.basename(full_path)
    return send_from_directory(directory, file_name, as_attachment=True)

if __name__ == "__main__":
    # Usar el puerto dinámico proporcionado por Heroku
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
