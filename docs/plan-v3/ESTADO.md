# Plan v3 · Estado

Tablero de las áreas de trabajo. Cada área actualiza **su fila** tras cada hito
(no solo al final) y añade lo que deja pendiente para otras. Orden: `00-vision.md` §9.

| Conv. | Área | Estado | Rama | Último hito | Interfaces que expone | Pendiente para otras |
|---|---|---|---|---|---|---|
| C1 | Arquitectura, repo y cimientos | hecho | `v3/c1-cimientos` (PR #1) | workspace uv, contratos v0, web SvelteKit, CI, entorno GPU comprobado | `karaoke_contracts` (`KaraokeDoc`, `Theme`, `validate_doc`, `validate_package`, `load_doc`, `dump_doc`); `schemas/*.schema.json`; `#lib/contracts` (tipos TS + `PlaybackClock`); `karaoke_engine.steps` (`Separator`, `Transcriber`, `Segmenter`, `Aligner`); CLI `karaoke validate|demo`; `fixtures/packages/demo-sintetico`; `fixtures/themes/basico.json`; `make ci|contracts|check-env` | C2: crear `packages/bench` y su comando; C5/C7: pueden empezar con el demo sintético |
| C2 | Banco de pruebas y métricas | hecho (PR #2, en `main` el 29/10) | `v3/c2-banco` | banco completo: JamendoLyrics (79 y rápido 20) y 5 gallegas con licencia libre, métricas, runner con caché, informes, comparación, línea base medida y metas fijadas (`decisiones/003`), página de revisión de oído y 3 paquetes reales; falta que el usuario valide de oído las 5 referencias gallegas | `karaoke-bench fetch\|run\|compare\|draft\|review\|realign\|package`; pipelines TOML en `bench/pipelines/` (cualquier clase que cumpla `karaoke_engine.steps`); `karaoke_bench.baseline` (Demucs, faster-whisper, alineador CTC); guía en `docs/banco.md` | ver notas C2 → C3, C4, C5/C7 |
| C3 | Audio: separación y sonido | hecho (PR #3, en `main` el 30/10) | `v3/c3-audio` | separador elegido con el banco (Mel-Band RoFormer de Kim en trozos de 8 s, `decisiones/004`), audio del paquete a −14 LUFS en m4a, motor de audio web con voz guía, tono, reloj con latencia y calibración, y página `/proba-audio`; falta que el usuario lo pruebe en aparatos reales y escuche la separación | `karaoke_engine.separation.RoformerSeparator`; `karaoke_engine.audio` (`decode`, `measure`, `plan_gain`, `package_audio`, `convert_package`); CLI `karaoke audio`; `#lib/audio/engine.js` (`AudioEngine`, cumple `PlaybackClock`), `clock.js` (`SongClock`), `calibration.js`; guía en `docs/audio.md` | ver notas C3 → C4, C5/C7, C8 |
| C4 | Transcripción y sincronización | hecho (PR #4, en `main` el 30/10); el usuario escuchó dos canciones suyas y suenan bien | `v3/c4-sincronia` | `karaoke make` de punta a punta (con letra, `--lrclib` o sin letra), alineador nuevo, sílabas, coros (contrato 1.1.0) y cantantes; con letra: jamendo 98,8 % a ≤ 0,3 s, media 0,093 s, inglés 97,6 %, gallego 98,6 %; sin letra: WER jamendo 23,2 %, gallego 26,5 % (meta 25 %); 0 cambios de idioma; `make` de 4 min: ~91 s con letra, 105–155 s sin letra (`decisiones/005` y `006`) | `karaoke make`; `karaoke_engine.make.make_package`; `karaoke_engine.align` (`LyricsAligner`, `parse_lyrics`, `syllables`…); `karaoke_engine.transcribe` (`WhisperTranscriber`, `LineSegmenter`); `karaoke_engine.lyrics_lookup`; `steps.TextAligner`; contrato 1.1.0 (`Line.role`); guía `docs/sincronia.md` | ver notas C4 → C2, C3, C5/C7, C8 |
| C5 | Subtítulos animados | hecho (PR #5, en `main` el 30/10); el usuario se queda con `clasico` y `moderno` (`contraste`, como opción); falta probarlo en su tele | `v3/c5-subtitulos` | maquetación única en Python y TS con casos compartidos, modos páginas y desplazamiento, cuenta atrás, barra de pausa, coros y colores por cantante; componente web a 60 fps; generador ASS que coincide con la web a 1–3 px; 3 temas con fuentes OFL; tema 1.1.0 (`decisiones/007`) | `karaoke_engine.subtitles` (`build_layout`, `build_ass`, `load_theme`, `fonts_dir`, `render_preview`); CLI `karaoke subtitles\|preview`; `#lib/lyrics` (`Lyrics`, `THEMES`, `normalizeDoc`, `buildLayout`); página `/proba-letra`; guía `docs/subtitulos.md` | ver notas C5 → C6, C7, C4 |
| C6 | Vídeo | hecho (PR #6, en `main` el 30/10); falta que el usuario elija el fondo por defecto | `v3/c6-video` | `make` guarda vídeo y portada; `karaoke render` 16:9 y 9:16 con fondo de vídeo, portada o degradado, oscurecido según su brillo, franja bajo la letra, título, créditos y miniatura, en 27–45 s para 4 min con NVENC (`decisiones/008`); vídeo de fondo sincronizado en la web | `karaoke_engine.video` (`render`, `add_background`, `extract_background`, `extract_cover`, `choose_background`); CLI `karaoke render\|background`; `#lib/video/background.js` (`BackgroundSync`); guía `docs/video.md` | ver notas C6 → C7, C8, C4 |
| C7 | Frontend | hecho a falta del OK del usuario y de probarlo en su móvil, portátil y tele | `v3/c7-frontend` | app completa contra un servidor simulado: biblioteca de carteles, reproductor (voz guía, tono, retardo, descargas, vídeo), crear con progreso en vivo, fiesta con tele y móviles (turnos, mando, QR), editor de letra y tiempos, ajustes con calibración, PWA sin conexión, gl/es/en; revisada con capturas en cuatro rondas de un revisor independiente y una revisión de código (`decisiones/010`) | rutas `/`, `/crear`, `/cantar/<id>`, `/editar/<id>`, `/festa`, `/festa/<código>`, `/axustes`; `#lib/api` (cliente), `#lib/party` (turnos `upcoming`, conexión SSE), `#lib/player` (`PlayerSession`, `Stage`), `#lib/editor/ops`; servidor simulado `web/dev/mock/` (API esperada en `decisiones/010`); guía `docs/web.md` | ver notas C7 → C10, C3/C5/C6 |
| C8 | Backend, servidor y despliegue | hecho a falta del OK del usuario y de sus pasos en Windows (red `mirrored`, cortafuegos, Tailscale Serve, arranque) | `v3/c8-servidor` (encima de C7) | `karaoke-server`: FastAPI en un proceso con dos sockets (casa 8765, túneles 8766), zonas de red y aparatos vinculados, cola de un trabajo de GPU a la vez con un proceso hijo por trabajo en un *scope* de systemd, subidas en streaming, enlaces con yt-dlp al día, progreso y tiempo restante con SSE, cancelar y reintentar, fiesta persistente, `doctor`, copias, arranque con Windows; OpenAPI y tipos TS generados; probado de punta a punta en la RTX 3050: 4:47 con letra en 106 s, 5:13 por enlace sin letra en 166 s, MP4 en 30 s, cancelar libera la GPU en 0,3 s (`decisiones/011`) | `karaoke-server serve|pair|devices|import|backup|prepare|openapi|doctor|autostart`; `make serve`; API en `schemas/openapi.json` (tipos en `web/src/lib/api/generated/`); `#lib/devices` (`owner`, `DevicePanel`); ruta `/vincular`; `pnpm --dir web test:e2e:server`; guía `docs/servidor.md` | ver notas C8 → C7, C3, C9, C10 |
| C9 | Calidad de código | hecho, en su PR a `main` (06/11) | `v3/c9-calidad` | `legacy/` fuera; auditoría por siete revisiones independientes: 1 fallo de seguridad alto y unos 40 fallos confirmados arreglados con test (fiesta que saltaba canciones, letras largas cortadas, pronombres mal juntados, cola de la GPU que moría, banco que infravaloraba el gallego…); puertas nuevas (ruff ampliado, deptry, import-linter, eslint con tipos, knip, zizmor, política de saltos en la CI con ffmpeg); tests en paralelo (167 s → 60 s, 4,9 → 2,8 GB); `make` −19 % (`decisiones/012`, `docs/calidad.md`) | `make test-models`; `KARAOKE_STRICT_SKIPS`; fixture `ffmpeg` y marca `models` (`conftest.py`); `karaoke_engine.make.prepare_models`; `DELETE /api/parties/{code}` y evento SSE `ended`; `PartyConnection.ended`, `HostParty.end()`; `#lib/offline/fallback.js`; `pnpm perf:frames` | ver notas C9 → todas, C2, C3, C10 |
| C10 | Proyecto profesional | sin empezar | — | — | — | — |

## Notas entre áreas

(Avisos que un área deja a otra: «C4 → C5: …». Borra los que ya estén atendidos.)

- C1 → todas: ya se puede trabajar en paralelo, como mucho dos áreas a la vez y cada una en su
  rama. C1–C8 están en `main` (05/11); C9 (calidad) está en su PR; lo siguiente es C10
  (proyecto profesional).
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
  con `ASYNC/S/BLE/DTZ/…`, eslint con tipos en `web/src` y knip (`docs/calidad.md`). Un test que
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
- C9 → C10: `README.md` línea 1 ya no enlaza `legacy/`; `CITATION.cff`, `CONTRIBUTING.md` y
  `LICENSE` solo ganaron el salto de línea final.
- C8 → C10: el `README.md` sigue describiendo el sistema viejo (Docker, Celery); arrancar ahora es
  `make serve` y la guía para personas es `docs/servidor.md`.
- C7 → C10: nombre provisional «Foliada» (constante en `web/src/lib/ui/Wordmark.svelte`, el título
  de `app.html` y el manifiesto); icono: la «F» medio cantada (`web/static/icons/`).
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
  (`docs/subtitulos.md`).
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
