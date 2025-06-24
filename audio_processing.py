import os
import subprocess
import shutil
import requests
from moviepy.editor import AudioFileClip

#Para convertir un video a un mp3 
def video_to_mp3(video_path: str) -> str:

    print(f"Convertindo video a mp3 => {video_path}")
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


#Funcion para usar demucs, separa as pistas de audio. Esto devolve a ruta da voz e a ruta da instrumental
def separate_stems_cli(audio_file_path: str) -> tuple[str, str]:

    print(f" Iniciando proceso demucs para: {audio_file_path}")
    directorio_saida = "./separated"
    if not os.path.exists("./stems"):
        os.makedirs("./stems")

    nombreArchivo = os.path.basename(audio_file_path)
    nombreBase = os.path.splitext(nombreArchivo)[0]

    try:
        subprocess.run(["demucs", "--device", "cuda", audio_file_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error de demucs {e}")
        return "", ""

    carpetaSeparado = os.path.join(directorio_saida, "htdemucs", nombreBase)       #chamase htdemucs desde unha das actualizacions. Importante
    if not os.path.exists(carpetaSeparado):   #Si non se encontrou a carpeta de salida
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
                    "ffmpeg",
                    "-i", drums_wav,
                    "-i", bass_wav,
                    "-i", other_wav,
                    "-filter_complex", "[0:a][1:a][2:a]amix=inputs=3",
                    instrumental_wav
                ], check=True)
            except subprocess.CalledProcessError as e:      #error ao combinar as partes
                return "", ""
        else:   #se falta algunha das partes damos error
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
def call_whisperx_endpoint(vocals_path: str):
    url = "http://whisperx:5001/align"              #dentro da red docker
    datos_envio = {"audio_path": vocals_path}
    #Facemos post
    try:
        resposta = requests.post(url, json=datos_envio, timeout=600)
        if resposta.status_code == 200:
            datos = resposta.json()
        else:
            print("WhisperX alignment Error:", resposta.text)
    except Exception as e:
        print(f"error ao chamar ao endpoint: {e}")


#Esto chama ao endpoint pero da letra manual
def call_whisperx_endpoint_manual(vocals_path: str, manual_lyrics: str, language="es"):
    url = "http://whisperx:5001/align"
    datos_envio = {
        "audio_path": vocals_path,
        "manual_lyrics": manual_lyrics,
        "language": language
    }
    try:
        resposta = requests.post(url, json=datos_envio, timeout=600)
        if resposta.status_code == 200:
            datos = resposta.json()
        else:
            print("Fallo do alineamento forzado:", resposta.text)
    except Exception as e:
        print(f"error co endpoint da letra manual {e}")
