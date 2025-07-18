import os
import subprocess
import json
from typing import Dict, Optional
from moviepy.editor import VideoFileClip
from config import ANCHO_VIDEO, ALTO_VIDEO, FPS_VIDEO

#Conten arreglo Pillow e mais cousas. Chequear o commit mais a web onde se arreglaba

def patch_pillow_compatibility():
    try:
        from PIL import Image
        if not hasattr(Image, 'ANTIALIAS'):
            Image.ANTIALIAS = Image.LANCZOS
    except ImportError:
        pass
    except Exception:
        pass


def get_video_info(video_path: str) -> Dict:
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception:
        return {}


def get_video_codec(video_path: str) -> Optional[str]:
    video_info = get_video_info(video_path)
    
    if video_info and 'streams' in video_info:
        for stream in video_info['streams']:
            if stream.get('codec_type') == 'video':
                return stream.get('codec_name')
    return None


def get_video_dimensions(video_path: str) -> tuple:
    video_info = get_video_info(video_path)
    
    if video_info and 'streams' in video_info:
        for stream in video_info['streams']:
            if stream.get('codec_type') == 'video':
                width = stream.get('width', 0)
                height = stream.get('height', 0)
                return (width, height)
    return (0, 0)


#solucion para mirar se o video ten que ser recodificado
def needs_reencoding(video_path: str) -> bool:
    codec = get_video_codec(video_path)
    
    problematic_codecs = ['av01', 'hevc', 'vp9']
    
    return codec in problematic_codecs if codec else True


patch_pillow_compatibility()


