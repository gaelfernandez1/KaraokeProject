from flask import Flask, request, jsonify
import torch
import whisperx
import math
import os
import librosa

app = Flask(__name__)

def sec2tc(sec_float):
    ms = int(math.floor(sec_float*1000))
    hh = ms//3600000
    mm = (ms%3600000)//60000
    ss = (ms%60000)//1000
    mmm= (ms%1000)
    return f"{hh:02}:{mm:02}:{ss:02},{mmm:03}"

def get_duration(audio_file):
    return librosa.get_duration(filename=audio_file)

@app.route("/align", methods=["POST"])
def align_endpoint():
    """
    Espera un JSON con al menos: { "audio_path": "/data/vocals.wav" }
    Opcionalmente: { "manual_lyrics": "texto...", "language": "es" }

    Si 'manual_lyrics' existe, hacemos forced alignment con esa letra.
      - Si 'language' NO está en el payload, autodetectamos el idioma
        con un modelo pequeño (tiny o medium), y luego forzamos alignment.

    Si 'manual_lyrics' NO existe, transcribimos automáticamente con WhisperX.
    """

    data = request.get_json()
    if not data or "audio_path" not in data:
        return jsonify({"error": "Missing 'audio_path'"}), 400

    audio_path = data["audio_path"]
    if not os.path.exists(audio_path):
        return jsonify({"error": f"File {audio_path} not found"}), 404

    manual_lyrics = data.get("manual_lyrics", None)
    lang_code = data.get("language", None)  # si no envían nada, autodetect

    # FORZAMOS CPU
    device = "cpu"
    print(f"[WhisperX API] Forzando device=CPU => {device}, audio={audio_path}")

    if manual_lyrics:
        # === FORCED ALIGNMENT CON LETRA MANUAL ===
        if not lang_code:
            # 1) Hacemos detección de idioma con un modelo pequeño (por ejemplo 'tiny')
            print("[WhisperX API] No se especificó language, autodetectando con un modelo pequeño ...")
            detect_model = whisperx.load_model("tiny", device=device, compute_type="float32")
            detect_result = detect_model.transcribe(audio_path, language=None)  # autodetect
            lang_code = detect_result["language"]
            print(f"[WhisperX API] Autodetectado => {lang_code}")

        print(f"[WhisperX API] Forced alignment con letra manual, lang={lang_code}")

        total_sec = get_duration(audio_path)
        # Simulamos segments con un único gran segmento [0..fin]
        result = {
            "language": lang_code,
            "segments": [
                {
                    "text": manual_lyrics,
                    "start": 0.0,
                    "end": total_sec
                }
            ]
        }

        # Cargamos el modelo de alineación
        align_model, metadata = whisperx.load_align_model(lang_code, device)
        result_aligned = whisperx.align(
            result["segments"], 
            align_model, 
            metadata, 
            audio_path, 
            device
        )

    else:
        # === TRANSCRIPCIÓN AUTOMÁTICA (como antes) ===
        model = whisperx.load_model("medium", device=device, compute_type="float32")
        result = model.transcribe(audio_path, language=None)  # autodetect
        lang_code = result["language"]
        print(f"[WhisperX API] Automatic transcription, detected lang={lang_code}")

        align_model, metadata = whisperx.load_align_model(lang_code, device)
        result_aligned = whisperx.align(
            result["segments"], 
            align_model, 
            metadata, 
            audio_path, 
            device
        )

    word_segments = result_aligned["word_segments"]

    # 3) Crear SRT final a nivel de palabra
    srt_path = audio_path.replace(".wav", "_whisperx.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        idx = 1
        for seg in word_segments:
            if "word" not in seg:
                continue
            text = seg["word"].strip()
            start= seg["start"]
            end  = seg["end"]
            block = f"{idx}\n{sec2tc(start)} --> {sec2tc(end)}\n{text}\n\n"
            f.write(block)
            idx+=1

    return jsonify({"srt_path": srt_path, "message": "Alignment done"}), 200


if __name__ == "__main__":
    # Levantamos en modo debug y en CPU
    app.run(host="0.0.0.0", port=5001, debug=True)
