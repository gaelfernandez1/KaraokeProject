from flask import Flask, request, jsonify
import torch
import whisperx
import math
import os

app = Flask(__name__)

def sec2tc(sec_float):
    ms = int(math.floor(sec_float*1000))
    hh = ms//3600000
    mm = (ms%3600000)//60000
    ss = (ms%60000)//1000
    mmm= (ms%1000)
    return f"{hh:02}:{mm:02}:{ss:02},{mmm:03}"

@app.route("/align", methods=["POST"])
def align_endpoint():
    """
    Espera un JSON como: { "audio_path": "/data/vocals.wav" }
    Genera /data/vocals_whisperx.srt y responde un JSON con la ruta del SRT.
    """
    data = request.get_json()
    if not data or "audio_path" not in data:
        return jsonify({"error": "Missing 'audio_path'"}), 400

    audio_path = data["audio_path"]
    if not os.path.exists(audio_path):
        return jsonify({"error": f"File {audio_path} not found"}), 404

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[WhisperX API] Using device={device}, audio={audio_path}")

    # 1) Cargar modelo principal
    model = whisperx.load_model("medium", device=device, compute_type="float32")
    result = model.transcribe(audio_path, language=None)  # autodetect language
    lang_code = result["language"]

    # 2) Forced alignment con pyannote.audio
    align_model, metadata = whisperx.load_align_model(lang_code, device)
    result_aligned = whisperx.align(result["segments"], align_model, metadata, audio_path, device)
    word_segments = result_aligned["word_segments"]

    # 3) Crear SRT final
    srt_path = audio_path.replace(".wav", "_whisperx.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        idx = 1
        for seg in word_segments:
            if "word" not in seg:
                print(f"[DEBUG] Segment sin 'word': {seg}")
                continue
            text = seg["word"].strip()
            start= seg["start"]
            end  = seg["end"]
            block = f"{idx}\n{sec2tc(start)} --> {sec2tc(end)}\n{text}\n\n"
            f.write(block)
            idx+=1

    return jsonify({"srt_path": srt_path, "message": "Alignment done"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
