# Plan v3 · Estado

Tablero de las áreas de trabajo. Cada área actualiza **su fila** tras cada hito
(no solo al final) y añade lo que deja pendiente para otras. Orden: `00-vision.md` §9.

| Conv. | Área | Estado | Rama | Último hito | Interfaces que expone | Pendiente para otras |
|---|---|---|---|---|---|---|
| C1 | Arquitectura, repo y cimientos | hecho | `v3/c1-cimientos` (PR #1) | workspace uv, contratos v0, web SvelteKit, CI, entorno GPU comprobado | `karaoke_contracts` (`KaraokeDoc`, `Theme`, `validate_doc`, `validate_package`, `load_doc`, `dump_doc`); `schemas/*.schema.json`; `#lib/contracts` (tipos TS + `PlaybackClock`); `karaoke_engine.steps` (`Separator`, `Transcriber`, `Segmenter`, `Aligner`); CLI `karaoke validate|demo`; `fixtures/packages/demo-sintetico`; `fixtures/themes/basico.json`; `make ci|contracts|check-env` | C2: crear `packages/bench` y su comando; C5/C7: pueden empezar con el demo sintético |
| C2 | Banco de pruebas y métricas | en curso | `v3/c2-banco` | banco completo: JamendoLyrics (79 y rápido 20) y 5 gallegas con licencia libre, métricas, runner con caché, informes, comparación, línea base medida y metas fijadas (`decisiones/003`), página de revisión de oído y 3 paquetes reales; falta que el usuario valide de oído las 5 referencias gallegas | `karaoke-bench fetch\|run\|compare\|draft\|review\|realign\|package`; pipelines TOML en `bench/pipelines/` (cualquier clase que cumpla `karaoke_engine.steps`); `karaoke_bench.baseline` (Demucs, faster-whisper, alineador CTC); guía en `docs/banco.md` | ver notas C2 → C3, C4, C5/C7 |
| C3 | Audio: separación y sonido | en curso | `v3/c3-audio` | separador elegido con el banco (Mel-Band RoFormer de Kim en trozos de 8 s, `decisiones/004`), audio del paquete a −14 LUFS en m4a, motor de audio web con voz guía, tono, reloj con latencia y calibración, y página `/proba-audio`; falta que el usuario lo pruebe en aparatos reales y escuche la separación | `karaoke_engine.separation.RoformerSeparator`; `karaoke_engine.audio` (`decode`, `measure`, `plan_gain`, `package_audio`, `convert_package`); CLI `karaoke audio`; `#lib/audio/engine.js` (`AudioEngine`, cumple `PlaybackClock`), `clock.js` (`SongClock`), `calibration.js`; guía en `docs/audio.md` | ver notas C3 → C4, C5/C7, C8 |
| C4 | Transcripción y sincronización | en curso (falta revisión final y PR) | `v3/c4-sincronia` | `karaoke make` de punta a punta (con letra, `--lrclib` o sin letra), alineador nuevo, sílabas, coros (contrato 1.1.0) y cantantes; con letra: jamendo 98,8 % a ≤ 0,3 s, media 0,093 s, inglés 97,6 %, gallego 98,6 %; sin letra: WER jamendo 23,2 %, gallego 26,5 % (meta 25 %); 0 cambios de idioma; `make` de 4 min: ~91 s con letra, 105–155 s sin letra (`decisiones/005` y `006`) | `karaoke make`; `karaoke_engine.make.make_package`; `karaoke_engine.align` (`LyricsAligner`, `parse_lyrics`, `syllables`…); `karaoke_engine.transcribe` (`WhisperTranscriber`, `LineSegmenter`); `karaoke_engine.lyrics_lookup`; `steps.TextAligner`; contrato 1.1.0 (`Line.role`); guía `docs/sincronia.md` | ver notas C4 → C2, C3, C5/C7, C8 |
| C5 | Subtítulos animados | sin empezar | — | — | — | — |
| C6 | Vídeo | sin empezar | — | — | — | — |
| C7 | Frontend | sin empezar | — | — | — | — |
| C8 | Backend, servidor y despliegue | sin empezar | — | — | — | — |
| C9 | Calidad de código | sin empezar | — | — | — | — |
| C10 | Proyecto profesional | sin empezar | — | — | — | — |

## Notas entre áreas

(Avisos que un área deja a otra: «C4 → C5: …». Borra los que ya estén atendidos.)

- C1 → todas: ya se puede trabajar en paralelo, como mucho dos áreas a la vez y cada una en su
  rama.
- C1 → C3/C4: torch está en el extra `ml` desde el índice cu130 (torch 2.14.1). whisperx 3.8.6
  exige torch 2.8; si lo usáis, cambiad versión e índice en una decisión.
- C1 → C5/C7: Playwright necesitará navegadores (`pnpm exec playwright install chromium`) y quizá
  librerías del sistema (con sudo).
- C1 → C7: `web/src/app.html` aún dice `lang="en"`; la interfaz va en gallego por defecto (y por
  idioma cuando haya i18n).
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
  Faltan en la interfaz los controles de voz guía, tono y calibración (`docs/audio.md`).
  `/proba-audio` y el middleware de `/paquetes/` en `web/vite.config.ts` son de prueba: C7 los
  sustituye o los borra. El cambio de tono necesita HTTPS o `localhost` (AudioWorklet).
- C3 → C8: separar una canción de 4 min cuesta unos 50 s en la RTX 3050 (Demucs, 14 s); el
  separador se descarga una vez a `~/.cache/karaoke/models/audio-separator` (0,9 GB).
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
- C4 → C8: `make_package(source, out_dir, language, lyrics | None, ...)` es lo que debe llamar el
  worker. Una canción de 4 min tarda 60–90 s con 3,8 GB de RAM de pico. Los modelos van a la caché
  de Hugging Face y a `~/.cache/karaoke/models/ct2`. El primer uso sin letra en gallego descarga y
  convierte HiTZ large-v3: unos 6 GB y un pico de 6,7 GB de RAM en un proceso aparte. Mejor hacerlo
  en la instalación, con `WhisperTranscriber().prepare_for("gl")`. `--lrclib` es la única llamada
  a la red.
