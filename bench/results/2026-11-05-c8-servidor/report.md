# Servidor · karaokes de punta a punta en la RTX 3050

- Fecha: 2026-11-05
- Equipo: RTX 3050 Laptop (4 GB), Ryzen 7 5800H, WSL 2 con unos 7,6 GB de RAM; servidor
  `karaoke-server serve` con el motor de verdad, datos en un disco (no en `/tmp`)
- Cada trabajo corre en su propio proceso dentro de un *scope* de systemd con `MemoryMax`
- Tiempos por fase: los que guarda el servidor en `jobs.stage_seconds`; RAM y VRAM: muestreo cada
  0,5 s (`nvidia-smi` y `/proc/meminfo`) mientras corría cada trabajo

## Canciones

| Canción | Licencia | Cómo entró | Letra | Duración |
|---|---|---|---|---|
| «un aire» (Pantis), FLAC de 58 MB | CC BY-NC-SA 4.0 | subida (multipart) | dada (`bench/sets/gl`) | 287 s |
| «laverca» (Clo Plas), MP3 de Internet Archive | CC BY-SA 4.0 | enlace directo, descargado con yt-dlp | sin letra: transcrita | 313 s |

## Tiempos

| Fase | «un aire» (con letra) | «laverca» (sin letra) | Segundos por segundo de canción |
|---|---|---|---|
| descarga | — | 25,5 s | depende de la red |
| separar (incluye decodificar) | 66,4 s | 72,2 s | 0,22–0,23 |
| transcribir (HiTZ, gallego) | — | 22,5 s | 0,07 |
| alinear | 10,9 s | 12,1 s | 0,04 |
| audio del paquete (sonoridad y m4a) | 31,5 s | 33,9 s | 0,11 |
| **total** | **106 s** | **166 s** (141 s sin la descarga) | |
| total para 4 min | 89 s | 108 s sin la descarga | |

Exportar el MP4 1080p (16:9, tema `clasico`, NVENC) de «un aire»: **30 s** (25 s para 4 min).

Meta de `00-vision.md` §1: canción de 4 min en ≤ 2 min, con letra o sin ella, y MP4 de 4 min en
≤ 1 min. Se cumplen las dos a través del servidor, con la carga de los modelos incluida.

Una segunda pasada de «laverca» por enlace, una hora después y tras las baterías de pruebas, tardó
227 s: todas las fases fueron más lentas (separar 108 s, transcribir 36 s, alinear 15 s, audio 38 s;
también el audio, que solo usa la CPU). El código de esas fases no había cambiado; lo más probable es
el estado del portátil (calor o modo de energía), pero no se comprobó. A ese ritmo, una canción de
4 min sin letra tardaría unos 150 s sin la descarga: **por encima de la meta de 2 min**. Ojo al
medir: conviene hacerlo con el portátil enchufado y frío, y repetir.

## Memoria

| Trabajo | VRAM pico | RAM usada en la máquina, pico (base 1,7 GB) | Memoria del *scope*, pico |
|---|---|---|---|
| «un aire» | 2,8 GB | 3,9 GB | 3,6 GB |
| «laverca» | 2,8 GB | 4,9 GB | 4,2 GB |
| exportar MP4 | 0,2 GB | 1,8 GB | 0,3 GB |

La memoria del *scope* cuenta también la caché de los ficheros que escribe el trabajo; la RAM
propia del motor es la subida sobre la base: 2,2 GB con letra y 3,3 GB sin ella. Meta de
`00-vision.md` §1: ≤ 3 GB de VRAM y ≤ 4 GB de RAM por paso. Se cumple. Un solo trabajo de GPU a la
vez: la máquina nunca pasó de 5 GB de los 7,6 GB.

## Cancelar a mitad de la separación

Tras 20 s separando, `DELETE /api/jobs/{id}`: el proceso del trabajo terminó en **0,3 s**, la VRAM
volvió a **0 MiB**, no quedó ningún proceso ni ninguna unidad `karaoke-*` de systemd, la carpeta
temporal quedó vacía y el trabajo pasó a `cancelled` con `can_retry` (la entrada se guarda para
reintentar sin volver a subirla).

## Lo que se cambió con esto

- Los valores iniciales de la estimación de progreso (`karaoke_server.jobs.progress.DEFAULTS`)
  pasan a los medidos aquí. Con ellos, el total estimado al empezar habría sido 110 s para «un
  aire» (real 106 s) y 167 s para «laverca» (real 166 s); con los anteriores salía 123 s y 200 s.
  Tras tres trabajos de una fase, el servidor usa la mediana de lo que tardó en esta máquina.
- Los títulos que vienen de un nombre de fichero (enlaces directos y subidas sin etiquetas) pierden
  el número de pista y los guiones bajos: «2_laverca» → «laverca».

## Por debajo de lo mejor

- El paso de audio del paquete se lleva 32–34 s, casi un tercio del total con letra: mide la
  sonoridad tres veces con `loudnorm` (mezcla y dos pistas, 6,3 s cada una para 287 s) y codifica
  dos m4a (5,5 s cada uno), todo en serie. Medido a mano con ffmpeg: las tres medidas a la vez
  tardan 8,8 s y las dos codificaciones a la vez 5,6 s, unos 14 s en total frente a 30 s. Es del
  motor (área C3), no del servidor.
- La descarga de Internet Archive (12,9 MB) tardó 25 s: es la red del sitio, no yt-dlp.
