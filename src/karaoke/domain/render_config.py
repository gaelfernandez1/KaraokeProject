import platform
import os
import logging

logger = logging.getLogger(__name__)

VOLUME_VOCAL = 0.05

ANCHO_VIDEO = 1280
ALTO_VIDEO = 720
FPS_VIDEO = 30

COR_TEXTO = "#FFFFFF"
COR_RESALTADO = "#FFFF00"
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
COR_LIÑA_SEGUINTE = "#BBBBBB"
ALPHA_LIÑA_SEGUINTE = 0.7
ESPACIADO_LIÑAS = 20
MARXE_INFERIOR_SUBTITULO = 150
MOSTRAR_LIÑA_SEGUINTE = True
MODO_SILABICO = True

BUFFER_ANTICIPACION = 0.15
PESO_PROGRESO_TEMPORAL = 0.2
PESO_PROGRESO_SEGMENTO = 0.8
UMBRAL_ACELERACION = 0.85
FACTOR_ACELERACION_MAX = 2.0


def configurar_imagemagick() -> None:
    """Configura ImageMagick según el sistema operativo"""
    try:
        from moviepy.config import change_settings

        if platform.system() == "Darwin":
            ruta_imagemagick = "/opt/homebrew/bin/magick"
        elif platform.system() == "Windows":
            ruta_imagemagick = "C:/Program Files/ImageMagick-7.1.1-Q16-HDRI/magick.exe"
        elif platform.system() == "Linux":
            posibles_rutas = [
                "/usr/bin/convert",
                "/usr/bin/magick",
                "/usr/local/bin/convert",
                "/usr/local/bin/magick",
            ]
            ruta_imagemagick = next(
                (r for r in posibles_rutas if os.path.exists(r)), "/usr/bin/convert"
            )
        else:
            raise NotImplementedError("Unsupported operating system")

        change_settings({"IMAGEMAGICK_BINARY": ruta_imagemagick})
    except Exception as e:
        logger.error(f"Error configurando ImageMagick: {e}")


configurar_imagemagick()
