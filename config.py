import platform
import os
from moviepy.config import change_settings


VOLUME_VOCAL = 0.05


ANCHO_VIDEO = 1280
ALTO_VIDEO = 720
FPS_VIDEO = 30


COR_TEXTO = "#FFFFFF"
COR_RESALTADO = "#FFFF00"          #Amarillo
COR_CONTORNO_TEXTO = "#000000"
GROSOR_CONTORNO_TEXTO = 3  
TAMAÑO_FONTE = 36  
TAMAÑO_FONTE_MIN = 30  
FACTOR_FONTE_LIÑA_SEGUINTE = 0.85  
FONTE = "./fonts/kg.ttf"
MARXE = 40
TEXT_CLIP_WIDTH = ANCHO_VIDEO - 2 * MARXE  
COR_FONDO_TEXTO = (0, 0, 0, 180)  
PADDING_FONDO_TEXTO = 15  
COR_LIÑA_SEGUINTE = "#BBBBBB"     #Gris claro 
ALPHA_LIÑA_SEGUINTE = 0.7           #Transparencia para línea siguiente
ESPACIADO_LIÑAS = 20            #Creo que o vou disminuir porque creo que o problema da frase larga esta arreglado. PROBAR ESTO
MARXE_INFERIOR_SUBTITULO = 150  #Aumentado para deixar espacio a línea siguiente. PROBAR TAMEN
MOSTRAR_LIÑA_SEGUINTE = True  
MODO_SILABICO = True  


# Se imagemagick está instalado na localización estandar non lle di a moviepy onde esta, hai qye facer este codigo
# https://dev.to/muddylemon/making-my-own-karaoke-videos-with-ai-4b8l
#Ainda que ahora que esta todo en docker, a ruta de windows que usaba antes xa non se usa

def configurar_imagemagick():
    """Configura ImageMagick según el sistema operativo"""
    try:
        if platform.system() == "Darwin":
            ruta_imagemagick = "/opt/homebrew/bin/magick"
        elif platform.system() == "Windows":
            ruta_imagemagick = "C:/Program Files/ImageMagick-7.1.1-Q16-HDRI/magick.exe"
        elif platform.system() == "Linux":
           
            posibles_rutas = [
                "/usr/bin/convert",      
                "/usr/bin/magick",       
                "/usr/local/bin/convert",
                "/usr/local/bin/magick"
            ]
            
            ruta_imagemagick = None
            for ruta in posibles_rutas:
                if os.path.exists(ruta):
                    ruta_imagemagick = ruta
                    break
            
            if not ruta_imagemagick:
                ruta_imagemagick = "/usr/bin/convert"  # Fallback
        else:
            raise NotImplementedError("Unsupported operating system")
        
        change_settings({"IMAGEMAGICK_BINARY": ruta_imagemagick})
        
    except Exception as e:
        print(f"Error configurando ImageMagick: {e}")


configurar_imagemagick()
