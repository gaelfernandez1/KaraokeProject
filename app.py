import os
import yt_dlp
from flask import Flask, request, send_file, render_template
from werkzeug.utils import secure_filename

from karaoke_generator import create, create_with_manual_lyrics
from gpu_utils import print_system_summary

app = Flask(__name__)


print_system_summary()

DIRECTORIO_ENTRADA = "input"
DIRECTORIO_SAIDA = "output"
os.makedirs(DIRECTORIO_ENTRADA, exist_ok=True)
os.makedirs(DIRECTORIO_SAIDA, exist_ok=True)

EXTENSIONES_PERMITIDAS = {"mp4"}


# PAra comprobar si o archivo ten unha extension permitida
def archivo_permitido(nome_arquivo: str) -> bool:
    return "." in nome_arquivo and nome_arquivo.rsplit(".", 1)[1].lower() in EXTENSIONES_PERMITIDAS


def descargar_video_youtube(url: str, directorio_saida: str = DIRECTORIO_ENTRADA) -> str:
    """ Funcion para descargar un video de YT e devolve a ruta do mp4 descargado """

    opcions_ydl = {
        'outtmpl': os.path.join(directorio_saida, '%(title)s.%(ext)s'),
        'format': 'bestvideo[height>=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',   # Esta combinacion funciona, varias que probei antes daban diversos errores
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(opcions_ydl) as ydl:
        info = ydl.extract_info(url, download=True)
        nome_ficheiro = ydl.prepare_filename(info)
        return nome_ficheiro



@app.route("/", methods=["GET"])
def inicio():
    return render_template("index.html")

#Esta é para generar un Karaoke automático. Chama a create() e devolve un mp4. Hai varios try except debido a sucesivos errores que foron aparecendo
@app.route("/generate", methods=["POST"])
def xerar_karaoke():

    # Si se lle pasa un MP4:
    ruta_video = None
    arquivo_subido = request.files.get("video_file")
    if arquivo_subido and arquivo_subido.filename and archivo_permitido(arquivo_subido.filename):
        nome_ficheiro = secure_filename(arquivo_subido.filename)
        ruta_video = os.path.join(DIRECTORIO_ENTRADA, nome_ficheiro)
        arquivo_subido.save(ruta_video)
    else:
        #especie de Fallback a  unha url de YT
        url_youtube = request.form.get("youtube_url", "").strip()
        if not url_youtube:
            return "Debes mandar ou un mp4 ou un link de Youtube", 400
        try:
            ruta_video = descargar_video_youtube(url_youtube)
        except Exception as e:
            return f"Error descargando vídeo: {e}", 500                   #Chamada ao xerador
    
    enable_diarization = request.form.get("enable_diarization") == "true"     #obter os parametros para diarizaation
    hf_token = request.form.get("hf_token", "").strip() if enable_diarization else None
    
    try:
        nome_saida = create(ruta_video, enable_diarization, hf_token)
        if not nome_saida:
            raise RuntimeError("create() devolveu cadea baleira")
    except Exception as e:
        return f"Error generando karaoke: {e}", 500               #envío do resultado
    ruta_saida = os.path.join(DIRECTORIO_SAIDA, nome_saida)
    if not os.path.exists(ruta_saida):
        #debug: buscar archivos parecidos para debug
        import glob
        arquivos_similares = glob.glob(os.path.join(DIRECTORIO_SAIDA, "karaoke_*"))
        app.logger.info(f" Archivos similares encontrados: {arquivos_similares}")
        return "Non se atopou o arquivo de saída", 500

    tamano_ficheiro = os.path.getsize(ruta_saida)
    
    nome_descarga_seguro = secure_filename(nome_saida)

    try:
        response = send_file(ruta_saida, as_attachment=True, download_name=nome_descarga_seguro)
        #Esto son headers a mayores para mellorar a compatibilidad
        response.headers["Content-Type"] = "video/mp4"
        response.headers["Content-Length"] = str(tamano_ficheiro)
        return response
    except Exception as e:
        return f"Erro enviando archiivo: {e}", 500


@app.route("/manual_lyrics_form", methods=["GET"])
def formulario_letras_manuales():
    return render_template("manual_lyrics_form.html")


@app.route("/process_manual_lyrics", methods=["POST"])
def procesar_letras_manuales():
    """
    Esto genera o karaoke con letra manual (forced alignment):
      - Acepta subida de MP4 ou URL de YouTube
      - Lee o textarea 'manual_lyrics' e chama a create_with_manual_lyrics(video_path, lyrics, lang)
    """
    #Pasaslle un mp4 ou un link de yt, igual que antes
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
            return f"Error descargando vídeo: {e}", 500

    #Letra manual
    letra_manual = request.form.get("manual_lyrics", "").strip()
    if not letra_manual:
        return "Falta o texto da letra.", 400
    
    
    enable_diarization = request.form.get("enable_diarization") == "true"      # o mesmo, parametros para diarization
    hf_token = request.form.get("hf_token", "").strip() if enable_diarization else None
    
    #Xerar karaoke forced alignment
    try:
        nome_saida = create_with_manual_lyrics(ruta_video, letra_manual, language=None, enable_diarization=enable_diarization, hf_token=hf_token)
        if not nome_saida:
            raise RuntimeError("create_with_manual_lyrics devolveu cadea baleira")
    except Exception as e:
        return f"Erro xerando karaoke con letra manual: {e}", 500  #Enviamos o resultado
    ruta_saida = os.path.join(DIRECTORIO_SAIDA, nome_saida)
    if not os.path.exists(ruta_saida):
        app.logger.error(f"[process_manual_lyrics] Non existe saída: {ruta_saida}")

        #archivos similares para debug
        import glob
        arquivos_similares = glob.glob(os.path.join(DIRECTORIO_SAIDA, "karaoke_manual_*"))
        app.logger.info(f"[process_manual_lyrics] Arquivos similares encontrados: {arquivos_similares}")
        return "Non se atopou o archivo de salida", 500

    
    tamano_ficheiro = os.path.getsize(ruta_saida)
    
    nome_descarga_seguro = secure_filename(nome_saida)

    try:
        response = send_file(ruta_saida, as_attachment=True, download_name=nome_descarga_seguro)
        
        response.headers["Content-Type"] = "video/mp4"
        response.headers["Content-Length"] = str(tamano_ficheiro)
        return response
    except Exception as e:
        return f"Erro enviando arquivo: {e}", 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
