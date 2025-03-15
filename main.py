import argparse
import os
import subprocess
import shutil
import requests
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
    print(f"[video_to_mp3] Convirtiendo video a mp3 => {video_path}")
    audio_path = video_path.replace(".mp4", ".mp3")
    if os.path.exists(audio_path):
        print(f"[video_to_mp3] El mp3 ya existía: {audio_path}")
        return audio_path

    try:
        audio = AudioFileClip(video_path)
        audio.write_audiofile(audio_path, logger="bar")
        print(f"[video_to_mp3] Audio guardado en: {audio_path}")
    except Exception as e:
        print(f"[video_to_mp3] ERROR al convertir video a mp3: {e}")
        return ""

    return audio_path

def separate_stems_cli(audio_file_path: str) -> tuple[str, str]:
    """
    Separa las pistas con Demucs CLI y retorna (vocals, instrumental).
    """
    print(f"[separate_stems_cli] Iniciando demucs para: {audio_file_path}")
    demucs_output_dir = "./separated"
    if not os.path.exists("./stems"):
        os.makedirs("./stems")

    audio_filename = os.path.basename(audio_file_path)
    base_name = os.path.splitext(audio_filename)[0]

    print(f"[separate_stems_cli] Llamando demucs CLI para {audio_file_path} ...")
    try:
        subprocess.run(["demucs", audio_file_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[separate_stems_cli] Error al ejecutar Demucs: {e}")
        return "", ""

    separated_folder = os.path.join(demucs_output_dir, "htdemucs", base_name)
    if not os.path.exists(separated_folder):
        print(f"[separate_stems_cli] No se encontró la carpeta de salida: {separated_folder}")
        return "", ""

    vocals_wav = os.path.join(separated_folder, "vocals.wav")
    instrumental_wav = os.path.join(separated_folder, "no_vocals.wav")

    if not os.path.exists(instrumental_wav):
        # Buscamos drums, bass, other
        drums_wav = os.path.join(separated_folder, "drums.wav")
        bass_wav = os.path.join(separated_folder, "bass.wav")
        other_wav = os.path.join(separated_folder, "other.wav")
        instrumental_wav = os.path.join(separated_folder, "music_instrumental.wav")

        if all(os.path.exists(p) for p in [drums_wav, bass_wav, other_wav]):
            print("[separate_stems_cli] Combinando drums+bass+other en instrumental.")
            try:
                subprocess.run([
                    "ffmpeg",
                    "-i", drums_wav,
                    "-i", bass_wav,
                    "-i", other_wav,
                    "-filter_complex", "[0:a][1:a][2:a]amix=inputs=3",
                    instrumental_wav
                ], check=True)
            except subprocess.CalledProcessError as e:
                print(f"[separate_stems_cli] Error al combinar stems: {e}")
                return "", ""
        else:
            print("[separate_stems_cli] Faltan drums/bass/other. No se pudo crear instrumental.")
            return "", ""

    if not os.path.exists(vocals_wav) or not os.path.exists(instrumental_wav):
        print("[separate_stems_cli] No se encontraron los WAVs resultantes (vocals o instrumental).")
        return "", ""

    final_vocals_path = f"/data/vocals_{base_name}.wav"
    final_music_path  = f"/data/music_{base_name}.wav"

    try:
        shutil.move(vocals_wav, final_vocals_path)
        shutil.move(instrumental_wav, final_music_path)
    except Exception as e:
        print(f"[separate_stems_cli] Error al mover stems a /data: {e}")
        return "", ""

    print(f"[separate_stems_cli] Pistas separadas => VOCALS: {final_vocals_path}, INSTR: {final_music_path}")
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
    => Transcripción automática.
    """
    url = "http://whisperx:5001/align"  # dentro de la red docker
    payload = {"audio_path": vocals_path}
    print(f"[call_whisperx_endpoint] Haciendo POST a {url} con audio_path={vocals_path}")
    try:
        resp = requests.post(url, json=payload, timeout=600)
        if resp.status_code == 200:
            data = resp.json()
            print("[call_whisperx_endpoint] WhisperX alignment OK:", data)
        else:
            print("[call_whisperx_endpoint] WhisperX alignment Error:", resp.text)
    except Exception as e:
        print(f"[call_whisperx_endpoint] EXCEPTION al llamar endpoint: {e}")

def call_whisperx_endpoint_manual(vocals_path: str, manual_lyrics: str, language="es"):
    """
    Llama al endpoint del contenedor B para forced alignment con 'manual_lyrics'.
    """
    url = "http://whisperx:5001/align"
    payload = {
        "audio_path": vocals_path,
        "manual_lyrics": manual_lyrics,
        "language": language
    }
    print(f"[call_whisperx_endpoint_manual] POST => {url}\n  audio_path={vocals_path}\n  manual_lyrics={manual_lyrics[:50]}...\n  lang={language}")
    try:
        resp = requests.post(url, json=payload, timeout=600)
        if resp.status_code == 200:
            data = resp.json()
            print("[call_whisperx_endpoint_manual] WhisperX forced alignment OK:", data)
        else:
            print("[call_whisperx_endpoint_manual] WhisperX forced alignment Error:", resp.text)
    except Exception as e:
        print(f"[call_whisperx_endpoint_manual] EXCEPTION: {e}")


def create(video_path: str):
    """
    Crea un karaoke con transcripción automática (WhisperX):
      1) Separa con demucs => vocals.wav
      2) Llama al endpoint contenedor B => genera .srt
      3) Compone el video final con moviepy
    """
    print(f"[create] Recibimos video_path={video_path}")
    audio_path = video_to_mp3(video_path)
    print(f"[create] audio_path => {audio_path}")
    if not audio_path:
        print("[create] audio_path está vacío => devolviendo ''")
        return ""

    vocals_path, music_path = separate_stems_cli(audio_path)
    print(f"[create] separate_stems_cli => vocals={vocals_path}, instrumental={music_path}")
    if not vocals_path or not music_path:
        print("[create] No hay vocals o music => devolviendo ''")
        return ""

    # 2) Llamamos a WhisperX => produce srt
    call_whisperx_endpoint(vocals_path)
    srt_file = vocals_path.replace(".wav","_whisperx.srt")
    print(f"[create] Esperamos SRT => {srt_file}")
    if not os.path.exists(srt_file):
        print("[create] SRT no existe => devolviendo ''")
        return ""

    # 3) Componer con moviepy
    print("[create] Componemos audio+video final ...")
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
    print(f"[create] Escribiendo videofile => {out_path}")
    final.write_videofile(out_path, fps=30, threads=4)
    print(f"[create] Terminamos => {filename}")
    return filename


def create_with_manual_lyrics(video_path: str, manual_lyrics: str, language="es") -> str:
    """
    Variante MANUAL que usa WhisperX en modo forced alignment:
      1) Separa con demucs => vocals.wav
      2) Llamada a WhisperX indicando la letra manual => genera srt
      3) Creamos el video con la letra forzada
    """
    print(f"[create_with_manual_lyrics] video={video_path}, language={language}")
    audio_path = video_to_mp3(video_path)
    print(f"[create_with_manual_lyrics] audio_path => {audio_path}")
    if not audio_path:
        print("[create_with_manual_lyrics] audio_path vacío => return ''")
        return ""

    vocals_path, music_path = separate_stems_cli(audio_path)
    print(f"[create_with_manual_lyrics] => vocals={vocals_path}, music={music_path}")
    if not vocals_path or not music_path:
        print("[create_with_manual_lyrics] Falta vocals o music => return ''")
        return ""

    # 2) Llamar a WhisperX contenedor B, pero con 'manual_lyrics'
    call_whisperx_endpoint_manual(vocals_path, manual_lyrics, language)
    srt_file = vocals_path.replace(".wav","_whisperx.srt")
    print(f"[create_with_manual_lyrics] srt esperado => {srt_file}")
    if not os.path.exists(srt_file):
        print("[create_with_manual_lyrics] SRT no encontrado => return ''")
        return ""

    # (AQUI) Llamamos a la función para unificar las líneas del SRT en una sola por bloque
    unify_srt_lines(srt_file)

    # (Opcional) Imprimir el contenido unificado para debug
    print("[DEBUG] SRT unificado =>")
    with open(srt_file, "r", encoding="utf-8") as dbg:
        print(dbg.read())

    # 3) Componer con moviepy
    print("[create_with_manual_lyrics] Componiendo audio+video con forced alignment")
    combined = CompositeAudioClip([
        AudioFileClip(music_path).set_fps(44100),
        AudioFileClip(vocals_path).volumex(VOCAL_VOLUME).set_fps(44100)
    ])

    # (Opcional) Si quieres envolver la creación de VideoFileClip en try/except también:
    # try:
    background = VideoFileClip(video_path, target_resolution=(VIDEO_WIDTH, VIDEO_HEIGHT)
                  ).set_duration(combined.duration).set_fps(30)
    # except Exception as ee:
    #     print(f"[create_with_manual_lyrics] VideoFileClip error => {ee}")
    #     return ""

    dimmed = background.fl_image(lambda img: (img*0.3).astype("uint8"))

    def generator(txt):
        return TextClip(txt, font=FONT, fontsize=FONT_SIZE,
                        color=TEXT_COLOR, stroke_color=TEXT_STROKE_COLOR,
                        stroke_width=TEXT_STROKE_WIDTH,
                        size=(TEXT_WIDTH, None), method='pango')

    try:
        subtitles = SubtitlesClip(srt_file, generator)
    except Exception as e:
        print(f"[create_with_manual_lyrics] SubtitlesClip error => {e}")
        return ""

    final = CompositeVideoClip([
        dimmed,
        subtitles.set_position(("center","center"), relative=True)
    ]).set_audio(combined)

    filename = f"karaoke_manual_{os.path.basename(video_path)}"
    if not os.path.exists("./output"):
        os.makedirs("./output")

    out_path = os.path.join("./output", filename)
    print(f"[create_with_manual_lyrics] Generando videofile => {out_path}")
    try:
        final.write_videofile(out_path, fps=30, threads=4)
    except Exception as e:
        print(f"[create_with_manual_lyrics] write_videofile error => {e}")
        return ""
    print(f"[create_with_manual_lyrics] Final => {filename}")
    return filename




def unify_srt_lines(srt_file: str):
    """
    Lee el archivo SRT y para cada bloque:
      - Índice
      - Línea de tiempo
      - Varias líneas de texto
      - Línea en blanco (fin de bloque)

    Combina todas las líneas de texto en una sola.

    Sobrescribe el archivo SRT final con el texto unificado por bloque.
    """
    import os

    if not os.path.exists(srt_file):
        print(f"[unify_srt_lines] No existe {srt_file}, no se hace post-procesado.")
        return

    with open(srt_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].rstrip("\n")
        # 1) Bloque: índice (ej. "10")
        if line.isdigit():
            # Copiamos el índice tal cual y saltamos
            new_lines.append(line + "\n")
            i += 1

            # 2) Esperamos la línea de tiempo (ej. "00:00:17,982 --> 00:00:18,742")
            if i < n and "-->" in lines[i]:
                new_lines.append(lines[i])  # copiamos la línea tal cual
                i += 1

                # 3) Acumulamos todas las líneas de texto hasta la línea en blanco o EOF
                text_accumulator = []
                while i < n and lines[i].strip() != "":
                    text_accumulator.append(lines[i].strip("\n"))
                    i += 1

                # Unificamos en una sola línea
                full_text = " ".join(text_accumulator)
                # escribimos la línea de texto unificada
                new_lines.append(full_text + "\n\n")

                # saltamos la línea en blanco (si existe)
                i += 1

            else:
                # si no hay línea de tiempo, simplemente avanzamos
                i += 1

        else:
            # no es un dígito => puede ser ruido, avanzamos
            i += 1

    # Sobrescribimos el archivo resultante
    with open(srt_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"[unify_srt_lines] Se ha reescrito el SRT unificando líneas: {srt_file}")



def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("video_path", help="ruta del video")
    return parser.parse_args()

def main():
    args = parse_arguments()
    print(f"[main] Creando karaoke para: {args.video_path}")
    res = create(args.video_path)
    print(f"[main] Resultado => {res}")

if __name__ == "__main__":
    main()
