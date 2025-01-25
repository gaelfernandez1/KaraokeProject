import argparse
import os
import subprocess
import shutil

#import demucs.api  # Solo si usas la API; si no, puedes eliminar esta línea
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

    Args:
        audio_file_path (str): Ruta al archivo de audio (MP3).

    Returns:
        tuple[str, str]: Rutas a los archivos de vocales y música.
    """
    # Directorio de salida para Demucs
    demucs_output_dir = "./separated"
    
    # Asegurarse de que el directorio de stems exista
    if not os.path.exists("./stems"):
        os.makedirs("./stems")
    
    audio_filename = os.path.basename(audio_file_path)
    base_name = os.path.splitext(audio_filename)[0]
    
    # Ejecutar Demucs CLI
    print(f"Ejecutando Demucs para separar {audio_file_path}...")
    try:
        subprocess.run(["demucs", audio_file_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar Demucs: {e}")
        return "", ""
    
    # Ruta donde Demucs guarda las separaciones
    # Ajusta 'demucs' al nombre del modelo que estás usando si es diferente
    separated_folder = os.path.join(demucs_output_dir, "htdemucs", base_name)
    
    if not os.path.exists(separated_folder):
        print(f"No se encontró la carpeta de salida de Demucs: {separated_folder}")
        return "", ""
    
    # Rutas de los archivos separados
    vocals_wav = os.path.join(separated_folder, "vocals.wav")
    # Algunas versiones de Demucs generan 'no_vocals.wav'; si no, combinamos 'drums', 'bass' y 'other'
    instrumental_wav = os.path.join(separated_folder, "no_vocals.wav")
    
    if not os.path.exists(instrumental_wav):
        # Combinar manualmente 'drums.wav', 'bass.wav' y 'other.wav' usando ffmpeg
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
    
    # Verificar que las pistas existen
    if not os.path.exists(vocals_wav):
        print(f"No se encontró la pista de vocales: {vocals_wav}")
        return "", ""
    
    if not os.path.exists(instrumental_wav):
        print(f"No se encontró la pista instrumental: {instrumental_wav}")
        return "", ""
    
    # Opcional: Mover las pistas a la carpeta 'stems' para una mejor organización
    final_vocals_path = f"./stems/vocals_{base_name}.wav"
    final_music_path = f"./stems/music_{base_name}.wav"
    
    shutil.move(vocals_wav, final_vocals_path)
    shutil.move(instrumental_wav, final_music_path)
    
    print(f"Pistas separadas guardadas en 'stems/':\n- Vocales: {final_vocals_path}\n- Música: {final_music_path}")
    
    return final_vocals_path, final_music_path


def transcribe(audiofile_path: str, num_passes: int = 1) -> str:
    """
    Convierte un archivo MP3 en una transcripción usando Whisper.

    Args:
        audiofile_path (str): Ruta al archivo MP3 a procesar.
        num_passes (int): Número de pasadas de transcripción a realizar.

    Returns:
        str: Ruta al archivo SRT con la transcripción de la última pasada.
    """
    try:
        subtitle_path = os.path.join("./subtitles", os.path.splitext(
            os.path.basename(audiofile_path))[0] + '.srt')

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
                audiofile_path, verbose=True, language="en", word_timestamps=True)
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
    Crea un video de karaoke a partir de las pistas de audio separadas y el video original.

    Args:
        video_path (str): Ruta al archivo de video original.

    Returns:
        str: Nombre del archivo de karaoke creado.
    """
    audio_path = video_to_mp3(video_path)
    vocals_path, music_path = separate_stems_cli(audio_path)

    if not vocals_path or not music_path:
        print("No se pudieron obtener las pistas de vocales y música.")
        return ""

    # Cargar las pistas de audio
    music = AudioFileClip(music_path).set_fps(44100)
    vocals_audio = AudioFileClip(vocals_path).volumex(VOCAL_VOLUME).set_fps(44100)

    # Combinar las pistas de música y vocales
    combined_audio = CompositeAudioClip([music, vocals_audio])

    # Cargar y ajustar el video de fondo
    background_video = VideoFileClip(
        video_path, 
        target_resolution=(VIDEO_WIDTH, VIDEO_HEIGHT)
    ).set_fps(30).set_duration(combined_audio.duration)

    # Atenuar el video de fondo
    dimmed_background_video = background_video.fl_image(
        lambda image: (image * 0.3).astype("uint8")
    )

    # Generar el archivo de subtítulos
    subtitles_file = transcribe(vocals_path, NUM_PASSES)
    if not subtitles_file:
        print("No se pudo generar el archivo de subtítulos.")
        return ""

    # Definir la función generadora de subtítulos
    def generator(txt):
        """
        Genera los subtítulos para el video de karaoke.

        Args:
            txt (str): El texto que se añadirá a los subtítulos.

        Returns:
            TextClip: El clip de texto de los subtítulos.
        """
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

    # Crear los subtítulos
    subtitles = SubtitlesClip(subtitles_file, generator)

    # Componer el video final
    result = CompositeVideoClip([
        dimmed_background_video,
        subtitles.set_position(('center', 'center'), relative=True)
    ]).set_audio(combined_audio)

    # Definir el nombre del archivo de salida
    filename = f"karaoke_{os.path.basename(video_path)}"
    if not os.path.exists("./output"):
        os.makedirs("./output")
    
    # Exportar el video de karaoke
    result.write_videofile(f"./output/{filename}", fps=30, threads=4)

    return filename


def parse_arguments():
    """
    Analiza los argumentos de la línea de comandos.

    Returns:
        argparse.Namespace: Objeto con los argumentos analizados.
    """
    parser = argparse.ArgumentParser(
        description="Crear un video de karaoke a partir de un archivo de video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "video_path", help="Ruta al archivo de video."
    )

    return parser.parse_args()


def main():
    """
    Función principal del script.
    """
    args = parse_arguments()
    video_path = args.video_path.replace("\\", "/")

    print(f"Creando video de karaoke para: {video_path}..")

    create(video_path)


if __name__ == "__main__":
    main()
