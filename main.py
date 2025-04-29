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
TEXT_WIDTH = 1400
TEXT_COLOR = "#FFFFFF"
HIGHLIGHT_COLOR = "#FFFF00"  # por ejemplo amarillo para resaltar
TEXT_STROKE_COLOR = "#000000"
TEXT_STROKE_WIDTH = 2
FONT_SIZE = 40
FONT_SIZE_MIN = 28  # Tamaño mínimo de fuente para textos muy largos
NEXT_LINE_FONT_SIZE_FACTOR = 0.85  # Factor para reducir la fuente de la línea siguiente
FONT = "./fonts/kg.ttf"
MARGIN = 40
TEXT_CLIP_WIDTH = VIDEO_WIDTH - 2 * MARGIN  # Esto te da 1200
TEXT_BG_COLOR = (0, 0, 0, 128)  # Color de fondo semitransparente (RGBA)
TEXT_BG_PADDING = 10  # Padding del fondo de texto
NEXT_LINE_COLOR = "#BBBBBB"  # Color para la línea siguiente (gris claro)
NEXT_LINE_ALPHA = 0.7  # Transparencia para la línea siguiente
NEXT_LINE_SPACING = 15  # Espaciado vertical entre línea actual y la siguiente
MAX_CHARS_PER_LINE = 60  # Máximo de caracteres por línea antes de hacer wrap
SUBTITLE_BOTTOM_MARGIN = 150  # Margen desde abajo para los subtítulos (aumentado para líneas dobles)

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
    Renderiza una imagen de la línea de texto para el karaoke con mejoras:
    - Respeta las frases originales según delimitación por saltos de línea
    - Ajuste visual de texto largo en múltiples líneas sin romper la sincronización
    - Ajuste dinámico del tamaño de fuente según longitud
    - Fondo semitransparente para mejor legibilidad
    """
    # Obtenemos el texto completo de la línea, que debe mantenerse como una unidad
    full_text = line_info["line_text"]
    
    # Ajuste dinámico del tamaño de fuente basado en longitud
    dynamic_font_size = font_size
    if len(full_text) > 80:
        # Reducimos progresivamente el tamaño para textos muy largos
        reduction_factor = min(1.0, 80 / len(full_text))
        dynamic_font_size = max(FONT_SIZE_MIN, int(font_size * reduction_factor))
    
    try:
        font = ImageFont.truetype(font_path, dynamic_font_size)
    except Exception as e:
        print(f"[render_line_image] Error al cargar la fuente: {e}")
        font = ImageFont.load_default()
    
    # Realizamos el ajuste visual (wrapping) sin alterar la estructura de sincronización
    # Esto es puramente visual - la frase completa sigue siendo una unidad de sincronización
    wrapped_lines = []
    words = full_text.split()
    current_line = ""
    
    for word in words:
        # Si la línea está vacía, añadimos la palabra directamente
        if not current_line:
            current_line = word
            continue
            
        # Probamos añadir la siguiente palabra
        test_line = current_line + " " + word
        
        # Calculamos el ancho con la fuente actual
        text_width = font.getlength(test_line) if hasattr(font, 'getlength') else font.getsize(test_line)[0]
        
        if text_width <= clip_width - 2 * TEXT_BG_PADDING:
            # La palabra cabe en la línea actual
            current_line = test_line
        else:
            # La palabra no cabe, guardamos línea actual y empezamos nueva con esta palabra
            wrapped_lines.append(current_line)
            current_line = word
    
    # No olvidamos la última línea
    if current_line:
        wrapped_lines.append(current_line)
    
    # Si no hay líneas (caso excepcional), usamos el texto completo
    if not wrapped_lines:
        wrapped_lines = [full_text]
    
    # Calculamos altura total necesaria para todas las líneas visuales
    line_height = dynamic_font_size + 10  # Espacio entre líneas
    total_height = len(wrapped_lines) * line_height + 2 * TEXT_BG_PADDING
    
    # Creamos imagen con altura adecuada para todas las líneas
    img = Image.new("RGBA", (clip_width, total_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Creamos fondo semitransparente para mejor legibilidad
    bg_layer = Image.new("RGBA", (clip_width, total_height), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg_layer)
    
    # Calculamos ancho máximo para dimensionar el fondo
    max_line_width = 0
    for line in wrapped_lines:
        line_width = font.getlength(line) if hasattr(font, 'getlength') else font.getsize(line)[0]
        max_line_width = max(max_line_width, line_width)
    
    # Dibujamos fondo semitransparente
    bg_width = min(max_line_width + 2 * TEXT_BG_PADDING, clip_width)
    bg_x = (clip_width - bg_width) // 2
    bg_draw.rectangle(
        [(bg_x, 0), (bg_x + bg_width, total_height)],
        fill=TEXT_BG_COLOR
    )
    
    # Ahora calculamos qué palabras deben resaltarse basado en el tiempo
    # Estamos trabajando con la frase completa como una unidad de sincronización
    words = full_text.split()
    words_to_highlight = 0
    
    # Para la sincronización, usamos los tiempos de word_segments asociados a esta línea
    if line_info["words"]:
        duration = line_info["end"] - line_info["start"]
        for i, seg in enumerate(line_info["words"]):
            word_relative_time = seg["start"] - line_info["start"]
            if t_offset >= word_relative_time:
                words_to_highlight = i + 1
    else:
        # Modo fallback: avance proporcional al tiempo
        progress_ratio = min(1.0, max(0.0, t_offset / (line_info["end"] - line_info["start"])))
        words_to_highlight = int(progress_ratio * len(words))
    
    # Ahora dibujamos cada línea visual (wrapping puramente visual)
    all_words = []
    for wrapped_line in wrapped_lines:
        all_words.extend(wrapped_line.split())
    
    # Reasignamos las palabras a las líneas visualmente envueltas
    words_assigned = 0
    for i, line in enumerate(wrapped_lines):
        line_words = line.split()
        y = i * line_height + TEXT_BG_PADDING
        
        # Centramos cada línea
        line_width = font.getlength(line) if hasattr(font, 'getlength') else font.getsize(line)[0]
        x = (clip_width - line_width) // 2
        
        # Dibujamos palabra por palabra
        for word in line_words:
            # Determinamos si esta palabra debe resaltarse
            color = highlight_color if words_assigned < words_to_highlight else normal_color
            
            # Dibujamos la palabra con su contorno
            draw.text((x, y), word, font=font, fill=color,
                     stroke_width=int(TEXT_STROKE_WIDTH), stroke_fill=TEXT_STROKE_COLOR)
            
            # Avanzamos la posición x para la siguiente palabra
            word_width = font.getlength(word) if hasattr(font, 'getlength') else font.getsize(word)[0]
            x += word_width + font.getlength(" ") if hasattr(font, 'getlength') else font.getsize(" ")[0]
            
            words_assigned += 1
    
    # Combinamos el fondo y el texto
    img = Image.alpha_composite(bg_layer, img)
    
    # Convertimos a formato RGB para moviepy
    frame = np.array(img.convert("RGB"))
    return frame


def render_next_line_image(line_info: dict, clip_width: int = TEXT_CLIP_WIDTH,
                        font_path: str = FONT, font_size: int = None) -> np.ndarray:
    """
    Renderiza una imagen para la próxima línea de karaoke (previsualización)
    con un estilo visual distinto (más tenue) para diferenciarla de la línea actual.
    """
    if font_size is None:
        # Usar un tamaño de fuente ligeramente más pequeño para la línea siguiente
        font_size = int(FONT_SIZE * NEXT_LINE_FONT_SIZE_FACTOR)
        
    # Obtenemos el texto completo de la línea
    full_text = line_info["line_text"]
    
    # Ajuste dinámico del tamaño de fuente basado en longitud
    dynamic_font_size = font_size
    if len(full_text) > 80:
        reduction_factor = min(1.0, 80 / len(full_text))
        dynamic_font_size = max(FONT_SIZE_MIN, int(font_size * reduction_factor))
    
    try:
        font = ImageFont.truetype(font_path, dynamic_font_size)
    except Exception as e:
        print(f"[render_next_line_image] Error al cargar la fuente: {e}")
        font = ImageFont.load_default()
    
    # Realizamos el ajuste visual (wrapping) igual que la línea principal
    wrapped_lines = []
    words = full_text.split()
    current_line = ""
    
    for word in words:
        if not current_line:
            current_line = word
            continue
            
        test_line = current_line + " " + word
        text_width = font.getlength(test_line) if hasattr(font, 'getlength') else font.getsize(test_line)[0]
        
        if text_width <= clip_width - 2 * TEXT_BG_PADDING:
            current_line = test_line
        else:
            wrapped_lines.append(current_line)
            current_line = word
    
    if current_line:
        wrapped_lines.append(current_line)
    
    if not wrapped_lines:
        wrapped_lines = [full_text]
    
    # Calculamos altura total necesaria para todas las líneas
    line_height = dynamic_font_size + 10
    total_height = len(wrapped_lines) * line_height + 2 * TEXT_BG_PADDING
    
    # Creamos imagen con fondo transparente
    img = Image.new("RGBA", (clip_width, total_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Creamos fondo semitransparente para la línea siguiente (más tenue que la principal)
    bg_layer = Image.new("RGBA", (clip_width, total_height), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg_layer)
    
    # Calculamos ancho máximo del texto
    max_line_width = 0
    for line in wrapped_lines:
        line_width = font.getlength(line) if hasattr(font, 'getlength') else font.getsize(line)[0]
        max_line_width = max(max_line_width, line_width)
    
    # Dibujamos fondo semitransparente con más transparencia que la línea principal
    next_line_bg_color = (TEXT_BG_COLOR[0], TEXT_BG_COLOR[1], TEXT_BG_COLOR[2], 
                         int(TEXT_BG_COLOR[3] * NEXT_LINE_ALPHA))
    bg_width = min(max_line_width + 2 * TEXT_BG_PADDING, clip_width)
    bg_x = (clip_width - bg_width) // 2
    bg_draw.rectangle(
        [(bg_x, 0), (bg_x + bg_width, total_height)],
        fill=next_line_bg_color
    )
    
    # Dibujamos cada línea visual con el color de la siguiente línea
    for i, line in enumerate(wrapped_lines):
        y = i * line_height + TEXT_BG_PADDING
        
        # Centramos cada línea
        line_width = font.getlength(line) if hasattr(font, 'getlength') else font.getsize(line)[0]
        x = (clip_width - line_width) // 2
        
        # Dibujamos el texto en un color más claro/grisáceo
        draw.text((x, y), line, font=font, fill=NEXT_LINE_COLOR,
                 stroke_width=int(TEXT_STROKE_WIDTH * 0.75), stroke_fill=TEXT_STROKE_COLOR)
    
    # Combinamos el fondo y el texto
    img = Image.alpha_composite(bg_layer, img)
    
    # Convertimos a formato RGB para moviepy
    frame = np.array(img.convert("RGB"))
    return frame


def create_karaoke_text_clip(line_info: dict, next_line_info: dict = None, advance: float=0.5, duration_padding: float=0.5):
    """
    Crea un VideoClip para la línea de karaoke con mejoras:
    - Se inicia 'advance' segundos antes del tiempo real (no negativo)
    - Dura hasta (line_info["end"] - line_info["start"] + advance + duration_padding)
    - Ajuste adaptable al tamaño del texto
    - Soporte para textos muy largos con wrap automático
    - Opcionalmente muestra la siguiente línea debajo (next_line_info)
    """
    line_duration = line_info["end"] - line_info["start"]
    clip_duration = line_duration + advance + duration_padding
    # Tiempo en que se considera que la línea empieza a mostrarse (dentro del clip)
    display_offset = advance  # es el retraso interno del clip

    def make_frame(t):
        # t es el tiempo transcurrido en el clip
        # Se renderiza la imagen de la línea con t - display_offset (si ya es positivo)
        effective_t = max(t - display_offset, 0)
        
        # Renderizamos la línea actual
        current_frame = render_line_image(line_info, effective_t)
        
        # Si se proporcionó la línea siguiente, la renderizamos debajo
        if next_line_info:
            next_frame = render_next_line_image(next_line_info)
            
            # Combinamos los dos frames
            height1 = current_frame.shape[0]
            height2 = next_frame.shape[0]
            width = max(current_frame.shape[1], next_frame.shape[1])
            
            # Creamos un frame combinado
            combined_height = height1 + NEXT_LINE_SPACING + height2
            combined_frame = np.zeros((combined_height, width, 3), dtype=np.uint8)
            
            # Copiamos la línea actual en la parte superior
            combined_frame[:height1, :current_frame.shape[1]] = current_frame
            
            # Copiamos la línea siguiente en la parte inferior
            combined_frame[height1 + NEXT_LINE_SPACING:, :next_frame.shape[1]] = next_frame
            
            return combined_frame
        
        # Si no hay línea siguiente, devolvemos solo el frame actual
        return current_frame

    txt_clip = VideoClip(make_frame, duration=clip_duration)
    return txt_clip

# ------------------------------------------------------------------------------------
# FUNCIONES DE CREACIÓN DE VIDEO
# ------------------------------------------------------------------------------------

def normalize_video(video_path: str) -> str:
    """
    Normaliza un video de entrada a un formato estándar para asegurar consistencia
    entre videos de YouTube y clips recortados manualmente.
    
    Args:
        video_path: Ruta al video original
    
    Returns:
        Ruta al nuevo video normalizado
    """
    print(f"[normalize_video] Normalizando video: {video_path}")
    normalized_path = video_path.replace(".mp4", "_normalized.mp4")
    
    # Si ya existe un video normalizado, lo devolvemos
    if os.path.exists(normalized_path):
        print(f"[normalize_video] Video normalizado ya existe: {normalized_path}")
        return normalized_path
    
    try:
        # Usamos ffmpeg para normalizar el video a un formato estándar
        # - Formato: MP4 con codec h264
        # - Resolución: 1280x720 (manteniendo aspect ratio)
        # - Framerate: 30 fps
        # - Audio: AAC codec, 44.1kHz, stereo
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-c:v", "libx264",
            "-preset", "medium",  # Equilibrio entre calidad y velocidad
            "-profile:v", "high",
            "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2",
            "-r", "30",
            "-c:a", "aac",
            "-ar", "44100",
            "-ac", "2",
            "-b:a", "192k",
            "-y",  # Sobrescribir si existe
            normalized_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"[normalize_video] Video normalizado guardado en: {normalized_path}")
        return normalized_path
    except Exception as e:
        print(f"[normalize_video] ERROR normalizando video: {e}")
        # Si falla la normalización, devolvemos el video original
        return video_path


def create(video_path: str):
    """
    Versión automática: transcribe con WhisperX, parsea el SRT en tokens,
    agrupa en frases cada N palabras, y renderiza karaoke dinámico.
    """
    remove_previous_srt()

    # 1) Convertir vídeo a mp3 y separar stems
    print(f"[create] Recibimos video_path={video_path}")
    video_path = normalize_video(video_path)
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
    for idx, grp in enumerate(groups):
        start    = max(grp["start"] - 0.5, 0)
        duration = grp["end"] - grp["start"] + 1.0  # Aumentamos duración para mejor lectura
        next_line = groups[idx + 1] if idx + 1 < len(groups) else None
        clip     = create_karaoke_text_clip(grp, next_line_info=next_line, advance=0.5, duration_padding=0.5)
        clip     = clip.set_start(start).set_duration(duration)
        
        # Posicionamos con margen inferior mejorado
        bottom_pos = VIDEO_HEIGHT - SUBTITLE_BOTTOM_MARGIN
        clip = clip.set_position(lambda t: ('center', bottom_pos))
        
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
    video_path = normalize_video(video_path)
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
    
    # Crear clips de karaoke para cada línea con nuestras mejoras
    karaoke_clips = []
    for idx, group in enumerate(groups):
        # Se mostrará la línea empezando 0.5 seg antes de la palabra inicial
        start_offset = max(group["start"] - 0.5, 0)
        duration = group["end"] - group["start"] + 1.0  # Aumentamos duración para mejor lectura
        
        # Usamos el clip mejorado con soporte para textos largos y línea siguiente
        next_line = groups[idx + 1] if idx + 1 < len(groups) else None
        clip = create_karaoke_text_clip(group, next_line_info=next_line, advance=0.5, duration_padding=0.5)
        
        # Posicionamos el clip con el margen inferior mejorado
        bottom_pos = VIDEO_HEIGHT - SUBTITLE_BOTTOM_MARGIN
        clip = clip.set_start(start_offset).set_duration(duration)
        clip = clip.set_position(lambda t: ('center', bottom_pos))
        
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
