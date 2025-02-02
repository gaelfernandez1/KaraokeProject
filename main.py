import argparse
import os
import subprocess
import shutil

import torch
import whisper
from moviepy.editor import *
from moviepy.video.tools.subtitles import SubtitlesClip

from moviepy.config import change_settings
from whisper.utils import get_writer
import platform


# Configuraciones
TRANSCRIPTION_MODEL = "medium.en"
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

# Configurar ImageMagick
if platform.system() == "Darwin":
    imagemagick_path = "/opt/homebrew/bin/magick"
elif platform.system() == "Windows":
    imagemagick_path = "C:/Program Files/ImageMagick-7.1.1-Q16-HDRI/magick.exe"
else:
    raise NotImplementedError("Unsupported operating system")

change_settings({"IMAGEMAGICK_BINARY": imagemagick_path})

def video_to_mp3(video_path: str) -> str:
    """Convierte un archivo de video a MP3."""
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
    Separa las pistas de vocales y música de un archivo de audio utilizando Demucs CLI.
    """
    demucs_output_dir = "./separated"
    
    if not os.path.exists("./stems"):
        os.makedirs("./stems")
    
    audio_filename = os.path.basename(audio_file_path)
    base_name = os.path.splitext(audio_filename)[0]
    
    print(f"Ejecutando Demucs para separar {audio_file_path}...")
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
            print("Combinando pistas de Demucs para crear la pista instrumental...")
            subprocess.run([
                "ffmpeg",
                "-i", drums_wav,
                "-i", bass_wav,
                "-i", other_wav,
                "-filter_complex", "[0:a][1:a][2:a]amix=inputs=3:normalize=0",
                instrumental_wav
            ], check=True)
        else:
            print("Faltan archivos de stems para crear la pista instrumental.")
            return "", ""
    
    if not os.path.exists(vocals_wav):
        print(f"No se encontró la pista de vocales: {vocals_wav}")
        return "", ""
    
    if not os.path.exists(instrumental_wav):
        print(f"No se encontró la pista instrumental: {instrumental_wav}")
        return "", ""
    
    final_vocals_path = f"./stems/vocals_{base_name}.wav"
    final_music_path = f"./stems/music_{base_name}.wav"
    
    shutil.move(vocals_wav, final_vocals_path)
    shutil.move(instrumental_wav, final_music_path)
    
    print(f"Pistas separadas guardadas en 'stems/':\n- Vocales: {final_vocals_path}\n- Música: {final_music_path}")
    
    return final_vocals_path, final_music_path

def transcribe(audiofile_path: str, num_passes: int = 1) -> str:
    """
    Convierte un archivo MP3 en una transcripción usando Whisper.
    """
    try:
        subtitle_path = os.path.join("./subtitles",
                                     os.path.splitext(os.path.basename(audiofile_path))[0] + '.srt')

        if os.path.exists(subtitle_path):
            return subtitle_path

        if not os.path.exists("./subtitles"):
            os.makedirs("./subtitles")

        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Usando dispositivo: {device}")
        model = whisper.load_model(TRANSCRIPTION_MODEL).to(device)

        last_result = None
        for i in range(num_passes):
            print(f"Transcripción pasada {i + 1} de {num_passes}...")
            current_result = model.transcribe(
                audiofile_path, verbose=True, word_timestamps=True)
            last_result = current_result

        if last_result is None:
            raise ValueError("No se obtuvieron resultados de transcripción.")

        srt_writer = get_writer("srt", "./subtitles")
        srt_writer(last_result, audiofile_path, highlight_words=True)

        return subtitle_path

    except Exception as e:
        print(f"Error al convertir MP3 a transcripción: {e}")
        return ""

def create(video_path: str):
    """
    Crea un video de karaoke a partir de las pistas de audio separadas y el video original,
    usando Whisper para generar subtítulos.
    """
    audio_path = video_to_mp3(video_path)
    vocals_path, music_path = separate_stems_cli(audio_path)

    if not vocals_path or not music_path:
        print("No se pudieron obtener las pistas de vocales y música.")
        return ""

    music = AudioFileClip(music_path).set_fps(44100)
    vocals_audio = AudioFileClip(vocals_path).volumex(VOCAL_VOLUME).set_fps(44100)
    combined_audio = CompositeAudioClip([music, vocals_audio])

    background_video = VideoFileClip(video_path,
                     target_resolution=(VIDEO_WIDTH, VIDEO_HEIGHT)
                    ).set_fps(30).set_duration(combined_audio.duration)

    dimmed_background_video = background_video.fl_image(
        lambda image: (image * 0.3).astype("uint8")
    )

    # Generar subtítulos con Whisper
    subtitles_file = transcribe(vocals_path, NUM_PASSES)
    if not subtitles_file:
        print("No se pudo generar el archivo de subtítulos.")
        return ""

    def generator(txt):
        return TextClip(
            txt,
            font=FONT,
            fontsize=FONT_SIZE,
            color=TEXT_COLOR,
            stroke_color=TEXT_STROKE_COLOR,
            stroke_width=TEXT_STROKE_WIDTH,
            size=(TEXT_WIDTH, None),
            method='pango'
        )

    subtitles = SubtitlesClip(subtitles_file, generator)

    result = CompositeVideoClip([
        dimmed_background_video,
        subtitles.set_position(('center', 'center'), relative=True)
    ]).set_audio(combined_audio)

    filename = f"karaoke_{os.path.basename(video_path)}"
    if not os.path.exists("./output"):
        os.makedirs("./output")

    out_path = f"./output/{filename}"
    result.write_videofile(out_path, fps=30, threads=4)
    return filename





def create_with_manual_lyrics(video_path: str, manual_lyrics: str) -> str:
    """
    Variante de create(...) que en lugar de transcribir con Whisper,
    genera un archivo SRT con varios bloques (uno por párrafo).
    Así evita problemas con un único bloque muy grande.
    """

    # 1) Convertir video a mp3 y separar pistas
    audio_path = video_to_mp3(video_path)
    vocals_path, music_path = separate_stems_cli(audio_path)
    if not vocals_path or not music_path:
        print("No se pudieron obtener las pistas de vocales y música.")
        return ""

    # 2) Cargar y combinar pistas (igual que en create)
    music = AudioFileClip(music_path).set_fps(44100)
    vocals_audio = AudioFileClip(vocals_path).volumex(VOCAL_VOLUME).set_fps(44100)
    combined_audio = CompositeAudioClip([music, vocals_audio])

    background_video = VideoFileClip(
        video_path, target_resolution=(VIDEO_WIDTH, VIDEO_HEIGHT)
    ).set_fps(30).set_duration(combined_audio.duration)

    dimmed_background_video = background_video.fl_image(
        lambda image: (image * 0.3).astype("uint8")
    )

    # 3) Definir tiempo de inicio y fin para los subtítulos
    start_sec = 2
    end_sec = int(combined_audio.duration)

    # Pequeña función para formatear [segundos] en "hh:mm:ss,mmm"
    def seconds_to_timecode(total_seconds: int):
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h:02}:{m:02}:{s:02},000"

    # 4) LIMPIEZA DEL TEXTO:
    import re

    # a) Eliminar corchetes (por si MoviePy se lía con "[...]")
    safe_lyrics = re.sub(r"\[.*?\]", "", manual_lyrics)

    # b) Quitar \r (retorno de carro) y unificar saltos múltiples
    safe_lyrics = safe_lyrics.replace('\r', '')
    while '\n\n\n' in safe_lyrics:
        safe_lyrics = safe_lyrics.replace('\n\n\n', '\n\n')
    
    # c) Separar párrafos por doble salto de línea
    paragraphs = safe_lyrics.strip().split('\n\n')
    paragraphs = [p.strip() for p in paragraphs if p.strip()]  # quita vacíos

    # Si no hay párrafos, meter todo en uno
    if not paragraphs:
        paragraphs = [safe_lyrics]

    # 5) Repartir el tiempo entre los párrafos
    total_paragraphs = len(paragraphs)
    total_time = end_sec - start_sec
    if total_time <= 0:
        total_time = 1  # evitar divisiones por cero

    time_per_paragraph = total_time / total_paragraphs

    # 6) Construir el SRT con varios bloques
    srt_lines = []
    current_start = start_sec
    for idx, paragraph in enumerate(paragraphs, start=1):
        p_start_tc = seconds_to_timecode(int(current_start))
        p_end = current_start + time_per_paragraph
        p_end_tc = seconds_to_timecode(int(p_end))

        # Bloque SRT
        block = f"""{idx}
{p_start_tc} --> {p_end_tc}
{paragraph}

