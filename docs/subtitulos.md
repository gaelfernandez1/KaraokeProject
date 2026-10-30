# Subtítulos animados

Cómo se pinta la letra de un `karaoke.json`, igual en el reproductor web y en el MP4. Las decisiones
y lo que se descartó están en `docs/plan-v3/decisiones/007-subtitulos.md`.

## La idea

Lo que decide **qué se ve y cuándo** (en qué fila va cada línea, dónde se corta, a qué tamaño, cuándo
entra y sale, la cuenta atrás) es un único algoritmo de maquetación con dos copias idénticas:

- `karaoke_engine.subtitles.layout` (Python), la referencia, que usa el MP4;
- `web/src/lib/lyrics/layout.ts`, la misma lógica para el navegador.

Las dos miden el texto con la misma tabla de anchos de la fuente (`*.metrics.json`), así que cortan
las líneas en los mismos sitios en cualquier navegador y en el vídeo. Los casos compartidos de
`fixtures/lyrics-layout/` obligan a que den lo mismo (tolerancia de 1e-6): un test de Python falla si
están viejos y uno de la web, si la web no coincide.

Lo que decide **cómo se pinta** cada fila lo hace cada renderizador con su herramienta:

- la web, con DOM: dos copias del texto por fila, la de abajo «por cantar» y la de arriba «cantada»,
  recortada (`clip-path`) hasta el borde del barrido;
- el MP4, con eventos ASS que libass dibuja: `\kf` por sílaba (barrido) o `\k` por palabra.

Medido lado a lado, la web y libass coinciden a 1–3 px (`scripts/side_by_side.py`).

## Qué se ve

- **Páginas** (`layout.mode = "pages"`, el clásico): `visible_lines` filas fijas que se turnan.
  Mientras se canta una línea, la siguiente ya está escrita en la otra fila; al acabar una línea
  (+`hold`), su sitio lo toma la que va `visible_lines` lugares después, siempre al menos 0,5 s antes
  de cantarla. El texto no se mueve mientras se lee.
- **Desplazamiento** (`"scroll"`, el moderno): la línea que se canta queda en el ancla (42 % de la
  altura con `position = "center"`), la anterior atenuada encima y las siguientes debajo, más tenues
  cuanto más lejos. La lista sube en `transition` segundos y se para 0,25 s antes de la línea
  siguiente.
- **Bloques y pausas**: un hueco de `countdown_min_gap` segundos (5) entre líneas parte la canción en
  bloques. Un bloque aparece `lead_in` segundos (3) antes de cantarse, con una **cuenta atrás** de
  `countdown_dots` puntos que se apagan de derecha a izquierda, uno cada `countdown_step` segundos,
  sobre el principio de la primera línea. En las pausas de `break_bar_min` segundos (8) o más, una
  **barra** dice cuánto falta (solo en páginas).
- **Barrido**: cada sílaba (`parts`) o palabra sin partes se rellena de izquierda a derecha en su
  tiempo real; entre palabras, espera. Con `fill = "word"`, cada palabra cambia de golpe al empezar.
  Todo va `anticipation` segundos (0,05) por delante del sonido: se nota mucho antes una letra
  atrasada que una adelantada, y así se compensa el fotograma que tarda en pintarse.
- **Coros** (`role = "backing"`): más pequeños (`backing.scale`), entre corchetes y algo
  transparentes, en una fila bajo la línea principal con la que suenan (la que más se solapa, o la
  anterior si acabó hace menos de 1,5 s); si no tienen ninguna cerca, van solos.
- **Cantantes**: con dos o más, cada uno rellena con su color (`singer.color` o la paleta
  `colors.singers` del tema).
- **Cortes**: una línea que no cabe se parte en dos filas equilibradas, mejor tras una coma o un
  punto; si aun así no cabe, se encoge (hasta 0,6).
- **Tamaño**: `font_size` × alto de la pantalla, pero no más del que deja `min_row_chars` letras por
  fila en el ancho útil; márgenes de `margin` (5 %) por cada lado.