#normalizar os videos ao mismo formato en ambas opcions para que os subtitulos salan sempre igual. Diferentes
#formatos de video facia que os subtitulos se comportasen diferente cada vez
def normalize_video(video_path: str) -> str:

    normalized_path = video_path.replace(".mp4", "_normalized.mp4")
    
    if os.path.exists(normalized_path):
        try:
            os.remove(normalized_path)
        except Exception as e:
            print(f"error ao eliminar o archivo previo {e}")
    
    

    #tuven que intentar diferentes estrategias de normalizacion compatibles co ffmpeg do contenedor    
    video_codec = get_video_codec(video_path)
    width, height = get_video_dimensions(video_path)
    requires_reencoding = needs_reencoding(video_path)
        
    if requires_reencoding or video_codec == 'av01':
        print("Usando estratexias de recodificación para codec problemático")
        strategies = [
            {
                "name": "recodificacion_av1_libaom",
                "cmd": [
                    "ffmpeg",
                    "-i", video_path,
                    "-c:v", "libx264",
                    "-vf", f"scale={ANCHO_VIDEO}:{ALTO_VIDEO}:force_original_aspect_ratio=decrease,pad={ANCHO_VIDEO}:{ALTO_VIDEO}:(ow-iw)/2:(oh-ih)/2",
                    "-r", f"{FPS_VIDEO}",
                    "-c:a", "aac",
                    "-pix_fmt", "yuv420p",
                    "-crf", "23",
                    "-maxrate", "2M",
                    "-bufsize", "4M",
                    "-y",
                    normalized_path
                ]
            },
            {
                "name": "recodificacion_forzada_h264",
                "cmd": [
                    "ffmpeg",
                    "-i", video_path,
                    "-c:v", "libx264",  
                    "-vf", f"scale={ANCHO_VIDEO}:{ALTO_VIDEO}:force_original_aspect_ratio=decrease,pad={ANCHO_VIDEO}:{ALTO_VIDEO}:(ow-iw)/2:(oh-ih)/2",
                    "-r", f"{FPS_VIDEO}",
                    "-c:a", "aac",
                    "-pix_fmt", "yuv420p",
                    "-y",
                    normalized_path
                ]
            },
            {
                "name": "escalado_simple_h264",
                "cmd": [
                    "ffmpeg",
                    "-i", video_path,
                    "-c:v", "libx264",
                    "-vf", f"scale={ANCHO_VIDEO}:{ALTO_VIDEO}",  
                    "-r", f"{FPS_VIDEO}",
                    "-c:a", "aac",
                    "-pix_fmt", "yuv420p",
                    "-y",
                    normalized_path
                ]
            },
            {
                "name": "moviepy_fallback",
                "moviepy": True  
            }
        ]
    else:
        print("Usando estratexias de escalado simple para codec compatible")
        strategies = [
            {
                "name": "escalado_simple",
                "cmd": [
                    "ffmpeg",
                    "-i", video_path,
                    "-vf", f"scale={ANCHO_VIDEO}:{ALTO_VIDEO}:force_original_aspect_ratio=decrease,pad={ANCHO_VIDEO}:{ALTO_VIDEO}:(ow-iw)/2:(oh-ih)/2",
                    "-r", f"{FPS_VIDEO}",
                    "-c:a", "copy",  
                    "-y",
                    normalized_path
                ]
            },
            {
                "name": "escalado_con_recodificacion",
                "cmd": [
                    "ffmpeg",
                    "-i", video_path,
                    "-c:v", "libx264",  
                    "-vf", f"scale={ANCHO_VIDEO}:{ALTO_VIDEO}:force_original_aspect_ratio=decrease,pad={ANCHO_VIDEO}:{ALTO_VIDEO}:(ow-iw)/2:(oh-ih)/2",
                    "-r", f"{FPS_VIDEO}",
                    "-c:a", "aac",  
                    "-y",
                    normalized_path
                ]
            },
            {
                "name": "moviepy_fallback",
                "moviepy": True  
            }
        ]
    
    
    for strategy in strategies:
        try:
            
            #este e un caso especial, uso moviepy como fallback
            if strategy.get("moviepy", False):
                try:
                    
                    video_clip = VideoFileClip(video_path)
                    
                    # Calcular o escalado mantendo a relación de aspecto
                    original_width, original_height = video_clip.size
                    aspect_ratio = original_width / original_height
                    target_aspect_ratio = ANCHO_VIDEO / ALTO_VIDEO
                    
                    if aspect_ratio > target_aspect_ratio:
                        # Video máis ancho, escalar por ancho
                        new_width = ANCHO_VIDEO
                        new_height = int(ANCHO_VIDEO / aspect_ratio)
                    else:
                        # Video máis alto, escalar por alto
                        new_height = ALTO_VIDEO
                        new_width = int(ALTO_VIDEO * aspect_ratio)
                    
                    
                    resized_clip = video_clip.resize((new_width, new_height))
                    
                    # igual fai falta padding
                    if new_width != ANCHO_VIDEO or new_height != ALTO_VIDEO:
                        from moviepy.editor import ColorClip, CompositeVideoClip
                        
                        #meto fondo negro
                        background = ColorClip(size=(ANCHO_VIDEO, ALTO_VIDEO), color=(0, 0, 0), duration=resized_clip.duration)
                        
                        
                        x_pos = (ANCHO_VIDEO - new_width) // 2
                        y_pos = (ALTO_VIDEO - new_height) // 2
                        
                        final_clip = CompositeVideoClip([
                            background,
                            resized_clip.set_position((x_pos, y_pos))
                        ])
                    else:
                        final_clip = resized_clip
                    
                    
                    final_clip.write_videofile(
                        normalized_path,
                        fps=FPS_VIDEO,
                        codec='libx264',
                        audio_codec='aac',
                        verbose=False,
                        logger=None,
                        temp_audiofile='temp-audio.m4a',
                        remove_temp=True
                    )
                    
                    
                    video_clip.close()
                    if 'resized_clip' in locals():
                        resized_clip.close()
                    if 'final_clip' in locals():
                        final_clip.close()
                    
                    if os.path.exists(normalized_path) and os.path.getsize(normalized_path) > 0:
                        print(f"Video normalizado correctamente con MoviePy")
                        return normalized_path
                    
                except Exception as e:
                    print(f" Error con MoviePy: {e}")
                    
                    try:
                        if 'video_clip' in locals():
                            video_clip.close()
                        if 'resized_clip' in locals():
                            resized_clip.close()
                        if 'final_clip' in locals():
                            final_clip.close()
                    except:
                        pass
                    continue
            else:
                #Estrategias normales con ffmpeg
                result = subprocess.run(
                    strategy["cmd"], 
                    check=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True) 
                               
                if os.path.exists(normalized_path) and os.path.getsize(normalized_path) > 0:
                    print(f"Video normalizado correctamente con estrategia: {strategy['name']}")
                    return normalized_path
                
        except subprocess.CalledProcessError as e:
            print(f"fallou: {strategy['name']}: {e}")
            if e.stderr:
                print(f" Error ffmpeg: {e.stderr}")
    
    print(f" Todas as estrategias fallaron. Usando video original: {video_path}")
    return video_path
