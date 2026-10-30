# Vídeo

Fondos de las canciones y exportación MP4 con la letra animada. Las decisiones están en
`docs/plan-v3/decisiones/008-video.md`; los tiempos, en `bench/results/2026-10-30-c6-render/`.

## El fondo de un paquete

`karaoke make` guarda lo que la canción trae para la vista:

- **`background.mp4`** si el fichero tiene vídeo (un videoclip de YouTube, por ejemplo): H.264 que
  reproduce cualquier móvil o tele, como mucho 1280×720 y 30 fps, un fotograma clave por segundo (los
  saltos son instantáneos), el índice al principio y sin audio. Va en `video.background`.
- **`cover.jpg`**: la carátula incrustada si la hay (mp3, m4a) o, si no, un fotograma a un tercio
  del vídeo. Va en `cover`.

Para un paquete ya hecho (o para cambiarle el fondo):

```bash
uv run karaoke background <paquete> <vídeo, canción con carátula o imagen>
```

Código: `karaoke_engine.video.media` (`probe_video`, `extract_background`, `extract_cover`,
`add_background`, `mean_luma`).

## Exportar el MP4

```bash
uv run karaoke render <paquete> [--theme clasico] [--aspect 16:9|9:16] [--background auto]
                                [--vocals 0.3] [--dim 0.8] [--size 1280x720] [-o video.mp4]
```

- **Fondo** (`--background`): `auto` usa el vídeo del paquete, si no su portada y si no un
  degradado con los colores del tema; también `video`, `cover`, `gradient` o la ruta de un vídeo o
  una imagen. Un fondo con la misma forma que el vídeo lo llena; con otra forma se ve entero sobre
  una copia ampliada, desenfocada y más oscura, nunca deformado ni cortado. En 9:16 se sube para
  dejar abajo la letra. Una imagen se mueve muy despacio.
- **Legibilidad**: el fondo se oscurece según su brillo (`--dim` lo fija a mano: 1 es sin
  oscurecer) y una franja oscura degradada va detrás de la letra.
- **Letra**: el ASS de los subtítulos (`docs/subtitulos.md`) con la misma maquetación que la web,
  más **título y artista** al principio (si la primera línea tarda 4 s o más) y **créditos** al
  final (título, artista y el primer párrafo de `LICENSE`, si quedan 4 s o más).
- **Audio**: el instrumental tal cual; con `--vocals`, mezclado con la voz guía a ese nivel.
- **Miniatura**: junto al vídeo, un `.jpg` de 1280 px con el título sobre el fondo.
- **Codificación**: NVENC en la GPU y, si no se puede, x264.

Una canción de 4 min sale en 27–45 s en la RTX 3050 (el fondo de vídeo es el más caro).

Código: `karaoke_engine.video.render` (`render`, `title_events`, `credits_text`),
`karaoke_engine.video.graph` (el grafo de filtros del fondo) y `karaoke_engine.video.encode`.

## En la web

`BackgroundSync` (`web/src/lib/video/background.ts`) mantiene un `<video>` mudo al paso del audio:
lo arranca y lo para con el reloj, salta si se desvía más de 0,3 s y, entre 40 ms y 0,3 s, acelera
o frena un 5 % como mucho hasta alcanzarlo. Si el vídeo es más corto que la canción, da la vuelta.

```ts
const sync = new BackgroundSync(videoElement, { now: () => engine.now(), get playing() { return engine.playing; } });
// en cada fotograma:
sync.tick();
```

`/proba-letra` lo enseña con el fondo como en el MP4 (portada desenfocada detrás, vídeo entero,
oscurecido, franja bajo la letra). El servidor de desarrollo sirve los vídeos con peticiones Range,
sin las que un navegador no puede saltar en un vídeo; el servidor de verdad (C8) debe hacer lo mismo.

## Pruebas

```bash
uv run pytest packages/engine/tests/test_video_*.py packages/engine/tests/test_make.py
pnpm --dir web test                 # BackgroundSync
pnpm --dir web test:e2e             # el vídeo de fondo sigue al reloj (Chromium)
```
