# CLAUDE.md — KaraokeProject (v3)

Generador de karaokes para cualquier canción, con el gallego como prioridad: letra bien transcrita,
subtítulos animados en sincronía con el canto y reproducción en el móvil, el portátil y la tele.
Proyecto personal y comunitario, sin monetización. El repo es público.

## Antes de empezar

1. Lee `docs/plan-v3/00-vision.md` (manda sobre todo lo demás), `docs/plan-v3/ESTADO.md` y
   `docs/plan-v3/decisiones/`.
2. Si te lanzaron como conversación CN, sigue `docs/plan-v3/01-conversaciones.md` («Bloque común»
   y «CN»).
3. Toca solo tu área (`00-vision.md` §8). Para cambiar un contrato o algo de otra área: decisión
   escrita en `decisiones/` y nota en `ESTADO.md`.

## Mapa del repo

| Ruta | Qué es |
|---|---|
| `packages/contracts/` | `karaoke_contracts`: modelos de `karaoke.json` y `theme.json`, validación, export de schemas |
| `packages/engine/` | `karaoke_engine`: interfaces de los pasos del motor y CLI `karaoke` |
| `web/` | App SvelteKit 3 + TypeScript (pnpm); tipos de los contratos en `src/lib/contracts/` |
| `schemas/` | JSON Schema generado desde los contratos (no se edita a mano) |
| `fixtures/` | Paquete de ejemplo sintético (`packages/demo-sintetico`) y tema básico |
| `scripts/` | Utilidades (`check_env.py`) |
| `docs/plan-v3/` | Visión, prompts, estado, decisiones y planes de cada conversación |
| `docs/desarrollo.md` | Instalación del entorno y comandos de cada día |
| `legacy/` | Sistema v2 congelado: no se toca, no pasa lint ni CI; lo borra C9 |

Llegarán `packages/bench` (C2) y `packages/server` (C8).

## Comandos

```bash
make setup                 # deps de Python (sin GPU), hooks de pre-commit y web
uv sync --extra ml         # además torch con CUDA, en el equipo con GPU
make ci                    # contratos + lint + tipos + tests de Python y web (como la CI)
make format                # ruff format + fix
make contracts             # regenera schemas/ y los tipos TS tras tocar un contrato
make check-env             # comprueba uv, node, pnpm, ffmpeg (libass, NVENC) y torch+CUDA
uv run karaoke validate <paquete|karaoke.json>
uv run karaoke demo fixtures/packages/demo-sintetico   # audio sintético que pita en cada sílaba
pnpm --dir web dev
```

## Reglas

- Código, comentarios, logs y commits en **inglés**. Docs del plan en español. Interfaz en
  gallego (por defecto), castellano e inglés. Con el usuario, en español claro.
- **Commits**: asunto imperativo de 50–72 caracteres y cuerpo de 1–3 párrafos con el porqué, tono
  humano, sin listas robóticas. Trailer `Co-Authored-By: Claude Opus 5.5
  <noreply@anthropic.com>`. Sin la línea «🤖 Generated with» en commits ni PRs.
- **Nunca commit ni push sin el OK explícito del usuario.** Nunca force-push a `main` ni
  `--no-verify`.
- **Usa siempre Opus**, también en subagentes. Si se acaba la cuota, espera.
- **Autenticaciones** (login, tokens, sudo): para y pídeselo al usuario; él lo hace a mano.
- **Secretos**: nunca en ficheros versionados ni en logs. `.env` no se versiona.
- **Canciones con copyright**: nunca en el repo; en local, en carpetas ignoradas (`bench/data/`,
  `input/`).
- **TDD**: primero un test que falle. Lo que afecte a la calidad o la velocidad del motor se mide
  con el banco (skill `probar-karaoke`, cuando exista).
- **Contratos**: tras tocarlos, `make contracts` y versiona los schemas y los tipos generados (la
  CI falla si no coinciden).

## Detalles que muerden

- Un `uv sync` a mano sin `--extra ml` desinstala torch (`make setup` no: usa `--inexact`).
- pnpm está fijado en 10.33.0: el corepack de Ubuntu 26.04 no sabe instalar pnpm 11 o superior.
- La GPU es una RTX 3050 de 4 GB: un modelo en la GPU a la vez, en int8/float16. WSL ve unos 7–8 GB
  de RAM.
- SvelteKit 3 ya no tiene `$lib`: se importa con `#lib/...` (y `#lib/contracts`).
- `docs/archivo/` (solo local) guarda los planes viejos: es historia, no fuente de verdad.
- Las cachés de root (`.mypy_cache/3.10`, `input/`, `output/`) son del Docker viejo; están
  ignoradas.
