import os
import subprocess
from moviepy.editor import VideoFileClip
from config import ANCHO_VIDEO, ALTO_VIDEO, FPS_VIDEO


#normalizar os videos ao mismo formato en ambas opcions para que os subtitulos salan sempre igual. Diferentes
#formatos de video facia que os subtitulos se comportasen diferente cada vez
def normalize_video(video_path: str) -> str:

    normalized_path = video_path.replace(".mp4", "_normalized.mp4")
    
    if os.path.exists(normalized_path):
        try:
            os.remove(normalized_path)
        except Exception as e:
            print(f"error ao eliminar o archivo previo {e}")
    
    #Tuven que intentar diferentes estrategias de normalizacion compatibles co ffmpeg do contenedor
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
            "name": "forzar_h264_con_recodificacion",
            "cmd": [
                "ffmpeg",
                "-i", video_path,
                "-c:v", "libx264",  
                "-vf", f"scale={ANCHO_VIDEO}:{ALTO_VIDEO}:force_original_aspect_ratio=decrease,pad={ANCHO_VIDEO}:{ALTO_VIDEO}:(ow-iw)/2:(oh-ih)/2",
                "-r", f"{FPS_VIDEO}",
                "-c:a", "aac",  
                "-preset", "fast",  
                "-y",
                normalized_path
            ]
        },
        {
            "name": "escalado_directo_h264",
            "cmd": [
                "ffmpeg",
                "-i", video_path,
                "-c:v", "libx264",
                "-vf", f"scale={ANCHO_VIDEO}:{ALTO_VIDEO}",  
                "-r", f"{FPS_VIDEO}",
                "-c:a", "aac",
                "-preset", "fast",
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
                    normalized_clip = video_clip.resize((ANCHO_VIDEO, ALTO_VIDEO))
                    
                    normalized_clip.write_videofile(
                        normalized_path,
                        fps=FPS_VIDEO,
                        codec='libx264',
                        audio_codec='aac',
                        verbose=False,
                        logger=None
                    )
                    
                    video_clip.close()
                    normalized_clip.close()
                    
                    if os.path.exists(normalized_path) and os.path.getsize(normalized_path) > 0:
                        return normalized_path
                    
                except Exception as e:
                    print(f" Error con MoviePy: {e}")
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
