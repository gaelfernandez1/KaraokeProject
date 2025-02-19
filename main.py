import argparse
import os
import subprocess
import shutil
import requests   # <--- Para llamar al endpoint en contenedor B
import math

from moviepy.editor import (
    AudioFileClip, VideoFileClip, CompositeAudioClip,
    TextClip, CompositeVideoClip
)
from moviepy.video.tools.subtitles import SubtitlesClip

from moviepy.config import change_settings
import platform

# ------------------------------------------------------------------------------------
# CONFIGURACIONES
# ------------------------------------------------------------------------------------
TRANSCRIPTION_MODEL = "medium" 
NUM_PASSES = 1
VOCAL_VOLUME = 0.05
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
TEXT_WIDTH = 1200
TEXT_COLOR = "#FFFFFF"
TEXT_STROKE_COLOR = "#000000"
TEXT_STROKE_WIDTH = 0.5
FONT_SIZE = 40
FONT = "./fonts/kg.ttf"

if platform.system() == "Darwin":
    imagemagick_path = "/opt/homebrew/bin/magick"
elif platform.system() == "Windows":
    imagemagick_path = "C:/Program Files/ImageMagick-7.1.1-Q16-HDRI/magick.exe"
elif platform.system() == "Linux":
    imagemagick_path = "/usr/bin/convert"
else:
    raise NotImplementedError("Unsupported operating system")

change_settings({"IMAGEMAGICK_BINARY": imagemagick_path})

# ------------------------------------------------------------------------------------
# FUNCIONES
# ------------------------------------------------------------------------------------

def video_to_mp3(video_path: str) -> str:
    from moviepy.editor import AudioFileClip
    print(f"Convirtiendo video a mp3 -> {video_path}")
    audio_path = video_path.replace(".mp4", ".mp3")
    if os.path.exists(audio_path):
        return audio_path

    audio = AudioFileClip(video_path)
    audio.write_audiofile(audio_path, logger="bar")
    print(f"Audio guardado en: {audio_path}")
    return audio_path

