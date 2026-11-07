# 014 · Descargas a la vista y vídeo original para el MP4

- **Fecha**: 07/11/2026
- **Estado**: aceptada (rama `v3/descargar-video`, con el OK del dueño el 07/11/2026)
- **Afecta a**: C1 (contrato 1.2.0: `video.master`), C6 (`extract_master`, el export usa el
  original), C8 (enlaces hasta 1080p, `GET`/`DELETE /api/songs/{id}/exports`, nombre de las
  descargas, `song_id` de los trabajos de vídeo), C7 (panel «Descargar» del reproductor)

## Contexto

El dueño preguntó si se puede descargar una canción ya procesada. Se podía, pero estaba escondido:
las descargas vivían al final del panel «Son», el MP4 solo aparecía en la tarjeta del trabajo en
«Crear» (y, al quitarla, en ningún sitio) y los ficheros se bajaban como `instrumental.m4a` o
`vocals.m4a`, sin el título. Además, en el servidor real los trabajos de vídeo no llevaban
`song_id`, así que el botón de descarga de «Crear» no salía nunca (el simulador sí lo rellenaba).
El dueño pidió poder descargar el resultado final en MP4 **con buena calidad**.

## Qué se miró

La calidad del MP4 actual con una referencia sin pérdidas (x264 `-qp 0` con el vídeo original
de fondo) y SSIM y XPSNR de ffmpeg (este ffmpeg no trae VMAF), en un clip 1080p a 50 fps con
mucho movimiento (`bench/results/2026-11-07-export-calidad/`):

| Variante (16:9) | Tamaño | XPSNR |
|---|---|---|
| actual: fondo 720p (CQ 30) y NVENC p4 CQ 21 | 22,7 MB | 36,9 dB |
| NVENC p6 + `tune hq` + multipase + AQ + *lookahead* | 28,7 MB | 37,0 dB |
| fondo recodificado a 1080p (CQ 30) | 21,1 MB | 39,4 dB |
| vídeo original sin recomprimir | 32,2 MB | 44,5 dB |

El codificador no es el cuello de botella: lo es el fondo, que se descargaba a 720p como mucho,
se recomprimía para la web y luego se ampliaba a 1080p.

## Enfoques comparados

| Tema | Opciones | Elegido |
|---|---|---|
| Calidad del fondo del MP4 | afinar NVENC · fondo de la web a 1080p · guardar el original aparte | **guardar el original** (`master.mp4`): +6,3 dB en 16:9 y +3,6 dB en 9:16; la web sigue con su 720p ligero (móviles, túnel, copias sin conexión) |
| Cómo se guarda | recodificar siempre · copiar siempre · copiar si se puede | **copiar el flujo** (un segundo, sin pérdida) si el lado corto es ≤ 1080, el códec es H.264, HEVC, VP9 o AV1 y no pasa de 16 Mb/s; si no, H.264 a 1080 con CQ 18 |
| Enlaces | 720p · 1080p · lo mejor | **hasta 1080p**: el MP4 es 1080p; más sería disco sin ganancia |
| Dónde se descarga | panel «Son» · página aparte · panel propio | **botón «Descargar» en la barra del reproductor** con su panel: vídeos hechos, el que se está haciendo con su barra, hacer otro, sonido y letra, guardar sin conexión |
| Lista de vídeos | en el resumen de la canción · ruta propia | **`GET /api/songs/{id}/exports`** (con miniatura, tamaño, fecha y `outdated` si la letra se corrigió después) y `DELETE` para el dueño |
| Nombre de los ficheros | el del disco · lo decide el servidor · lo pide la web | **lo pide la web** (en su idioma: «Artista - Título (karaoke).mp4», «(sen voz).m4a»…) con `?download=1&name=`; el servidor lo limpia y le pone la extensión real; además, el atributo `download` |

## Decisión

- Contrato **1.2.0**: `video.master` (opcional), «el mismo vídeo a su calidad, para el MP4». Un
  lector de 1.1 lo conserva (`extra="allow"`).
- `karaoke make` y `karaoke background` guardan `master.mp4` junto a `background.mp4`; si el
  original falla, queda el fondo y el karaoke se hace igual. `karaoke render` usa el original si
  lo hay. Los paquetes viejos no lo tienen y exportan como antes (rehacer la canción desde su
  enlace lo añade).
- Los enlaces bajan hasta 1080p (`FORMAT` de yt-dlp).
- El trabajo de vídeo lleva `song_id` desde que se pide.

## Resultados

- Calidad con el código real (clip de 27 s): 16:9 de 36,9 a 43,3 dB XPSNR (SSIM 0,987 → 0,995) y
  9:16 de 41,5 a 45,1 dB; el MP4 pesa un 9–14 % más y tarda lo mismo (7,4 → 7,7 s).
- Coste: el original ocupa lo que traía (un vídeo de YouTube a 1080p, 2–5 Mb/s: 60–150 MB por
  canción de 4 min) y la descarga por enlace tarda algo más.
- Tests: contrato, motor (copia sin recodificar, bajada a 1080, códecs viejos, bitrate enorme),
  servidor (lista, borrar, nombres seguros, `song_id`, importar con original), web (cliente,
  nombres, simulador) y navegador en móvil, portátil y tele, y contra el servidor real.

## Al probarlo el dueño (07/11, tarde)

«Se queda en 0 %». Los registros contaron esto: su servidor seguía con el código viejo pero ya
servía la web nueva, el panel no veía sus trabajos (sin `song_id`) y pulsó «Facer vídeo» seis
veces; tras reiniciar había siete exportaciones iguales en cola y el panel solo mostraba la última,
en espera, como «0 %». Además, al reconectar seis reproductores a la vez, dos recibieron un 500:
las dependencias de FastAPI escritas como `def` corren en hilos y usaban la conexión de SQLite del
bucle de eventos (`sqlite3.InterfaceError`). Arreglos, cada uno con su test: dependencias `async`
(y un test que recorre todas las rutas), una exportación igual pendiente devuelve el mismo trabajo,
los trabajos viejos toman su canción de la petición, «Á espera da tarxeta gráfica» en lugar de
«0 %» y los botones esperan la respuesta. La velocidad no era el problema: 3 min de canción en
unos 70 s con «Moderno» (≈30 % más que «Clásico»).

Pidió también **elegir el volumen de la voz al descargar**: `vocals` (0–1, en centésimas) en
`POST /api/songs/{id}/exports`, un fichero por nivel (`…-v30.mp4`), el nivel en la lista y en el
nombre del fichero, y un control en el panel que empieza en «sen voz» (la voz guía del reproductor
viene al 15 % por defecto: copiarla haría vídeos con voz sin pedirlo). La mezcla ya existía en
`render` (con limitador): con voz al 100 % el clip pasa de −17,8 a −15,7 LUFS.

## Pendiente

- El dueño: probar el panel en su móvil, portátil y tele, y rehacer desde su enlace las canciones
  que quiera exportar con el vídeo original.
