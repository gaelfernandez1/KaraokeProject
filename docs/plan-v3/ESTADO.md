# Plan v3 · Estado

Tablero de las áreas de trabajo. Cada área actualiza **su fila** tras cada hito
(no solo al final) y añade lo que deja pendiente para otras. Orden: `00-vision.md` §9.

| Conv. | Área | Estado | Rama | Último hito | Interfaces que expone | Pendiente para otras |
|---|---|---|---|---|---|---|
| C1 | Arquitectura, repo y cimientos | hecho | `v3/c1-cimientos` (PR #1) | workspace uv, contratos v0, web SvelteKit, CI, entorno GPU comprobado | `karaoke_contracts` (`KaraokeDoc`, `Theme`, `validate_doc`, `validate_package`, `load_doc`, `dump_doc`); `schemas/*.schema.json`; `#lib/contracts` (tipos TS + `PlaybackClock`); `karaoke_engine.steps` (`Separator`, `Transcriber`, `Segmenter`, `Aligner`); CLI `karaoke validate|demo`; `fixtures/packages/demo-sintetico`; `fixtures/themes/basico.json`; `make ci|contracts|check-env` | C2: crear `packages/bench` y su comando; C5/C7: pueden empezar con el demo sintético |
| C2 | Banco de pruebas y métricas | sin empezar | — | — | — | — |
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
