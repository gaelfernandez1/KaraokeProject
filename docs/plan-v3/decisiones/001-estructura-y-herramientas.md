# 001 · Estructura del repo y herramientas

- **Fecha**: 28/10/2026
- **Estado**: aceptada (C1)
- **Afecta a**: todas las áreas

## Contexto

`00-vision.md` §5 propuso un monorepo con Python y TypeScript. C1 tenía que confirmarlo y fijar las
herramientas para que C2–C10 trabajen igual.

## Decisión

- **Monorepo con un workspace de uv** (`packages/*`) y una app web en `web/`. Cada paquete Python
  tiene su `pyproject.toml`; la raíz es virtual (`package = false`) y depende de todos.
- **Solo existen `contracts` y `engine`.** C2 crea `packages/bench` y C8 crea `packages/server`
  cuando los necesiten (sin paquetes vacíos por adelantado).
- **Una CLI por paquete**: `karaoke` (engine: `validate`, `demo`; luego `make` y `render`); el banco
  y el servidor tendrán la suya (p. ej. `karaoke-bench`, `karaoke-server`). Sustituye a la CLI
  orientativa de `00-vision.md` §6.5.
- **Python 3.12** (`>=3.12,<3.13`): lo más nuevo que aceptan todas las librerías candidatas
  (whisperx exige < 3.14 y pycotovia ≥ 3.11).
- **uv 0.13**, **ruff** (estricto en el código nuevo), **mypy** estricto con el plugin de pydantic
  (ty sigue en 0.0.x) y **pytest** con `--import-mode=importlib`.
- **pre-commit**: hooks locales que llaman a ruff vía `uv run`, para que la versión salga del lock.
- **make** como lanzador de tareas (ya instalado; nada que añadir).
- **torch** solo en el extra `ml`, desde el índice `pytorch-cu130` (torch 2.14.1+cu130 probado en
  la RTX 3050 bajo WSL). C3/C4 pueden cambiar versión o índice si una librería lo exige (p. ej.
  whisperx 3.8.6 fija torch 2.8).
- **Web**: SvelteKit 3, Svelte 5, TypeScript 6, Vite 8, Vitest 4, ESLint y Prettier, con
  `adapter-static` en modo SPA (`ssr = false`, `fallback: index.html`). pnpm 10.33.0, fijado en
  `packageManager`. C7 puede cambiar el modo de renderizado.
- **CI** en GitHub Actions: tres trabajos (Python, web, contratos sincronizados) sin GPU ni torch.
- **El sistema v2** queda en `legacy/` sin lint ni CI y etiquetado como `v2-final`. Las ramas viejas
  se archivaron como etiquetas `archive/*`.
- **Docs**: se versionan `docs/plan-v3/`, `docs/desarrollo.md` y `docs/tfg/`. Los planes viejos
  y las notas de trabajo personales viven solo en local.

## Consecuencias

- `uv sync` sin `--extra ml` desinstala torch: en el equipo con GPU se sincroniza con el extra.
- El corepack de Ubuntu 26.04 no instala pnpm ≥ 11; se revisará cuando haya uno nuevo.
- Playwright necesitará navegadores (y quizá librerías del sistema con sudo) cuando C5/C7 lo usen.
