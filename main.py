import argparse
import os
import subprocess
import shutil
import requests
import math
import glob
import platform
import numpy as np
import re

from moviepy.editor import (
    AudioFileClip, VideoFileClip, CompositeAudioClip,
    CompositeVideoClip, VideoClip
)
from moviepy.config import change_settings

# IMPORTANTE: Asegúrate de tener instalada la librería Pillow
from PIL import Image, ImageDraw, ImageFont

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
HIGHLIGHT_COLOR = "#FFFF00"  # por ejemplo amarillo para resaltar
TEXT_STROKE_COLOR = "#000000"
TEXT_STROKE_WIDTH = 1
FONT_SIZE = 40
FONT = "./fonts/kg.ttf"
MARGIN = 40
TEXT_CLIP_WIDTH = VIDEO_WIDTH - 2 * MARGIN  # Esto te da 1200

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
# FUNCIONES EXISTENTES (video_to_mp3, separate_stems_cli, call_whisperx_endpoint, etc.)
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
    print(f"[separate_stems_cli] Iniciando demucs para: {audio_file_path}")
    demucs_output_dir = "./separated"
    if not os.path.exists("./stems"):
        os.makedirs("./stems")

    audio_filename = os.path.basename(audio_file_path)
    base_name = os.path.splitext(audio_filename)[0]

    print(f"[separate_stems_cli] Llamando demucs CLI para {audio_file_path} ...")
    try:
        subprocess.run(["demucs", "--device", "cuda", audio_file_path], check=True)
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

def remove_previous_srt():
    srt_files = glob.glob("/data/*")
    if srt_files:
        print(f"[remove_previous_srt] Borrando SRT anteriores => {srt_files}")
        for path in srt_files:
            try:
                os.remove(path)
                print(f"   [remove_previous_srt] Eliminado: {path}")
            except Exception as e:
                print(f"   [remove_previous_srt] Error al eliminar {path}: {e}")
    else:
        print("[remove_previous_srt] No había SRT previos en /data.")

# ------------------------------------------------------------------------------------
# NUEVAS FUNCIONES PARA KARAOKE DINÁMICO
# ------------------------------------------------------------------------------------

