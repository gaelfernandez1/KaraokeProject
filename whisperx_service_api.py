from flask import Flask, request, jsonify
import torch
import whisperx
import math
import os
import librosa
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

app = Flask(__name__)

def sec2tc(sec_float):
    ms = int(math.floor(sec_float*1000))
    hh = ms//3600000
    mm = (ms%3600000)//60000
    ss = (ms%60000)//1000
    ms = (ms%1000)
    return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"

def get_duration(audio_file):
    return librosa.get_duration(filename=audio_file)


#Esperase un json, si existe a letra manual, faise forced aligment.
# si language non está no payload autodetectase o idioma
# podense probar varios modelos pero notase unha diferencia escasa polo menos nas cancions en galego que estou probando. Pode ser un error?
# se non existe letra manual transcribese automaticamente con WhisperX
@app.route("/align", methods=["POST"])
def align_endpoint():

    datos = request.get_json()
    if not datos or "audio_path" not in datos:
        return jsonify({"error": "Missing 'audio_path'"}), 400

    ruta_audio = datos["audio_path"]
    if not os.path.exists(ruta_audio):
        return jsonify({"error": f"File {ruta_audio} not found"}), 404

    letra_manual = datos.get("manual_lyrics", None)
    codigo_idioma = datos.get("language", None)  

    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"-------USANDO DISPOSITIVO----- device={dispositivo}, audio={ruta_audio}")

    if letra_manual:        #FORCED ALIGNMENT
        if not codigo_idioma:            
            modelo_deteccion = whisperx.load_model("large-v2", device=dispositivo, compute_type="float32")
            resultado_deteccion = modelo_deteccion.transcribe(ruta_audio, language=None)  
            codigo_idioma = resultado_deteccion["language"]
            print(f"Autodetectado => {codigo_idioma}")

        total_segundos = get_duration(ruta_audio)

        # Simulase segments cun único gran segmento [0..fin]
        resultado = {
            "language": codigo_idioma,
            "segments": [
                {
                    "text": letra_manual,
                    "start": 0.0,
                    "end": total_segundos
                }
            ]
        }        
        modelo_alineacion, metadatos = whisperx.load_align_model(codigo_idioma, dispositivo)
        resultado_alineado = whisperx.align(
            resultado["segments"], 
            modelo_alineacion, 
            metadatos, 
            ruta_audio, 
            dispositivo
        )

    else:        #TRANSCRICIÓN AUTOMÁTICA
        modelo = whisperx.load_model("large-v2", device=dispositivo, compute_type="float32")
        resultado = modelo.transcribe(ruta_audio, language=None)  
        codigo_idioma = resultado["language"]
        print(f"IDIOMA DETECTADO={codigo_idioma}")

        modelo_alineacion, metadatos = whisperx.load_align_model(codigo_idioma, dispositivo)
        resultado_alineado = whisperx.align(
            resultado["segments"], 
            modelo_alineacion, 
            metadatos, 
            ruta_audio, 
            dispositivo
        )

    segmentos_palabras = resultado_alineado["word_segments"]

    #Crear SRT final a nivel de palabra
    ruta_srt = ruta_audio.replace(".wav", "_whisperx.srt")
    with open(ruta_srt, "w", encoding="utf-8") as f:
        indice = 1
        for seg in segmentos_palabras:
            if "word" not in seg:
                continue
            texto = seg["word"].strip()
            inicio = seg["start"]
            fin = seg["end"]
            bloque = f"{indice}\n{sec2tc(inicio)} --> {sec2tc(fin)}\n{texto}\n\n"
            f.write(bloque)
            indice += 1

    return jsonify({"srt_path": ruta_srt, "message": "Alignment done"}), 200


if __name__ == "__main__":
    #Levantamos en modo debug e en CPU
    app.run(host="0.0.0.0", port=5001, debug=True)