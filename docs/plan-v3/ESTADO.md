# Plan v3 · Estado

Tablero de las áreas de trabajo. Cada área actualiza **su fila** tras cada hito
(no solo al final) y añade lo que deja pendiente para otras. Orden: `00-vision.md` §9.

| Conv. | Área | Estado | Rama | Último hito | Interfaces que expone | Pendiente para otras |
|---|---|---|---|---|---|---|
| C1 | Arquitectura, repo y cimientos | hecho | `v3/c1-cimientos` (PR #1) | workspace uv, contratos v0, web SvelteKit, CI, entorno GPU comprobado | `karaoke_contracts` (`KaraokeDoc`, `Theme`, `validate_doc`, `validate_package`, `load_doc`, `dump_doc`); `schemas/*.schema.json`; `#lib/contracts` (tipos TS + `PlaybackClock`); `karaoke_engine.steps` (`Separator`, `Transcriber`, `Segmenter`, `Aligner`); CLI `karaoke validate|demo`; `fixtures/packages/demo-sintetico`; `fixtures/themes/basico.json`; `make ci|contracts|check-env` | C2: crear `packages/bench` y su comando; C5/C7: pueden empezar con el demo sintético |
| C2 | Banco de pruebas y métricas | en curso | `v3/c2-banco` | banco completo: JamendoLyrics (79 y rápido 20) y 5 gallegas con licencia libre, métricas, runner con caché, informes, comparación, línea base medida y metas fijadas (`decisiones/003`), página de revisión de oído y 3 paquetes reales; falta que el usuario valide de oído las 5 referencias gallegas | `karaoke-bench fetch\|run\|compare\|draft\|review\|realign\|package`; pipelines TOML en `bench/pipelines/` (cualquier clase que cumpla `karaoke_engine.steps`); `karaoke_bench.baseline` (Demucs, faster-whisper, alineador CTC); guía en `docs/banco.md` | ver notas C2 → C3, C4, C5/C7 |
| C3 | Audio: separación y sonido | sin empezar | — | — | — | — |
| C4 | Transcripción y sincronización | sin empezar | — | — | — | — |
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
- C2 → C3: la separación se mide con `karaoke-bench run --pipeline <nuevo>.toml --set quick --mode
  both` y `compare` contra `base-turbo` (Demucs htdemucs). El alineador provisional es
  `karaoke_bench.baseline.ctc:CtcAligner` (los modelos por defecto de WhisperX, sin WhisperX, que
  fija torch 2.8): C4 debe revalidar el separador elegido con su alineador. Demucs con la canción
  entera en la GPU llegó a ir 20 veces más lento en 4 GB: mezcla en RAM y trozos a la GPU.
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
