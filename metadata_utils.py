import os
import re
from moviepy.editor import VideoFileClip
from typing import Dict, Optional
from urllib.parse import urlparse, parse_qs

#extrae un titulo limpo do nome do archivo
def extract_title_from_filename(filename: str) -> str:

    title = os.path.splitext(filename)[0]
    title = re.sub(r'^(karaoke_manual_[^_]+_|karaoke_[^_]+_|instrumental_[^_]+_|vocal_[^_]+_)', '', title)
    title = re.sub(r'^(karaoke_|karaoke_manual_|instrumental_|vocal_)', '', title)
    title = re.sub(r'_normalized$', '', title)   
    title = title.replace('_', ' ')    
    title = ' '.join(word.capitalize() for word in title.split())
    
    return title


#idealmente tiña q usar yt dlp para obter os metadatos pero e mais facil extraer o id e devolver none para que se use o titulo do archivo descargado
def extract_youtube_title_from_url(url: str) -> Optional[str]:
    try:
        return None
    except:
        return None

def get_video_duration(video_path: str) -> Optional[float]:
    try:
        with VideoFileClip(video_path) as video:
            return video.duration
    except Exception as e:
        return None

def get_file_size(file_path: str) -> int:
    try:
        return os.path.getsize(file_path)
    except:
        return 0

def clean_youtube_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
            if 'youtu.be' in parsed.netloc:
                video_id = parsed.path[1:]  #quitar a barra inicial
            else:
                video_id = parse_qs(parsed.query).get('v', [None])[0]
            
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
        
        return url
    except:
        return url

def generate_song_metadata(
    original_filename: str,
    karaoke_filename: str,
    source_type: str,
    source_url: Optional[str] = None,
    processing_type: str = "automatic",
    manual_lyrics: Optional[str] = None,
    language: Optional[str] = None,
    enable_diarization: bool = False,
    whisper_model: str = "small",
    output_dir: str = "output"
) -> Dict:
    """Xera metadatos completos para unha canción"""
    
    # xerar nomes dos archivos relacionados
    if karaoke_filename.startswith("karaoke_manual_"):
        base_name = karaoke_filename.replace("karaoke_manual_", "").replace(".mp4", "")
    elif karaoke_filename.startswith("karaoke_"):
        base_name = karaoke_filename.replace("karaoke_", "").replace(".mp4", "")
    else:
        base_name = karaoke_filename.replace(".mp4", "")
    
    video_only_filename = f"{karaoke_filename.replace('.mp4', '_video_only.mp4')}"
    vocal_filename = f"vocal_{base_name}.wav"
    instrumental_filename = f"instrumental_{base_name}.wav"
    
    title = extract_title_from_filename(original_filename)
    if source_url:
        youtube_title = extract_youtube_title_from_url(source_url)
        if youtube_title:
            title = youtube_title
    
    karaoke_path = os.path.join(output_dir, karaoke_filename)
    file_size = get_file_size(karaoke_path)
    duration = get_video_duration(karaoke_path)
    
    if source_url:
        source_url = clean_youtube_url(source_url)
    
    return {
        'title': title,
        'original_filename': original_filename,
        'karaoke_filename': karaoke_filename,
        'video_only_filename': video_only_filename,
        'vocal_filename': vocal_filename,
        'instrumental_filename': instrumental_filename,
        'source_type': source_type,
        'source_url': source_url,
        'processing_type': processing_type,
        'manual_lyrics': manual_lyrics,
        'language': language,
        'enable_diarization': enable_diarization,
        'whisper_model': whisper_model,
        'file_size': file_size,
        'duration': duration
    }

def format_file_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"

def format_duration(seconds: Optional[float]) -> str:
    """   HH:MM:SS  """
    if seconds is None:
        return "Descoñecida"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"