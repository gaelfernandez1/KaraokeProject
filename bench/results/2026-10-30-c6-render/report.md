# Exportación MP4 · tiempos de `karaoke render`

- Fecha: 2026-10-30
- Equipo: RTX 3050 Laptop (4 GB), Ryzen 7 5800H, WSL; ffmpeg 8.0.1 (libass 0.17.4), NVENC
- Tema `clasico`, letra animada con título, créditos y franja oscura; audio instrumental copiado
- Medido con `render()` en un solo proceso, una exportación detrás de otra; el tiempo incluye
  medir el brillo del fondo y la miniatura

| Canción | Duración | Fondo | Formato | Codificador | Tiempo | Para 4 min |
|---|---|---|---|---|---|---|
| privada con videoclip cuadrado (1080×1080, 25 fps) | 177 s | vídeo | 16:9 | h264_nvenc | 29,5 s | 40 s |
| privada con videoclip cuadrado (1080×1080, 25 fps) | 177 s | vídeo | 9:16 | h264_nvenc | 29,5 s | 40 s |
| Esencia (NANDOMALO, CC BY-SA, JamendoLyrics) | 262 s | degradado | 16:9 | h264_nvenc | 30,9 s | 28 s |
| Esencia (NANDOMALO, CC BY-SA, JamendoLyrics) | 262 s | degradado | 9:16 | h264_nvenc | 29,9 s | 27 s |
| Esencia, con el videoclip anterior en bucle | 262 s | vídeo | 16:9 | h264_nvenc | 48,8 s | 45 s |

Meta (`00-vision.md` §1): MP4 1080p de 4 min en ≤ 1 min. Se cumple en todos los casos.

## Dónde va el tiempo (videoclip de 177 s, 16:9)

| Paso | Tiempo |
|---|---|
| decodificar el vídeo | 2,0 s |
| fondo (desenfoque reducido a 1/6, vídeo encima, oscurecido) + letra, sin codificar | 18,7 s |
| + franja oscura, convertida a YUV una vez | +3,6 s (con la conversión en cada fotograma, +7,9 s) |
| medir el brillo del fondo (12 fotogramas) | 2,1 s |

## Guardar el vídeo de la canción en el paquete (`karaoke make`)

| Fuente | Duración | Tiempo | Tamaño de `background.mp4` (720p) |
|---|---|---|---|
| videoclip cuadrado | 177 s | 7,3 s | 1,8 MB |
| videoclip 1920×1080 a 50 fps, mucho movimiento | 27 s | 4,2 s | 5,2 MB |