def separate_stems_cli(audio_file_path: str) -> tuple[str, str]:
    """
    Separa las pistas con Demucs CLI y retorna (vocals, instrumental).
    """
    demucs_output_dir = "./separated"
    if not os.path.exists("./stems"):
        os.makedirs("./stems")

    audio_filename = os.path.basename(audio_file_path)
    base_name = os.path.splitext(audio_filename)[0]

    print(f"Ejecutando Demucs para separar {audio_file_path}...")
    import subprocess
    try:
        subprocess.run(["demucs", audio_file_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar Demucs: {e}")
        return "", ""

    separated_folder = os.path.join(demucs_output_dir, "htdemucs", base_name)
    if not os.path.exists(separated_folder):
        print(f"No se encontró la carpeta de salida de Demucs: {separated_folder}")
        return "", ""

    vocals_wav = os.path.join(separated_folder, "vocals.wav")
    instrumental_wav = os.path.join(separated_folder, "no_vocals.wav")

    if not os.path.exists(instrumental_wav):
        drums_wav = os.path.join(separated_folder, "drums.wav")
        bass_wav = os.path.join(separated_folder, "bass.wav")
        other_wav = os.path.join(separated_folder, "other.wav")
        instrumental_wav = os.path.join(separated_folder, "music_instrumental.wav")

        if all(os.path.exists(p) for p in [drums_wav, bass_wav, other_wav]):
            print("Combinando pistas para crear la instrumental...")
            subprocess.run([
                "ffmpeg",
                "-i", drums_wav,
                "-i", bass_wav,
                "-i", other_wav,
                "-filter_complex", "[0:a][1:a][2:a]amix=inputs=3:normalize=0",
                instrumental_wav
            ], check=True)
        else:
            print("Faltan archivos stems para instrumental.")
            return "", ""

    if not os.path.exists(vocals_wav) or not os.path.exists(instrumental_wav):
        print("No se encontraron los WAVs resultantes.")
        return "", ""

    final_vocals_path = f"/data/vocals_{base_name}.wav"
    final_music_path  = f"/data/music_{base_name}.wav"


    shutil.move(vocals_wav, final_vocals_path)
    shutil.move(instrumental_wav, final_music_path)

    print(f"Pistas separadas: {final_vocals_path}, {final_music_path}")
    return final_vocals_path, final_music_path

def seconds_to_timecode(sec):
    total_ms = int(math.floor(sec*1000))
    hh = total_ms // 3600000
    mm = (total_ms % 3600000)//60000
    ss = ((total_ms %60000)//1000)
    ms = (total_ms % 1000)
    return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"

def call_whisperx_endpoint(vocals_path: str):
    """
    Llama al endpoint del contenedor B (whisperx) enviando JSON: {audio_path: vocals_path}
    Asume que en docker-compose, el servicio se llama 'whisperx' y expone el puerto 5001.
    """
    url = "http://whisperx:5001/align"  # dentro de la red docker
    payload = {"audio_path": vocals_path}
    try:
        resp = requests.post(url, json=payload, timeout=600)
        if resp.status_code == 200:
            data = resp.json()
            print("[Contenedor A] WhisperX alignment OK:", data)
        else:
            print("[Contenedor A] WhisperX alignment Error:", resp.text)
    except Exception as e:
        print(f"[Contenedor A] Error llamando a whisperx endpoint: {e}")

def create(video_path: str):
    """
    Crea un karaoke con forced alignment:
      1) Separa con demucs => vocals.wav
      2) Llama al endpoint contenedor B => genera .srt
      3) Compone el video final con moviepy
    """
    audio_path = video_to_mp3(video_path)
    vocals_path, music_path = separate_stems_cli(audio_path)
    if not vocals_path or not music_path:
        return ""

    # 2) Llamamos a WhisperX (contenedor B) => produce srt
    call_whisperx_endpoint(vocals_path)
    # Por convención, whisperx generará vocals_whisperx.srt
    srt_file = vocals_path.replace(".wav","_whisperx.srt")
    if not os.path.exists(srt_file):
        print("No se encontró el srt, algo falló con contenedor B")
        return ""

    # 3) Componer con moviepy
    music = AudioFileClip(music_path).set_fps(44100)
    vocals = AudioFileClip(vocals_path).volumex(VOCAL_VOLUME).set_fps(44100)
    combined = CompositeAudioClip([music, vocals])

    background = VideoFileClip(video_path, target_resolution=(VIDEO_WIDTH, VIDEO_HEIGHT)
                   ).set_duration(combined.duration).set_fps(30)

    dimmed = background.fl_image(lambda img: (img*0.3).astype("uint8"))

    def generator(txt):
        return TextClip(txt, font=FONT, fontsize=FONT_SIZE,
                        color=TEXT_COLOR, stroke_color=TEXT_STROKE_COLOR,
                        stroke_width=TEXT_STROKE_WIDTH, size=(TEXT_WIDTH, None),
                        method='pango')

    subtitles = SubtitlesClip(srt_file, generator)
    final = CompositeVideoClip([
        dimmed,
        subtitles.set_position(('center','center'), relative=True)
    ]).set_audio(combined)

    filename = f"karaoke_{os.path.basename(video_path)}"
    if not os.path.exists("./output"):
        os.makedirs("./output")

    out_path = os.path.join("./output", filename)
    final.write_videofile(out_path, fps=30, threads=4)
    return filename

def create_with_manual_lyrics(video_path: str, manual_lyrics: str) -> str:
    """
    Variante manual sin whisperx
    """
    import re
    audio_path = video_to_mp3(video_path)
    vocals_path, music_path = separate_stems_cli(audio_path)
    if not vocals_path or not music_path:
        return ""

    combined = CompositeAudioClip([
        AudioFileClip(music_path).set_fps(44100),
        AudioFileClip(vocals_path).volumex(VOCAL_VOLUME).set_fps(44100)
    ])

    background = VideoFileClip(video_path, target_resolution=(VIDEO_WIDTH, VIDEO_HEIGHT)
                  ).set_duration(combined.duration).set_fps(30)

    dimmed = background.fl_image(lambda img: (img*0.3).astype("uint8"))

    start_sec = 2
    end_sec = int(combined.duration)

    def s_to_tc(s):
        h = s // 3600
        m = (s%3600)//60
        sec = s%60
        return f"{h:02}:{m:02}:{sec:02},000"

    safe_lyrics = re.sub(r"\[.*?\]", "", manual_lyrics)
    safe_lyrics = safe_lyrics.replace('\r','')
    while '\n\n\n' in safe_lyrics:
        safe_lyrics = safe_lyrics.replace('\n\n\n','\n\n')

    paragraphs = safe_lyrics.strip().split('\n\n')
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        paragraphs = [safe_lyrics]

    total_paragraphs = len(paragraphs)
    total_time = end_sec - start_sec
    if total_time < 1:
        total_time = 1

    time_per_par = total_time / total_paragraphs

    srt_lines = []
    current_start = start_sec
    idx=1
    for p in paragraphs:
        start_tc = s_to_tc(int(current_start))
        end_p = current_start + time_per_par
        end_tc = s_to_tc(int(end_p))
        block = f"""{idx}
{start_tc} --> {end_tc}
{p}

"""
        srt_lines.append(block)
        current_start = end_p
        idx+=1

    if not os.path.exists("./subtitles"):
        os.makedirs("./subtitles")

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    srt_file = os.path.join("./subtitles", f"manual_{base_name}.srt")
    with open(srt_file,"w",encoding="utf-8") as f:
        f.write("".join(srt_lines))

    def generator(txt):
        return TextClip(txt, font=FONT, fontsize=FONT_SIZE,
                        color="#FFFFFF", stroke_color="#000000", stroke_width=0.5,
                        size=(TEXT_WIDTH, None), method='pango')

    subtitles = SubtitlesClip(srt_file, generator)
    final = CompositeVideoClip([
        dimmed,
        subtitles.set_position(("center","center"), relative=True)
    ]).set_audio(combined)

    filename = f"karaoke_manual_{os.path.basename(video_path)}"
    if not os.path.exists("./output"):
        os.makedirs("./output")

    out_path = os.path.join("./output", filename)
    final.write_videofile(out_path, fps=30, threads=4)
    return filename

def parse_arguments():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("video_path", help="ruta del video")
    return parser.parse_args()

def main():
    args = parse_arguments()
    print(f"Creando karaoke para: {args.video_path}")
    create(args.video_path)

if __name__ == "__main__":
    main()