"""
        srt_lines.append(block)
        current_start = p_end

    srt_content = "".join(srt_lines)

    # 7) DEBUG: imprime el contenido final del SRT
    print("=== DEBUG: SRT Content ===")
    print(srt_content)
    print("=== END SRT Content ===")

    # 8) Guardar en un archivo .srt
    if not os.path.exists("./subtitles"):
        os.makedirs("./subtitles")

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    srt_file = os.path.join("./subtitles", f"manual_{base_name}.srt")
    with open(srt_file, "w", encoding="utf-8") as f:
        f.write(srt_content)

    # 9) Crear SubtitlesClip
    def generator(txt):
        return TextClip(
            txt,
            font=FONT,
            fontsize=FONT_SIZE,
            color=TEXT_COLOR,
            stroke_color=TEXT_STROKE_COLOR,
            stroke_width=TEXT_STROKE_WIDTH,
            size=(TEXT_WIDTH, None),
            method='pango'
        )

    subtitles = SubtitlesClip(srt_file, generator)

    # 10) Componer el video final
    result = CompositeVideoClip([
        dimmed_background_video,
        subtitles.set_position(('center', 'center'), relative=True)
    ]).set_audio(combined_audio)

    # 11) Guardar video
    filename = f"karaoke_manual_{os.path.basename(video_path)}"
    if not os.path.exists("./output"):
        os.makedirs("./output")

    out_path = f"./output/{filename}"
    result.write_videofile(out_path, fps=30, threads=4)
    return filename




def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Crear un video de karaoke a partir de un archivo de video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("video_path", help="Ruta al archivo de video.")
    return parser.parse_args()

def main():
    args = parse_arguments()
    video_path = args.video_path.replace("\\", "/")
    print(f"Creando video de karaoke para: {video_path}..")
    create(video_path)

if __name__ == "__main__":
    main()
