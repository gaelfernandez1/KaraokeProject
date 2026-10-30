# 007 · Subtítulos animados: una maquetación, dos pinceles (tema 1.1.0)

- **Fecha**: 30/10/2026
- **Estado**: propuesta (área C5); se aprueba con su PR
- **Afecta a**: C6 (el MP4 usa el ASS), C7 (integra el componente y elige tema), C4 (los tiempos que
  se pintan), C8 (sirve los temas y las fuentes con la web)

## Contexto

La letra tiene que verse bonita y cómoda para cantar, ir exactamente al ritmo del canto y verse igual
en el navegador (móvil, portátil, tele) que en el MP4. El plan proponía un componente web y un
generador ASS a partir del mismo `karaoke.json` y tema.

## Qué se miró

- **Reproductores de letra actuales**: los de las apps de música (lista que sube, máscara de
  degradado por línea, palabras largas que brillan) y los karaokes clásicos (dos filas fijas que se
  turnan, barrido por sílaba, puntos de cuenta atrás).
- **Percepción de la sincronía** (ITU-R BT.1359): una imagen atrasada se nota desde unos 45 ms; una
  adelantada, no hasta unos 125 ms.
- **Legibilidad a distancia**: las guías de TV piden como mínimo ~3 % de la altura para texto
  normal; para leer cantando a 3 m hace falta bastante más, con contorno o caja sobre cualquier fondo
  y márgenes del 5 %.
- **libass 0.17** (el de ffmpeg 8): `\kf` barre cada sílaba en su anchura real; las fuentes
  variables no son fiables, así que se usan instancias fijas con `fontsdir`.

## Enfoques comparados

| | Web | MP4 | Igualdad | Veredicto |
|---|---|---|---|---|
| A. Maquetación compartida + DOM + ASS | componente con DOM | ASS + libass | misma maquetación (mismas reglas y mismas métricas de fuente), barrido equivalente | **elegido** |
| B. libass también en la web (WASM) | ASS en el navegador | libass | idéntica | exige hilos de WASM y cabeceras COOP/COEP, resolución fija y regenerar el ASS en el navegador para el editor |
| C. Capturar la web para el MP4 | componente | capturas de Chromium | idéntica | 7200 capturas 1080p no caben en el minuto de meta del MP4 y gastan mucha RAM |
| D. Canvas compartido (también en Node) | canvas | canvas en Node | casi idéntica | mucha maquinaria nueva; peor texto y accesibilidad en la web |

## Decisión

- **Una maquetación con dos copias idénticas**: `karaoke_engine.subtitles.layout` (Python, la
  referencia) y `web/src/lib/lyrics/layout.ts`. Ambas miden con la tabla de anchos de la fuente
  (`*.metrics.json`), no con el motor de texto de cada uno, y los casos de
  `fixtures/lyrics-layout/` fallan si se separan.
- **Dos modos**: páginas (filas fijas que se turnan; por defecto) y desplazamiento (lista que sube).
- **Barrido con los tiempos del documento**, sin retoques en el renderizador; todo va 0,05 s por
  delante del sonido (`animation.anticipation`).
- **Cuenta atrás** tras pausas de 5 s o más, **barra de progreso** en pausas largas, **coros** más
  pequeños, entre corchetes y bajo su línea principal, **color por cantante**.
- **Tres temas** con fuentes OFL incluidas: `clasico` (por defecto), `moderno` y `contraste`.
- **Contrato del tema 1.1.0** (este área es su dueña): campos nuevos, todos con valor por defecto, así
  que un tema 1.0.0 sigue valiendo: `layout.mode`, `margin`, `min_row_chars`, `max_rows`,
  `outline_width`, `shadow_offset`, `shadow_blur`; `colors.singers`; `backing` (`scale`,
  `brackets`, `opacity`); `animation.lead_in`, `hold`, `transition`, `anticipation`,
  `countdown_dots`, `countdown_step`, `break_bar_min`.

## Resultados

- La web y libass coinciden a 1–3 px en la misma pantalla (antes de corregir el centrado vertical,
  libass pintaba unos 5 px más abajo: centra con las métricas `win` y los navegadores con `hhea`).
- 60 fps con la CPU de un móvil simulada 4 veces más lenta (mediana y p99 de 16,7 ms por fotograma).
- Pruebas: maquetación (Python y TS con los mismos casos), ASS (tiempos sin deriva, un fotograma de
  libass con el borde del barrido en su sitio), componente en Chromium a tamaño de móvil, portátil y
  tele.

## Consecuencias

- C6: `build_ass(doc, theme, width, height)` y `fonts_dir()` (para `fontsdir`); `karaoke preview`
  enseña cómo quemarlo con ffmpeg. Vale para 16:9 y 9:16.
- C7: `<Lyrics doc theme clock />` de `#lib/lyrics`, con `normalizeDoc` para paquetes 1.0.0; el tema
  lo elige la app (`THEMES`). `/proba-letra` es una página de prueba que C7 puede quitar.
- Quien cambie la maquetación cambia las dos copias y regenera los casos.
- Los tipos TS del tema marcan como obligatorios los campos nuevos (siempre se escriben): un tema
  1.0.0 leído en TS necesita sus valores por defecto antes de usarse.
- Pendiente: una cuenta atrás a tempo necesitaría los pulsos de la canción en el documento.
