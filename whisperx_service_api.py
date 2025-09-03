from flask import Flask, request, jsonify
import torch
import whisperx
import math
import os
import librosa
import ssl
from speaker_diarization import (
    perform_speaker_diarization, 
    merge_transcription_with_speakers,
    assign_colors_to_speakers
)
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
    enable_diarization = datos.get("enable_diarization", False)
    hf_token = datos.get("hf_token", None)
    whisper_model = datos.get("whisper_model", "small")  

    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"-------USANDO DISPOSITIVO----- device={dispositivo}, audio={ruta_audio}")

    if letra_manual:        #FORCED ALIGNMENT
        if not codigo_idioma:            
            
            try:
                modelo_deteccion = whisperx.load_model(whisper_model, device=dispositivo, compute_type="int8")
                resultado_deteccion = modelo_deteccion.transcribe(ruta_audio, language=None)  
                codigo_idioma = resultado_deteccion["language"]
                print(f"Autodetectado con modelo {whisper_model} => {codigo_idioma}")

                # Liberar memoria 
                del modelo_deteccion
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
            except Exception as e:
                print(f"Erro, usando inglés por defecto: {e}")
                codigo_idioma = "en"

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
        
        print(f"Usando modelo {whisper_model} para transcrición automática")
        modelo = whisperx.load_model(whisper_model, device=dispositivo, compute_type="int8")
        resultado = modelo.transcribe(ruta_audio, language=None)  
        codigo_idioma = resultado["language"]
        print(f"idioma detectado con {whisper_model}={codigo_idioma}")
        del modelo
        torch.cuda.empty_cache() if torch.cuda.is_available() else None

        modelo_alineacion, metadatos = whisperx.load_align_model(codigo_idioma, dispositivo)
        resultado_alineado = whisperx.align(
            resultado["segments"], 
            modelo_alineacion, 
            metadatos, 
            ruta_audio, 
            dispositivo
        )

    segmentos_palabras = resultado_alineado["word_segments"]
    
    #speaker diarization
    speaker_info = None
    speaker_colors = None
    if enable_diarization:
        try:
            speaker_info = perform_speaker_diarization(ruta_audio, hf_token)
            if speaker_info and speaker_info["num_speakers"] > 1:
                print(f"Detectados {speaker_info['num_speakers']} speakers")
                segmentos_palabras = merge_transcription_with_speakers(
                    segmentos_palabras, 
                    speaker_info["segments"]
                )
                speaker_colors = assign_colors_to_speakers(speaker_info["speakers"])
                print(f"Colores asignados: {speaker_colors}")
            else:
                print("error en diarization")
        except Exception as e:
            print(f"Error en speaker diarization: {e}")
            # Continuar sin diarization

    #Crear srt final a nivel de palabra (con speaker info se hai)
    ruta_srt = ruta_audio.replace(".wav", "_whisperx.srt")
    with open(ruta_srt, "w", encoding="utf-8") as f:
        indice = 1
        for seg in segmentos_palabras:
            if "word" not in seg:
                continue
            texto = seg["word"].strip()
            inicio = seg["start"]
            fin = seg["end"]
            
            if "speaker" in seg and speaker_colors:
                speaker_id = seg["speaker"]
                color = speaker_colors.get(speaker_id, "#FFFFFF")
                texto = f"{speaker_id}|{color}|{texto}"
            
            bloque = f"{indice}\n{sec2tc(inicio)} --> {sec2tc(fin)}\n{texto}\n\n"
            f.write(bloque)
            indice += 1

    response_data = {
        "srt_path": ruta_srt, 
        "message": "Alignment done"
    }
    
    if speaker_info:
        response_data["speaker_info"] = speaker_info
        response_data["speaker_colors"] = speaker_colors
    
    return jsonify(response_data), 200


if __name__ == "__main__":
    #Levantamos en modo debug e en CPU
    app.run(host="0.0.0.0", port=5001, debug=True)