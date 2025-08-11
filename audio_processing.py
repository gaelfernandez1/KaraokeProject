import os
import subprocess
import shutil
import requests
from moviepy.editor import AudioFileClip
from gpu_utils import detect_gpu_capability, get_optimal_demucs_args

#añador esto para detectas as capacidades da gpu en general, non solo do meu equipo
GPU_INFO = detect_gpu_capability()
DEMUCS_ARGS = get_optimal_demucs_args(GPU_INFO)

def video_to_mp3(video_path: str) -> str:

    
    if video_path.lower().endswith('.mp3'):
        if os.path.exists(video_path):
            return video_path
        else:
            print(f"Archivo MP3 non encontrado: {video_path}")
            return ""
    
    ruta_audio = video_path.replace(".mp4", ".mp3")
    if os.path.exists(ruta_audio):
        return ruta_audio

    try:
        clip_audio = AudioFileClip(video_path)
        clip_audio.write_audiofile(ruta_audio, logger="bar")
    except Exception as e:
        print(f" error ao convertir video a mp3: {e}")
        return ""

    return ruta_audio


#Funcion para usar demucs, separa as pistas de audio. Esto devolve a ruta da voz e a ruta da instrumental. ahora detecta a gpu automaticamente
def separate_stems_cli(audio_file_path: str) -> tuple[str, str]:


    if GPU_INFO['has_cuda']:
        print(f"GPU detectada: {GPU_INFO['gpu_name']} ({GPU_INFO['gpu_memory']:.1f}GB)")
    
    directorio_saida = "./separated"
    if not os.path.exists("./stems"):
        os.makedirs("./stems")

    nombreArchivo = os.path.basename(audio_file_path)
    nombreBase = os.path.splitext(nombreArchivo)[0]

    cmd = ["demucs"] + DEMUCS_ARGS + [audio_file_path]
    #print(f"Comando demucs: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("separaronse os stems sin problemas")
    except subprocess.CalledProcessError as e:
        print(f"Stderr: {e.stderr}")
        
        if GPU_INFO['recommended_device'] == 'cuda':
            print("problemas con gpu, vaise seguir con cpu")
            try:
                cmd_cpu = ["demucs", "--device", "cpu", "--two-stems=vocals", "--jobs", "2", audio_file_path]
                result = subprocess.run(cmd_cpu, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e2:
                print(f"error tamen con cpu: {e2}")
                return "", ""
        else:
            return "", ""

    carpetaSeparado = os.path.join(directorio_saida, "htdemucs", nombreBase)
    if not os.path.exists(carpetaSeparado):
        return "", ""

    vocals_wav = os.path.join(carpetaSeparado, "vocals.wav")
    instrumental_wav = os.path.join(carpetaSeparado, "no_vocals.wav")

    if not os.path.exists(instrumental_wav):
        drums_wav = os.path.join(carpetaSeparado, "drums.wav")
        bass_wav = os.path.join(carpetaSeparado, "bass.wav")
        other_wav = os.path.join(carpetaSeparado, "other.wav")
        instrumental_wav = os.path.join(carpetaSeparado, "music_instrumental.wav")

        #hai que combinar os stems de drums, bass e other para crear a instrumental porque demucs non o fai automaticamente
        if all(os.path.exists(p) for p in [drums_wav, bass_wav, other_wav]):
            try:
                subprocess.run([
                    "ffmpeg", "-y",  
                    "-i", drums_wav,
                    "-i", bass_wav,
                    "-i", other_wav,
                    "-filter_complex", "[0:a][1:a][2:a]amix=inputs=3",
                    instrumental_wav
                ], check=True)
            except subprocess.CalledProcessError as e:
                return "", ""
        else:
            print("Falta algun dos stems?")
            return "", ""

    if not os.path.exists(vocals_wav) or not os.path.exists(instrumental_wav):
        return "", ""

    ruta_final_vocals = f"/data/vocals_{nombreBase}.wav"
    ruta_final_musica = f"/data/music_{nombreBase}.wav"

    try:
        shutil.move(vocals_wav, ruta_final_vocals)
        shutil.move(instrumental_wav, ruta_final_musica)
    except Exception as e:
        return "", ""

    return ruta_final_vocals, ruta_final_musica


# Esto chama ao endpoint de  whisperx para facer a transcripción automatica
def call_whisperx_endpoint(vocals_path: str, enable_diarization: bool = False, hf_token: str = None):
    url = "http://whisperx:5001/align"              #dentro da red docker
    datos_envio = {
        "audio_path": vocals_path,
        "enable_diarization": enable_diarization
    }
    
    # Agregar token de HuggingFace
    if hf_token:
        datos_envio["hf_token"] = hf_token
    
    #Facemos post
    try:
        resposta = requests.post(url, json=datos_envio, timeout=600)
        if resposta.status_code == 200:
            datos = resposta.json()
            return datos  # Devolver datos para acceder a speaker_info
        else:
            print("WhisperX alignment Error:", resposta.text)
            return None
    except Exception as e:
        print(f"error ao chamar ao endpoint: {e}")
        return None


#Esto chama ao endpoint pero da letra manual
def call_whisperx_endpoint_manual(vocals_path: str, manual_lyrics: str, language=None, enable_diarization: bool = False, hf_token: str = None):
    url = "http://whisperx:5001/align"
    datos_envio = {
        "audio_path": vocals_path,
        "manual_lyrics": manual_lyrics,
        "enable_diarization": enable_diarization
    }
    
    # Solo añadir language si se especifica, si non WhisperX detectará automáticamente
    if language:
        datos_envio["language"] = language
    
   
    if hf_token:
        datos_envio["hf_token"] = hf_token
    
    try:
        resposta = requests.post(url, json=datos_envio, timeout=600)
        if resposta.status_code == 200:
            datos = resposta.json()
            return datos  
        else:
            print("Fallo do alineamento forzado:", resposta.text)
            return None
    except Exception as e:
        print(f"error co endpoint da letra manual {e}")
        return None
