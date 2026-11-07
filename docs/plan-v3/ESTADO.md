# Plan v3 · Estado

Tablero de las áreas de trabajo. Cada área actualiza **su fila** tras cada hito
(no solo al final) y añade lo que deja pendiente para otras. Orden: `00-vision.md` §9.

| Conv. | Área | Estado | Rama | Último hito | Interfaces que expone | Pendiente para otras |
|---|---|---|---|---|---|---|
| C1 | Arquitectura, repo y cimientos | hecho | `v3/c1-cimientos` (PR #1) | workspace uv, contratos v0, web SvelteKit, CI, entorno GPU comprobado | `karaoke_contracts` (`KaraokeDoc`, `Theme`, `validate_doc`, `validate_package`, `load_doc`, `dump_doc`); `schemas/*.schema.json`; `#lib/contracts` (tipos TS + `PlaybackClock`); `karaoke_engine.steps` (`Separator`, `Transcriber`, `Segmenter`, `Aligner`); CLI `karaoke validate|demo`; `fixtures/packages/demo-sintetico`; `fixtures/themes/basico.json`; `make ci|contracts|check-env` | C2: crear `packages/bench` y su comando; C5/C7: pueden empezar con el demo sintético |
| C2 | Banco de pruebas y métricas | hecho (PR #2, en `main` el 29/10) | `v3/c2-banco` | banco completo: JamendoLyrics (79 y rápido 20) y 5 gallegas con licencia libre, métricas, runner con caché, informes, comparación, línea base medida y metas fijadas (`decisiones/003`), página de revisión de oído y 3 paquetes reales; falta que el usuario valide de oído las 5 referencias gallegas | `karaoke-bench fetch\|run\|compare\|draft\|review\|realign\|package`; pipelines TOML en `bench/pipelines/` (cualquier clase que cumpla `karaoke_engine.steps`); `karaoke_bench.baseline` (Demucs, faster-whisper, alineador CTC); guía en `docs/benchmark.md` | ver notas C2 → C3, C4, C5/C7 |
| C3 | Audio: separación y sonido | hecho (PR #3, en `main` el 30/10) | `v3/c3-audio` | separador elegido con el banco (Mel-Band RoFormer de Kim en trozos de 8 s, `decisiones/004`), audio del paquete a −14 LUFS en m4a, motor de audio web con voz guía, tono, reloj con latencia y calibración, y página `/proba-audio`; falta que el usuario lo pruebe en aparatos reales y escuche la separación | `karaoke_engine.separation.RoformerSeparator`; `karaoke_engine.audio` (`decode`, `measure`, `plan_gain`, `package_audio`, `convert_package`); CLI `karaoke audio`; `#lib/audio/engine.js` (`AudioEngine`, cumple `PlaybackClock`), `clock.js` (`SongClock`), `calibration.js`; guía en `docs/audio.md` | ver notas C3 → C4, C5/C7, C8 |
| C4 | Transcripción y sincronización | hecho (PR #4, en `main` el 30/10); el usuario escuchó dos canciones suyas y suenan bien | `v3/c4-sincronia` | `karaoke make` de punta a punta (con letra, `--lrclib` o sin letra), alineador nuevo, sílabas, coros (contrato 1.1.0) y cantantes; con letra: jamendo 98,8 % a ≤ 0,3 s, media 0,093 s, inglés 97,6 %, gallego 98,6 %; sin letra: WER jamendo 23,2 %, gallego 26,5 % (meta 25 %); 0 cambios de idioma; `make` de 4 min: ~91 s con letra, 105–155 s sin letra (`decisiones/005` y `006`) | `karaoke make`; `karaoke_engine.make.make_package`; `karaoke_engine.align` (`LyricsAligner`, `parse_lyrics`, `syllables`…); `karaoke_engine.transcribe` (`WhisperTranscriber`, `LineSegmenter`); `karaoke_engine.lyrics_lookup`; `steps.TextAligner`; contrato 1.1.0 (`Line.role`); guía `docs/lyrics-sync.md` | ver notas C4 → C2, C3, C5/C7, C8 |
| C5 | Subtítulos animados | hecho (PR #5, en `main` el 30/10); el usuario se queda con `clasico` y `moderno` (`contraste`, como opción); falta probarlo en su tele | `v3/c5-subtitulos` | maquetación única en Python y TS con casos compartidos, modos páginas y desplazamiento, cuenta atrás, barra de pausa, coros y colores por cantante; componente web a 60 fps; generador ASS que coincide con la web a 1–3 px; 3 temas con fuentes OFL; tema 1.1.0 (`decisiones/007`) | `karaoke_engine.subtitles` (`build_layout`, `build_ass`, `load_theme`, `fonts_dir`, `render_preview`); CLI `karaoke subtitles\|preview`; `#lib/lyrics` (`Lyrics`, `THEMES`, `normalizeDoc`, `buildLayout`); página `/proba-letra`; guía `docs/subtitles.md` | ver notas C5 → C6, C7, C4 |
| C6 | Vídeo | hecho (PR #6, en `main` el 30/10); falta que el usuario elija el fondo por defecto | `v3/c6-video` | `make` guarda vídeo y portada; `karaoke render` 16:9 y 9:16 con fondo de vídeo, portada o degradado, oscurecido según su brillo, franja bajo la letra, título, créditos y miniatura, en 27–45 s para 4 min con NVENC (`decisiones/008`); vídeo de fondo sincronizado en la web | `karaoke_engine.video` (`render`, `add_background`, `extract_background`, `extract_cover`, `choose_background`); CLI `karaoke render\|background`; `#lib/video/background.js` (`BackgroundSync`); guía `docs/video.md` | ver notas C6 → C7, C8, C4 |
| C7 | Frontend | hecho a falta del OK del usuario y de probarlo en su móvil, portátil y tele | `v3/c7-frontend` | app completa contra un servidor simulado: biblioteca de carteles, reproductor (voz guía, tono, retardo, descargas, vídeo), crear con progreso en vivo, fiesta con tele y móviles (turnos, mando, QR), editor de letra y tiempos, ajustes con calibración, PWA sin conexión, gl/es/en; revisada con capturas en cuatro rondas de un revisor independiente y una revisión de código (`decisiones/010`) | rutas `/`, `/crear`, `/cantar/<id>`, `/editar/<id>`, `/festa`, `/festa/<código>`, `/axustes`; `#lib/api` (cliente), `#lib/party` (turnos `upcoming`, conexión SSE), `#lib/player` (`PlayerSession`, `Stage`), `#lib/editor/ops`; servidor simulado `web/dev/mock/` (API esperada en `decisiones/010`); guía `docs/web.md` | ver notas C7 → C10, C3/C5/C6 |
| C8 | Backend, servidor y despliegue | hecho a falta del OK del usuario y de sus pasos en Windows (red `mirrored`, cortafuegos, Tailscale Serve, arranque) | `v3/c8-servidor` (encima de C7) | `karaoke-server`: FastAPI en un proceso con dos sockets (casa 8765, túneles 8766), zonas de red y aparatos vinculados, cola de un trabajo de GPU a la vez con un proceso hijo por trabajo en un *scope* de systemd, subidas en streaming, enlaces con yt-dlp al día, progreso y tiempo restante con SSE, cancelar y reintentar, fiesta persistente, `doctor`, copias, arranque con Windows; OpenAPI y tipos TS generados; probado de punta a punta en la RTX 3050: 4:47 con letra en 106 s, 5:13 por enlace sin letra en 166 s, MP4 en 30 s, cancelar libera la GPU en 0,3 s (`decisiones/011`) | `karaoke-server serve|pair|devices|import|backup|prepare|openapi|doctor|autostart`; `make serve`; API en `schemas/openapi.json` (tipos en `web/src/lib/api/generated/`); `#lib/devices` (`owner`, `DevicePanel`); ruta `/vincular`; `pnpm --dir web test:e2e:server`; guía `docs/server.md` | ver notas C8 → C7, C3, C9, C10 |
| C9 | Calidad de código | hecho (PR #11, en `main` el 06/11) | `v3/c9-calidad` | `legacy/` fuera; auditoría por siete revisiones independientes: 1 fallo de seguridad alto y unos 40 fallos confirmados arreglados con test (fiesta que saltaba canciones, letras largas cortadas, pronombres mal juntados, cola de la GPU que moría, banco que infravaloraba el gallego…); puertas nuevas (ruff ampliado, deptry, import-linter, eslint con tipos, knip, zizmor, política de saltos en la CI con ffmpeg); tests en paralelo (167 s → 60 s, 4,9 → 2,8 GB); `make` −19 % (`decisiones/012`, `docs/quality.md`) | `make test-models`; `KARAOKE_STRICT_SKIPS`; fixture `ffmpeg` y marca `models` (`conftest.py`); `karaoke_engine.make.prepare_models`; `DELETE /api/parties/{code}` y evento SSE `ended`; `PartyConnection.ended`, `HostParty.end()`; `#lib/offline/fallback.js`; `pnpm perf:frames` | ver notas C9 → todas, C2, C3, C10 |
| C10 | Proyecto profesional | hecho (PR #12, en `main` el 06/11); release [v3.0.0](https://github.com/gaelfernandez1/KaraokeProject/releases/tag/v3.0.0) publicada | `v3/c10-profesional` | Proxecto Karaoke en Galego 3.0.0 (nombre elegido por el usuario): README en gallego, inglés y castellano con GIF, capturas y cifras del banco; guías técnicas de `docs/` en inglés y con nombres en inglés; `make install` (probado en limpio en la CI); versión única y releases en borrador desde el CHANGELOG; `NOTICE.md` y comprobador de licencias (`diffq`, no comercial, fuera); SECURITY, CONTRIBUTING, código de conducta, formularios y plantilla de PR; Dependabot; arquitectura e idiomas y modelos; paquete de demostración «laverca» (`decisiones/013`) | `scripts/release.py check\|set\|notes`; `scripts/licenses.py`; `scripts/check_links.py`; `scripts/install.sh` (`make install`); `--version` en las tres órdenes; workflow `release.yml`; `web/dev/brand.mjs` y `web/dev/readme-media.mjs`; `fixtures/packages/cloplas-laverca` | ver notas C10 → todas, C4 |

## Notas entre áreas

(Avisos que un área deja a otra: «C4 → C5: …». Borra los que ya estén atendidos.)

- Mantenimiento → C4, C2 (07/11, rama `v3/repeticiones`, `decisiones/016`): las repeticiones que
  la letra escribe una vez se cantan las veces que suenan. `align_segments(repeat_penalty=…)` deja
  volver a versos de la misma estrofa (`Segment.group`, `SegmentPath.repeats`), `best_path`
  devuelve la puntuación y el alineador elige con ella cuántos versos abarca cada «(xN)»
  (`parse_lyrics(text, scopes)`, `repeat_marks`); `LyricLine.stanza`; `LyricsAligner.version` = 14.
  El banco gana el conjunto `repeats` (`fetch --set repeats`). Mismo resultado en `jamendo`, `gl`,
  `quick`, `stress` y las privadas.

- Mantenimiento → C4, C7 (07/11, rama `v3/letra-pegada`, `decisiones/015`): la letra se pega
  tal cual viene de la web. `karaoke_engine.align.pasted.strip_page_text` quita lo que añade la
  página (recomendaciones y anuncios de Genius, créditos, enlaces, tiempos, acotaciones) y
  reescribe las etiquetas sin corchetes como cabeceras; `parse_lyrics` lo llama siempre y
  `make_package` con el título y el artista. `parse_lyrics` entiende además «Ela: …» (quién canta)
  y «Repite el coro» con otro nombre del estribillo. Mismo resultado en las 107 letras del banco;
  `LyricsAligner.version` = 13. En «Crear», el texto de ayuda de la letra lo dice.

- Mantenimiento → C1, C6, C7, C8 (07/11, rama `v3/descargar-video`, `decisiones/014`): contrato
  **1.2.0** con `video.master` (el vídeo original, hasta 1080p, solo para el MP4; `karaoke make` y
  `karaoke background` lo guardan con `extract_master` y `render` lo prefiere); los enlaces bajan
  hasta 1080p; API nueva `GET`/`DELETE /api/songs/{id}/exports` y `?download=1&name=` en `/media`;
  los trabajos de vídeo llevan `song_id` desde que se piden (antes el botón de descarga de «Crear»
  no salía con el servidor real); en la web, panel «Descargar» en el reproductor
  (`#lib/player/DownloadPanel`, `PlayerPanel`, `downloads.ts`) y «Son» solo con el sonido.
  Después: `vocals` en las exportaciones (un fichero por nivel), una exportación igual pendiente
  devuelve el mismo trabajo y **todas las dependencias de FastAPI son `async`** (las `def` corrían
  en hilos con la conexión de SQLite del bucle: 500 con varios reproductores; lo vigila
  `test_dependencies.py`).
- C1 → todas: las diez áreas del plan v3 están en `main` y la versión 3.0.0 está publicada
  (06/11). `main` solo acepta cambios por PR con la CI en verde (ruleset de GitHub).
- C10 → todas: una sola versión del producto (3.0.0) en los paquetes, la web y `CITATION.cff`;
  `make lint` comprueba que coinciden y que `CHANGELOG.md` tiene su entrada (`scripts/release.py`),
  la licencia de cada paquete instalado (`scripts/licenses.py`, con `--extra ml` también la de los
  modelos), shellcheck y los esquemas de los ficheros de GitHub y de `CITATION.cff`; un test
  rechaza enlaces de los `.md` a ficheros que no están en el repo. Lo que cambie para quien usa
  el proyecto va en `## [Unreleased]` del CHANGELOG; publicar: `docs/releasing.md`. Un modelo o
  una dependencia nuevos, en `NOTICE.md`. Las guías técnicas de `docs/` se escriben en inglés (las
  del plan, en castellano).
- C10 → C4: en el paquete de demostración («laverca», `fixtures/packages/cloplas-laverca`) la
  primera palabra («A», confianza 0,64) quedó en 3,98 s cuando se canta en 31,9 s, y «o», al final
  de esa línea, 2 s tarde: palabras de una letra con poca confianza en el borde de una línea saltan
  a la intro. Son 2 de 378 (el banco sigue en 99,8 %), pero se ven en la primera línea.
- C10 → C3: `diffq` (lo pide audio-separator para sus modelos Demucs; licencia no comercial) ya no
  se instala (`override-dependencies` en `pyproject.toml`); la separación con RoFormer no lo usa.
- C8 → C7: la API real es la de `decisiones/010` con añadidos (`decisiones/011`): `Job.error_code`,
  `overall`, `eta`, `can_retry`; errores `{detail, code}`; `/api/me`, vincular aparatos y
  `home_reachable`. Los tipos de `#lib/api` y `#lib/party` salen de `schemas/openapi.json` (`make
  contracts`). C8 tocó ficheros de C7 (lista en `decisiones/011`): si C7 cambia antes de fusionarse,
  hay que rehacer C8 encima. `pnpm --dir web test:e2e:server` prueba la web contra el servidor real.
  `e2e/app/player.spec.ts` («a song plays, pauses and jumps») falló una vez de 2 con toda la batería
  en paralelo; repetida sola, 36 de 36 bien. `e2e/app/editor.spec.ts` («a word is corrected…») es
  intermitente con toda la batería: las versiones de móvil y portátil guardan a la vez la misma
  canción del simulador y gana la última.
- C8 → C3: el paso `encode` de `make_package` (`package_audio`) tarda 30–34 s en una canción de 5
  min, casi un tercio del total con letra: tres `loudnorm` y dos codificaciones AAC en serie. En
  paralelo serían unos 14 s (medido a mano, `bench/results/2026-11-05-c8-servidor/`).
- C9 → todas: `make ci` pide ahora deptry (cada paquete declara lo que importa), import-linter
  (contratos → motor → banco/servidor; el proceso del servidor no importa torch ni modelos), ruff
  con `ASYNC/S/BLE/DTZ/…`, eslint con tipos en `web/src` y knip (`docs/quality.md`). Un test que
  use ffmpeg pide el fixture `ffmpeg`; uno que cargue modelos lleva `@pytest.mark.models`. En la CI
  cualquier otro salto es un fallo. `legacy/` ya no existe (etiqueta `v2-final`).
- C9 → C2: el banco empareja contra toda la referencia (el gallego subía del 98,6 % al 99,8 % sobre
  las mismas alineaciones), cuenta las canciones que fallan en la cobertura y mide el WER sin letra
  contra lo cantado. Pendiente tuyo: avisar al comparar ejecuciones con canciones distintas, que la
  caché sepa del código (hoy solo `version`), emparejar las transcripciones también por tiempo, y
  los menores de la revisión (normalización desalineada con `parse_lyrics`, «validada de oído» en
  referencias trianguladas, `drafting.py` con `KeyError` si falla el separador).
- C9 → C3: el audio del paquete ya mide y codifica en paralelo y mientras la GPU alinea (−20 s por
  canción). La separación va con la GPU al 92–100 %: más rápida solo con menos pasadas u otro
  modelo (decisión tuya, con el banco).
- C7 → C3/C5/C6: se usan `AudioEngine`, `<Lyrics>` y `BackgroundSync` sin cambios; `/proba-audio`
  se retiró (la sustituyen el reproductor y Axustes) y `/proba-letra` queda solo en desarrollo. Las
  portadas se pintan a dos tintas en el reproductor; el vídeo de fondo, como en el MP4.
- C1 → C3/C4: torch está en el extra `ml` desde el índice cu130 (torch 2.14.1). whisperx 3.8.6
  exige torch 2.8; si lo usáis, cambiad versión e índice en una decisión.
- C1 → C5/C7: Playwright necesitará navegadores (`pnpm exec playwright install chromium`) y quizá
  librerías del sistema (con sudo).
- C2 → C4: faster-whisper 1.2.1 (CTranslate2 4.8) es CUDA 12: precarga `libcublas.so.12` y recibe
  audio decodificado (ver `karaoke_bench/baseline/whisper.py`). Whisper `small` adivinando el idioma
  confunde el gallego (5 de 5) con noruego, coreano, latín o castellano; `large-v3-turbo` con el
  idioma dado, nunca (`decisiones/003`). El alineador CTC de la línea base llega a 4,6–5,9 GB de RAM:
  hay que bajarlo. Los
  borradores de las referencias gallegas salen del alineador con
  `proxectonos/Nos_ASR-wav2vec2-xls-r-300m-gl` y la letra de 3 canciones, de
  `proxectonos/whisper-large-v3-turbo-gl-v1.0`: si C4 usa esos modelos, sus cifras en `gl` pueden
  salir optimistas en las líneas que el usuario dio por buenas sin moverlas.
- C2 → C5/C7: hay 3 paquetes con canciones reales en `fixtures/packages/` (`cortez-feel-stripped`,
  `nandomalo-esencia`, `law-mere-nature`): se versionan `karaoke.json` y `LICENSE`; el audio se
  crea en local con el comando que trae el final de cada `LICENSE` (antes, una vez,
  `uv run karaoke-bench fetch --set jamendo`).
- C3 → C4: compara contra `bench/pipelines/sep-melkim-8s.toml` (separador elegido) además de
  `base-turbo`, y revalida la elección con tu alineador. Con Kim aún no se cumplen las metas de
  sincronía (97,5 % frente al 98 % en jamendo; inglés 94,4 % frente al 96 %). En gallego sin letra
  Kim salió 4,7 puntos peor (dentro del ruido, 2 canciones): repítelo cuando estén validadas.
  Kim usa 2,9 GB de VRAM: suelta el separador antes de cargar Whisper o el alineador.
- C3 → C5/C7: el reproductor usa `AudioEngine` (`#lib/audio/engine.js`); la letra sigue
  `engine.now()`, que ya descuenta la latencia de salida, la del cambio de tono y la calibración.
  El cambio de tono necesita HTTPS o `localhost` (AudioWorklet).
- C4 → C2: el banco gana `TextAligner` (letra tal cual y número de líneas libre), el conjunto
  `stress`, `import-srt` (referencias aproximadas y columna ≤ 0,5 s), `triangulate`,
  `package --align`, avisos sin referencia, alineador por idioma agrupado, y los informes de
  `private` van a `bench/data/results/`. Pantis y Clo Plas quedaron validadas solas
  (`decisiones/005`); Cibrán, Fanny + Alexander y Mortos en Vida, no.
- C4 → C3: `RoformerSeparator` decodifica con ffmpeg lo que no es WAV ni FLAC (fallaba con
  `.m4a`, el formato de YouTube).
- C4 → C5/C7: contrato **1.1.0** (`decisiones/006`): `Line.role` es `"lead"` o `"backing"`, y los
  coros pueden solaparse con la línea principal (un `role` ausente en paquetes 1.0.0 es `"lead"`).
  Las palabras de dos o más sílabas traen `parts` con tiempo real (gl, es, pt), y `confidence` por
  palabra sirve al editor. `karaoke make` ya hace paquetes de canciones reales para probar.
- C5 → C6: el MP4 quema el ASS de `build_ass(doc, theme, ancho, alto)` con
  `subtitles=letra.ass:fontsdir=<fonts_dir()>` (sin `fontsdir`, libass no encuentra las fuentes de los
  temas). Vale para 16:9 y 9:16; `karaoke preview` es un ejemplo mínimo con fondo liso.
- C5 → C7: `<Lyrics doc={normalizeDoc(doc)} theme={THEMES.clasico} clock={engine} />` de
  `#lib/lyrics`; ocupa su contenedor y se adapta a su tamaño. `/proba-letra` es de prueba. Las
  pruebas de navegador (`pnpm test:e2e`) usan el puerto 5181 y necesitan `libnss3`/`libnspr4`
  (`docs/subtitles.md`).
- C5 → C4: el barrido pinta los tiempos tal cual (sin retoques); lo que se vea adelantado o atrasado se
  arregla en el motor o en el editor. Una cuenta atrás a tempo necesitaría los pulsos en el documento.
- C6 → C7: el reproductor pone detrás de la letra el `<video muted playsinline>` del paquete
  (`video.background`) con `BackgroundSync` y, si no hay vídeo, la portada; `/proba-letra` lo enseña
  (portada desenfocada detrás, oscurecido y franja bajo la letra).
- C6 → C4: `make_package` guarda `background.mp4` y `cover.jpg` si la canción trae vídeo o carátula
  (unos 7 s más para 3 min de vídeo).
- C6 → C4: `make` en gallego junta ahora los pronombres enclíticos escritos aparte a su verbo
  (`dixo lle` → `díxolle`, `decisiones/009`), después de alinear; `karaoke join-clitics` arregla
  paquetes ya hechos. El banco no cambia (mide el alineador).