def parse_word_srt(srt_path: str) -> list:
    """
    Parsea el archivo SRT y para cada bloque, si aparecen varias líneas
    (varias palabras), las distribuye equitativamente en el intervalo.
    Devuelve una lista de diccionarios: { "start": float, "end": float, "word": str }.
    """
    segments = []
    if not os.path.exists(srt_path):
        print(f"[parse_word_srt] SRT no encontrado: {srt_path}")
        return segments
    with open(srt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if line.isdigit():
            idx += 1  # índice del bloque
            if idx < len(lines):
                time_line = lines[idx].strip()
                try:
                    start_str, end_str = time_line.split(" --> ")
                    block_start = time_str_to_sec(start_str)
                    block_end = time_str_to_sec(end_str)
                except Exception as e:
                    print(f"[parse_word_srt] Error parseando tiempos: {e}")
                    idx += 1
                    continue
                idx += 1
                text_lines = []
                while idx < len(lines) and lines[idx].strip() != "":
                    text_lines.append(lines[idx].strip())
                    idx += 1
                full_text = " ".join(text_lines)
                tokens = full_text.split()
                n_tokens = len(tokens)
                duration = block_end - block_start
                if n_tokens > 0:
                    token_duration = duration / n_tokens
                    for i, token in enumerate(tokens):
                        token_start = block_start + i * token_duration
                        token_end = token_start + token_duration
                        segments.append({"start": token_start, "end": token_end, "word": token})
                idx += 1  # Salta la línea vacía
            else:
                idx += 1
        else:
            idx += 1
    return segments



def time_str_to_sec(time_str: str) -> float:
    # time_str en formato "hh:mm:ss,ms"
    parts = time_str.split(":")
    hh = int(parts[0])
    mm = int(parts[1])
    ss, ms = parts[2].split(",")
    total = hh*3600 + mm*60 + int(ss) + int(ms)/1000
    return total

def normalize_manual_lyrics(lyrics: str) -> str:
    """
    Elimina todas las líneas vacías de la letra, de modo que si había
    uno o más saltos de línea consecutivos, todos ellos desaparecen,
    dejando sólo las líneas con texto.
    """
    # 1) Separa en líneas y filtra las vacías
    lines = [line.strip() for line in lyrics.splitlines() if line.strip()]
    # 2) Vuelve a unir con un único '\n'
    return "\n".join(lines)


def group_word_segments(manual_lyrics: str, word_segments: list) -> list:
    """
    Agrupa los segmentos de palabra en líneas, asignando de forma proporcional
    los tokens disponibles respecto a la cantidad esperada en la letra manual,
    y asegurando que cada línea obtenga al menos 1 token si contiene al menos
    una palabra en la letra.

    Devuelve una lista de diccionarios con:
      - line_text: la línea completa (como en la letra manual)
      - start: tiempo de inicio (del primer token asignado)
      - end: tiempo de fin (del último token asignado)
      - words: lista de tokens con sus tiempos
    """

    # 1) Normalizamos saltos de línea para colapsar dobles o más en uno solo
    normalized = re.sub(r'\n+', '\n', manual_lyrics)

    # 2) Separamos las líneas (ignorando líneas vacías)
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]

    # 3) Contamos cuántas palabras “esperamos” por línea
    manual_tokens_counts = [len(line.split()) for line in lines]
    expected_total = sum(manual_tokens_counts)
    actual_total   = len(word_segments)

    if expected_total == 0 or actual_total == 0:
        return []

    # 4) Cálculo proporcional inicial
    proportional = [ (cnt/expected_total) * actual_total for cnt in manual_tokens_counts ]

    # 5) Redondeo y forzar mínimo 1 token por línea
    assigned = []
    for cnt_exp, prop in zip(manual_tokens_counts, proportional):
        raw = int(round(prop))
        if cnt_exp > 0:
            # Si la línea tiene al menos una palabra, forzamos al menos 1 token
            assigned.append(max(1, raw))
        else:
            assigned.append(0)

    # 6) Ajuste fino para que la suma coincida con actual_total
    diff = actual_total - sum(assigned)
    # Precomputamos decimales para saber dónde ajustar
    decimals = [(p - round(p)) for p in proportional]

    while diff != 0:
        if diff > 0:
            # Aumentamos 1 token donde el decimal sea mayor
            idx = max(range(len(decimals)), key=lambda i: decimals[i])
            assigned[idx] += 1
            decimals[idx] = 0
            diff -= 1
        else:  # diff < 0
            # Disminuimos 1 token donde el decimal sea más pequeño,
            # pero sin caer por debajo de 1 (si la línea tenía palabras)
            idx = min(range(len(decimals)), key=lambda i: decimals[i])
            if assigned[idx] > 1:
                assigned[idx] -= 1
                decimals[idx] = 0
                diff += 1
            else:
                # Si no podemos quitar más sin romper la regla de mínimo 1, salimos
                break

    # 7) Finalmente, cortamos los segmentos según assigned y construimos el resultado
    grouped = []
    cur = 0
    for line, cnt in zip(lines, assigned):
        segs = word_segments[cur: cur+cnt]
        cur += cnt
        if segs:
            grouped.append({
                "line_text": line,
                "start": segs[0]["start"],
                "end": segs[-1]["end"],
                "words": segs
            })

    return grouped