## Temas

Los temas y sus fuentes están en `packages/engine/src/karaoke_engine/subtitles/themes/` (una sola
copia: la web los importa de ahí).

| id | Modo | Fuente | Aspecto |
|---|---|---|---|
| `clasico` | páginas | Nunito Black | blanco con contorno oscuro, cantado en amarillo, sombra |
| `moderno` | desplazamiento | Inter ExtraBold | por cantar blanco tenue, cantado blanco pleno, halo suave |
| `contraste` | páginas | Atkinson Hyperlegible Next ExtraBold | amarillo sobre caja negra, más grande, palabra a palabra |

Para añadir uno, copia un `.json`, cambia `id` y `name` y ajusta los valores (el esquema está en
`schemas/theme.schema.json`). Para otra fuente, añádela a `FONTS` en `scripts/build_fonts.py`,
ejecuta `uv run --with fonttools --with brotli python scripts/build_fonts.py` y añádela también a
`web/src/lib/lyrics/themes.ts`. Las fuentes van con su licencia OFL y su procedencia en
`themes/fonts/README.md`.

## Web

```svelte
<script>
	import { Lyrics, THEMES, normalizeDoc } from '#lib/lyrics';
</script>

<Lyrics doc={normalizeDoc(doc)} theme={THEMES.clasico} clock={engine} />
```

`clock` es cualquier `PlaybackClock`: el `AudioEngine` de `#lib/audio/engine.js`, que ya descuenta la
latencia de salida. El componente ocupa su contenedor (`position: absolute; inset: 0`) y se adapta a
su tamaño. Cada fotograma solo escribe opacidades, el borde del barrido y el desplazamiento de la
lista: con la CPU de un móvil simulada 4 veces más lenta, mediana y p99 de 16,7 ms por fotograma,
ninguno por encima de 20 ms.

Página de prueba: `pnpm --dir web dev` y `/proba-letra` (elige canción, tema y tamaño de pantalla,
y reproduce con audio). `?t=12.3` congela la letra en ese instante y `?fondo=liso` quita el fondo.

## Vídeo

```bash
uv run karaoke subtitles <paquete> [--theme clasico] [--size 1920x1080] [-o letra.ass]
uv run karaoke preview <paquete> [--theme] [--size 1080x1920] [--start 20 --duration 30] [-o p.mp4]
```

`subtitles` escribe el ASS; `preview`, un MP4 rápido con la letra sobre un fondo liso, el
instrumental y la voz guía (para comprobar a ojo y oído). Para quemar el ASS en un vídeo hace falta
pasarle a libass las fuentes: `subtitles=letra.ass:fontsdir=<themes/fonts>`
(`karaoke_engine.subtitles.themes.fonts_dir()`). Desde Python: `build_ass(doc, theme, width, height)`.

## Pruebas

```bash
uv run pytest packages/engine/tests/test_subtitles_*.py      # maquetación, ASS y un fotograma de libass
pnpm --dir web test                                           # maquetación TS (casos compartidos), escena, barrido
pnpm --dir web exec playwright install chromium --only-shell  # una vez
pnpm --dir web test:e2e                                       # el componente en Chromium: móvil, portátil y tele
uv run python scripts/side_by_side.py fixtures/packages/demo-sintetico --times 4.5,13
```

Chromium necesita `libnss3` y `libnspr4`. Con permisos de administrador:
`sudo pnpm --dir web exec playwright install-deps chromium`. Sin ellos, se pueden sacar de los
paquetes de Ubuntu a una carpeta propia (`apt-get download libnspr4 libnss3` y `dpkg -x`) y
apuntar `LD_LIBRARY_PATH` a su `usr/lib/x86_64-linux-gnu`.

Tras cambiar la maquetación a propósito: `uv run python -m karaoke_engine.subtitles.conformance
--write` y repetir el cambio en `layout.ts` hasta que `pnpm --dir web test` pase.
