# 008 · Vídeo: el fondo viaja en el paquete y el MP4 se hace con un solo ffmpeg

- **Fecha**: 30/10/2026
- **Estado**: propuesta (área C6); se aprueba con su PR
- **Afecta a**: C4 (`make` guarda fondo y portada), C7 (fondo en el reproductor), C8 (sirve vídeos
  con peticiones Range; puede llamar a `render`)

## Contexto

Las canciones del usuario vienen de YouTube: su videoclip es el fondo más natural. El MP4 tiene que
salir rápido (≤ 1 min para 4 min de canción), verse bien en la tele y en vertical para redes, y la
letra leerse sobre cualquier imagen, también sobre vídeos casi blancos.

## Qué se miró y midió

- ffmpeg 8 con libass y NVENC en la RTX 3050 (WSL): NVENC funciona; libass pinta la letra en la CPU
  (unos 9 s por canción de 3 min a 1080p).
- Un fondo desenfocado a 1080p es lo caro (16 s): desenfocado a 1/6 de tamaño y escalado rápido
  queda igual y tarda la mitad.
- `zoompan` tiembla (ticket abierto de ffmpeg); sobre un fondo desenfocado no se nota.
- Fondos generados con `gradients` y `showcqt`: a tamaño completo son caros; pequeños y escalados,
  baratos. El espectro por defecto parece una herramienta técnica: no se usa.
- En la web, lo estándar para seguir el audio con un `<video>` es corregir con `playbackRate` y saltar
  solo si se va lejos; su `currentTime` es demasiado grueso para corregir cada fotograma.

## Decisión

- **El paquete guarda el vídeo de la canción** (`background.mp4`, 720p, H.264, clave por segundo,
  `+faststart`, sin audio) y una **portada** (`cover.jpg`: la carátula o un fotograma). Lo hace
  `karaoke make` (cambio mínimo en el área C4) y `karaoke background` para paquetes ya hechos. 720p
  basta para un fondo oscurecido bajo la letra y pesa un tercio que 1080p.
- **`karaoke render`**: un solo ffmpeg con el fondo (vídeo, portada o degradado del tema), oscurecido
  según su brillo, una franja oscura degradada detrás de la letra, el ASS de los subtítulos con
  título y créditos, y NVENC (x264 si no). 16:9 y 9:16; miniatura junto al vídeo.
- **Formas distintas**: el fondo se ve entero sobre una copia desenfocada que llena el resto; en
  vertical, arriba.
- **Web**: `BackgroundSync` (`#lib/video/background.ts`).

## Resultados

27–45 s para 4 min en la RTX 3050 (`bench/results/2026-10-30-c6-render/`).

## Consecuencias

- `make` tarda unos segundos más con vídeo (7 s para 3 min).
- C7: el reproductor pone el `<video>` del paquete detrás de la letra con `BackgroundSync` (el
  `/proba-letra` lo enseña).
- C8: los vídeos se sirven con peticiones Range (si no, el navegador no puede saltar); `render` es lo
  que debe llamar para exportar.
- MoviePy, PIL e ImageMagick no se usan en nada nuevo; solo quedan en `legacy/`, que borra C9.