def render_line_image(line_info: dict, t_offset: float, clip_width: int = TEXT_CLIP_WIDTH, 
                      font_path: str = FONT, font_size: int = FONT_SIZE, 
                      normal_color: str = TEXT_COLOR, highlight_color: str = HIGHLIGHT_COLOR) -> np.ndarray:
    """
    Renderiza una imagen de la línea de texto para el karaoke.
    Se centra horizontalmente y se pinta en highlight las palabras ya "cantadas".
    """
    # Creamos una imagen con fondo transparente usando el ancho definido
    img = Image.new("RGBA", (clip_width, font_size + 20), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        print(f"[render_line_image] Error al cargar la fuente: {e}")
        font = ImageFont.load_default()

    # Concatenamos todas las palabras para medir el ancho total
    full_text = " ".join([seg["word"] for seg in line_info["words"]])
    total_text_width, _ = draw.textsize(full_text, font=font)
    # Calculamos el margen horizontal para centrar el texto
    x_start = max((clip_width - total_text_width) // 2, 0)
    x = x_start
    y = 10

    # Iteramos sobre cada palabra para renderizarlas con el color adecuado
    for seg in line_info["words"]:
        word_relative_time = seg["start"] - line_info["start"]
        word_text = seg["word"]
        color = highlight_color if t_offset >= word_relative_time else normal_color
        # Convertimos stroke_width a entero
        draw.text((x, y), word_text + " ", font=font, fill=color,
                  stroke_width=int(TEXT_STROKE_WIDTH), stroke_fill=TEXT_STROKE_COLOR)
        word_width, _ = draw.textsize(word_text + " ", font=font)
        x += word_width
    frame = np.array(img.convert("RGB"))
    return frame


def create_karaoke_text_clip(line_info: dict, advance: float=0.5, duration_padding: float=0.0):
    """
    Crea un VideoClip para la línea de karaoke.
    - Se inicia 'advance' segundos antes del tiempo real (no negativo).
    - Dura hasta (line_info["end"] - line_info["start"] + advance + duration_padding)
    """
    line_duration = line_info["end"] - line_info["start"]
    clip_duration = line_duration + advance + duration_padding
    # Tiempo en que se considera que la línea empieza a mostrarse (dentro del clip)
    display_offset = advance  # es el retraso interno del clip

    def make_frame(t):
        # t es el tiempo transcurrido en el clip
        # Se renderiza la imagen de la línea con t - display_offset (si ya es positivo)
        effective_t = max(t - display_offset, 0)
        frame = render_line_image(line_info, effective_t)
        return frame

    txt_clip = VideoClip(make_frame, duration=clip_duration)
    return txt_clip

# ------------------------------------------------------------------------------------
# FUNCIONES DE CREACIÓN DE VIDEO
# ------------------------------------------------------------------------------------

def create(video_path: str):
    """
    Versión automática: transcribe con WhisperX, parsea el SRT en tokens,
    agrupa en frases cada N palabras, y renderiza karaoke dinámico.
    """
    remove_previous_srt()

    # 1) Convertir vídeo a mp3 y separar stems
    print(f"[create] Recibimos video_path={video_path}")
    audio_path = video_to_mp3(video_path)
    if not audio_path:
        print("[create] audio_path vacío")
        return ""
    vocals_path, music_path = separate_stems_cli(audio_path)
    if not vocals_path or not music_path:
        print("[create] No hay vocals o music")
        return ""

    # 2) Transcripción automática con WhisperX
    call_whisperx_endpoint(vocals_path)
    srt_file = vocals_path.replace(".wav", "_whisperx.srt")
    if not os.path.exists(srt_file):
        print("[create] SRT no existe")
        return ""

    # 3) Parsear SRT en segmentos de palabra
    word_segments = parse_word_srt(srt_file)
    if not word_segments:
        print("[create] No hay segmentos de palabra")
        return ""

    # 4) Agrupar cada N tokens en una frase
    N = 10  # número de palabras por frase
    groups = []
    for i in range(0, len(word_segments), N):
        segs = word_segments[i:i+N]
        # construye la línea uniendo las palabras de estos segmentos
        line_text = " ".join([w["word"] for w in segs])
        groups.append({
            "line_text": line_text,
            "start": segs[0]["start"],
            "end":   segs[-1]["end"],
            "words": segs
        })

    # 5) Preparar audio y vídeo de fondo
    music  = AudioFileClip(music_path).set_fps(44100)
    vocals = AudioFileClip(vocals_path).volumex(VOCAL_VOLUME).set_fps(44100)
    combined = CompositeAudioClip([music, vocals])
    background = VideoFileClip(video_path).set_duration(combined.duration).set_fps(30)
    dimmed = background.fl_image(lambda img: (img*0.3).astype("uint8"))

    # 6) Crear y posicionar los clips de karaoke
    karaoke_clips = []
    for grp in groups:
        start    = max(grp["start"] - 0.5, 0)
        duration = grp["end"] - grp["start"] + 0.5
        clip     = create_karaoke_text_clip(grp, advance=0.5)
        clip     = clip.set_start(start).set_duration(duration)
        clip     = clip.set_position(("center","bottom"))
        karaoke_clips.append(clip)

    # 7) Componer y exportar
    final = CompositeVideoClip([dimmed] + karaoke_clips).set_audio(combined)
    out_name = f"karaoke_{os.path.basename(video_path)}"
    if not os.path.exists("./output"):
        os.makedirs("./output")
    out_path = os.path.join("./output", out_name)
    print(f"[create] Generando vídeo => {out_path}")
    final.write_videofile(out_path, fps=30, threads=4)
    print(f"[create] Terminado => {out_name}")
    return out_name



def create_with_manual_lyrics(video_path: str, manual_lyrics: str, language="es") -> str:
    """
    Variante MANUAL que usa WhisperX en modo forced alignment
    con letra proporcionada manualmente, y genera karaoke con subtítulos
    por línea y animación dinámica de highlight.
    """
    remove_previous_srt()
    manual_lyrics = normalize_manual_lyrics(manual_lyrics)
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
    # Llamada a WhisperX con letra manual
    call_whisperx_endpoint_manual(vocals_path, manual_lyrics, language)
    srt_file = vocals_path.replace(".wav","_whisperx.srt")
    print(f"[create_with_manual_lyrics] srt esperado => {srt_file}")
    if not os.path.exists(srt_file):
        print("[create_with_manual_lyrics] SRT no encontrado => return ''")
        return ""
    # PARTE NUEVA: Procesar el SRT para agrupar palabras según la letra manual
    word_segments = parse_word_srt(srt_file)
    groups = group_word_segments(manual_lyrics, word_segments)
    if not groups:
        print("[create_with_manual_lyrics] No se pudieron agrupar las palabras => return ''")
        return ""
    print(f"[create_with_manual_lyrics] Se han generado {len(groups)} líneas para karaoke")
    # Componer con moviepy
    music = AudioFileClip(music_path).set_fps(44100)
    vocals = AudioFileClip(vocals_path).volumex(VOCAL_VOLUME).set_fps(44100)
    combined = CompositeAudioClip([music, vocals])
    try:
        background = VideoFileClip(video_path).set_duration(combined.duration).set_fps(30)

    except Exception as ee:
        print(f"[create_with_manual_lyrics] VideoFileClip error => {ee}")
        return ""
    dimmed = background.fl_image(lambda img: (img*0.3).astype("uint8"))
    # Crear clips de karaoke para cada línea
    karaoke_clips = []
    for group in groups:
        # Se mostrará la línea empezando 0.5 seg antes de la palabra inicial
        start_offset = max(group["start"] - 0.5, 0)
        duration = group["end"] - group["start"] + 0.5
        clip = create_karaoke_text_clip(group, advance=0.5, duration_padding=0.0)
        # Posicionamos el clip (por ejemplo, centrado en la parte inferior)
        clip = clip.set_start(start_offset).set_duration(duration)
        clip = clip.set_position(("center", "bottom"))
        karaoke_clips.append(clip)
    # Componer el video final superponiendo los clips de karaoke sobre el background
    final = CompositeVideoClip([dimmed] + karaoke_clips).set_audio(combined)
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
