from moviepy.config import change_settings
import platform
# test_moviepy.py
from moviepy.editor import (
    ColorClip, 
    AudioFileClip, 
    TextClip, 
    CompositeVideoClip
)

if platform.system() == "Windows":
    imagemagick_path = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"

change_settings({"IMAGEMAGICK_BINARY": imagemagick_path})

# 1. Carga la pista instrumental (ya deberías haberla mezclado)
audio = AudioFileClip("other.wav")
duration = audio.duration

# 2. Crea un clip de color (fondo) con la misma duración
video_bg = ColorClip(size=(1280,720), color=(30,30,30))
video_bg = video_bg.set_duration(duration)

# 3. Ejemplo: añadir un texto (tipo "Hola Karaoke!") en un momento concreto
txt_clip = (TextClip("Hola Karaoke!", fontsize=70, color='white')
            .set_position('center')
            .set_duration(5)  # Este texto estará 5s
            .set_start(0))    # Empieza en el segundo 0

# 4. Componer
video = CompositeVideoClip([video_bg, txt_clip])
video = video.set_audio(audio)

# 5. Renderizar
video.write_videofile("karaoke_example.mp4", fps=24)
