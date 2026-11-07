# Exportación MP4 · calidad del fondo y del codificador

- Fecha: 2026-11-07
- Equipo: RTX 3050 Laptop (4 GB), Ryzen 7 5800H, WSL; ffmpeg 8.0.1 (libass 0.17.4), NVENC
- Fuente: videoclip de 27 s, 1920×1080 a 50 fps y 8 Mb/s, con mucho movimiento (privado,
  `bench/data/gl/`), con la letra del paquete `make-pelijroso`; tema `clasico`
- Referencia: el mismo `render()` con el vídeo original de fondo y x264 sin pérdidas (`-qp 0`);
  todas las variantes con el mismo oscurecido
- Métricas: SSIM y XPSNR (luma) de ffmpeg sobre el fotograma entero y sobre la franja de la letra
  (este ffmpeg no trae VMAF)

## Qué limita la calidad (16:9)

| Variante | Tiempo | Tamaño | SSIM | XPSNR | XPSNR en la letra |
|---|---|---|---|---|---|
| fondo 720p (CQ 30) · NVENC p4 CQ 21 (lo que había) | 7,9 s | 22,7 MB | 0,9866 | 36,9 | 36,9 |
| fondo 720p · NVENC p6 `tune hq`, multipase, AQ, *lookahead* 32, CQ 21 | 8,7 s | 28,7 MB | 0,9865 | 37,0 | 37,0 |
| fondo 720p · lo mismo con CQ 23 | 8,7 s | 22,9 MB | 0,9863 | 36,9 | 36,8 |
| fondo 720p · x264 `veryfast` CRF 21 | 7,7 s | 10,5 MB | 0,9834 | 35,9 | 35,3 |
| fondo 720p · x264 `medium` CRF 21 | 11,8 s | 12,0 MB | 0,9851 | 36,5 | 36,1 |
| fondo 1080p (CQ 30) · NVENC p4 CQ 21 | 7,2 s | 21,1 MB | 0,9906 | 39,4 | 38,9 |
| fondo 1080p (CQ 30) · NVENC hq CQ 21 | 8,6 s | 27,8 MB | 0,9906 | 39,5 | 39,1 |
| vídeo original · NVENC hq CQ 21 | 8,8 s | 32,2 MB | 0,9959 | 44,5 | 42,8 |

Afinar el codificador no mejora nada medible; lo que pierde calidad es el fondo de 720p
recomprimido. `decisiones/014`: el paquete guarda el original (`master.mp4`) para exportar.

## Antes y después, con el código nuevo

`karaoke background` sobre el mismo clip (ahora guarda `background.mp4`, 5,5 MB, y `master.mp4`,
27,8 MB, copiado sin recodificar) y `render()` con sus opciones por defecto (NVENC p4 CQ 21):

| Formato | Paquete | Tiempo | Tamaño | SSIM | XPSNR | XPSNR en la letra |
|---|---|---|---|---|---|---|
| 16:9 | sin original (antes) | 7,4 s | 22,7 MB | 0,9866 | 36,9 | 36,9 |
| 16:9 | con original | 7,7 s | 25,8 MB | 0,9951 | 43,3 | 41,7 |
| 9:16 | sin original (antes) | 9,0 s | 20,1 MB | 0,9936 | 41,5 | 42,9 |
| 9:16 | con original | 9,6 s | 22,0 MB | 0,9964 | 45,1 | 44,8 |
