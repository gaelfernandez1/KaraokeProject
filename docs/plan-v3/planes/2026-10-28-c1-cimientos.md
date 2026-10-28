# C1 · Cimientos — plan de implementación

> **Para agentes:** SUB-SKILL OBLIGATORIA: usa superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan tarea a tarea. Los pasos usan casillas (`- [ ]`).

**Objetivo:** dejar el repo listo para que C2–C10 trabajen sin pisarse. Incluye las ramas ordenadas,
el sistema viejo apartado, un workspace Python 3.12 con uv, los contratos v0 en código, una web
SvelteKit vacía, un entorno GPU comprobado, CI, comodidades de Claude Code y un CLAUDE.md nuevo.

**Arquitectura:** monorepo con un workspace uv (`packages/contracts`, `packages/engine`) y una app
SvelteKit en `web/`. Los contratos se escriben en pydantic. De ellos sale el JSON Schema
(`schemas/`) y, a partir de este, los tipos TS (`web/src/lib/contracts/generated/`). El sistema v2
queda congelado en `legacy/` (excluido de lint y CI) y etiquetado como `v2-final`.

**Tech stack:** uv, Python 3.12, pydantic 2, ruff, mypy, pytest, pre-commit, make; Node 22, pnpm,
SvelteKit 3 / Svelte 5, Vitest, ESLint y Prettier; json-schema-to-typescript; torch (índice CUDA
cu130) solo en el extra `ml`; ffmpeg de apt; GitHub Actions.

**Spec:** `docs/plan-v3/00-vision.md` (§5, §6, §10, §11, §13) y `docs/plan-v3/01-conversaciones.md`
(«Bloque común» y «C1»).

## Restricciones globales

- Python `>=3.12,<3.13` y `.python-version` = `3.12`.
- Código, comentarios y commits en inglés. Docs del plan y CLAUDE.md en español.
- Commits con tono humano, sin listas robóticas, y con el trailer `Co-Authored-By: Claude Opus 5.5
  <noreply@anthropic.com>`. Sin la línea «🤖 Generated with» (regla del usuario).
- Commits locales en `v3/c1-cimientos` solo con el OK del usuario. Push y PR, con otro OK aparte.
- Nada de secretos en ficheros versionados. `.env` sigue sin versionarse.
- Ruff y mypy no miran `legacy/` ni `web/`.
- Contratos: tiempos en segundos (float ≥ 0). `schema_version` con major 1. Se ignoran los campos
  desconocidos (las versiones menores nuevas se aceptan). Las rutas de medios son relativas al
  paquete.

## Foco de revisión

1. **Ruta de medio que se sale del paquete** (`../x.wav`, `/etc/x`) → `validate_package` la
   rechaza. Test en la tarea 4.
2. **Texto gallego con diacríticos y apóstrofos** (`ñ á ç ’ «»`) → sale idéntico al escribir y
   leer, sin escapes `\u`. Test en la tarea 4.
3. **Líneas solapadas** (dúo) → son válidas. Test en la tarea 4.
4. **Redondeo de tiempos**: una palabra que acaba 0,0005 s después que su línea → válida (tolerancia
   de 1 ms). Test en la tarea 4.
5. **Documento 1.3.0 con un campo nuevo** → se acepta; uno 2.0.0 → se rechaza. Test en la tarea 4.

---

### Task 1: ramas, etiquetas y rama de trabajo

**Ficheros:** ninguno (solo git).

- [ ] **Paso 1:** con el árbol limpio, `git checkout main && git merge --ff-only feature/f13-deploy`.
  Esperado: fast-forward de 5 commits.
- [ ] **Paso 2:** etiquetas anotadas:
  - `git tag -a v2-final -m "Last state of the v2 system before the v3 rebuild"`
  - `git tag -a archive/carrubranch carrubranch -m "Archived branch: API docs draft"`
  - `git tag -a archive/refactor-cambios refactor/cambios -m "Archived branch: env cleanup"`
- [ ] **Paso 3:** borrar las ramas locales `carrubranch`, `refactor/cambios`, `feature/f13-deploy` y
  `feature/f10-passwordless-auth`. Usa `git branch -d` y `-D` solo en las dos archivadas, que ya
  tienen etiqueta.
- [ ] **Paso 4:** `git checkout -b v3/c1-cimientos`.
- [ ] **Verificación:** `git branch` muestra solo `main` y `v3/c1-cimientos`; `git tag` muestra las
  cinco etiquetas. Lo remoto (push de main y etiquetas, borrado de `origin/carrubranch` y de
  `origin/feature/f10-passwordless-auth`) se hace en la tarea 12.

### Task 2: apartar el sistema viejo y versionar el plan

**Ficheros:**
- Mover con `git mv` a `legacy/`: `src/`, `templates/`, `static/`, `tests/`, `translations/`,
  `alembic/`, `alembic.ini`, `babel.cfg`, `Dockerfile.web`, `Dockerfile.whisperx`,
  `Dockerfile.worker`, `docker-compose.yml`, `.dockerignore`, `fly.toml`, `modal/`, `scripts/`,
  `fixtures/`, `fonts/`, `.env.example`, `pyproject.toml`, `.pre-commit-config.yaml`.
- Mover: `.github/workflows/{ci,deploy}.yml` → `legacy/.github/workflows/`;
  `docs/05-runbook.md` → `legacy/docs/05-runbook.md`; `Memoria/*.pdf` → `docs/tfg/memoria-tfg.pdf`.
- Crear: `legacy/README.md` (3–5 líneas: qué es, que está congelado, que lo borra C9, cómo
  arrancarlo con `v2-final`).
- Reescribir: `.gitignore`.
- Modificar: `README.md` (aviso al principio).
- Sin versionar: los `docs/0*.md` y `docs/planning/` restantes pasan a `docs/archivo/`, y el
  CLAUDE.md viejo a `docs/archivo/CLAUDE-v2.md`.

- [ ] **Paso 1:** hacer los movimientos.
- [ ] **Paso 2:** nuevo `.gitignore`.
  - Mantener: cachés de Python y herramientas, `.env*` salvo `.env.example`, `.venv/`, artefactos
    (`*.mp4`, `*.mp3`, `*.wav`, `*.m4a`, `*.srt`), `input/`, `output/`, `db/`, `*.db`, `*.log`,
    `node_modules/`, `web/.svelte-kit/`, `web/build/`, `.claude/settings.local.json`,
    `.claude/worktrees/`, `docs/archivo/`, `bench/data/`.
  - Dejar de ignorar: `docs/`, `CLAUDE.md` y `.python-version`.
- [ ] **Paso 3:** antes de versionar `docs/plan-v3/`, buscar secretos:
  `grep -rniE "(token|secret|password|api[_-]?key)\s*[:=]\s*\S{8,}" docs/plan-v3`.
  Esperado: nada.
- [ ] **Paso 4:** aviso al principio del README (en gallego, 2 líneas): proyecto en reconstrucción
  (plan v3); el sistema anterior está en `legacy/` y en la etiqueta `v2-final`.
- [ ] **Verificación:** `git status` muestra los renombrados como `R` (se conserva el historial) y
  `docs/plan-v3/*` como nuevos; `git check-ignore docs/archivo/x CLAUDE.md` solo lista
  `docs/archivo/x`.
- [ ] **Paso 5:** commit «Move the v2 system into legacy/ and start tracking the v3 plan» (con OK).

### Task 3: workspace Python con uv

**Ficheros:**
- Crear: `pyproject.toml` (raíz virtual), `.python-version`, `Makefile`, `.pre-commit-config.yaml`,
  `packages/contracts/pyproject.toml`, `packages/contracts/src/karaoke_contracts/__init__.py`,
  `packages/engine/pyproject.toml`, `packages/engine/src/karaoke_engine/__init__.py`.

**Interfaces:**
- Produce: distribuciones `karaoke-contracts` (import `karaoke_contracts`, depende de
  `pydantic>=2.12`) y `karaoke-engine` (import `karaoke_engine`, depende de `karaoke-contracts`;
  extra `ml` = `torch>=2.8` desde el índice `pytorch-cu130`, explícito). La raíz depende de las dos
  y define el extra `ml = ["karaoke-engine[ml]"]`.
- Comandos make: `setup`, `lint`, `format`, `typecheck`, `test`, `contracts`, `check-env`, `ci`
  (= lint + typecheck + test + contracts-check).

- [ ] **Paso 1:** instalar uv sin sudo (`curl -LsSf https://astral.sh/uv/install.sh | sh`, en
  `~/.local/bin`) y Python 3.12 gestionado (`uv python install 3.12`).
- [ ] **Paso 2:** escribir los pyproject.
  - Workspace: `members = ["packages/*"]`; raíz con `package = false`.
  - Grupo `dev`: pytest, ruff, mypy y pre-commit.
  - Ruff: py312, longitud de línea 100, reglas `E F W I B UP N SIM RUF PT`, excluye `legacy` y `web`.
  - mypy: estricto con el plugin `pydantic.mypy`, sobre `packages/*/src`.
  - pytest: `--import-mode=importlib`, testpaths `packages`.
- [ ] **Paso 3:** pre-commit con hooks `local` que ejecutan `uv run ruff format` y
  `uv run ruff check --fix` (las versiones salen de `uv.lock`), más `end-of-file-fixer` y
  `check-yaml`.
- [ ] **Verificación:** `uv sync` crea `uv.lock` y `.venv`; `make lint typecheck` en verde (sin
  código todavía); `uv run python -c "import karaoke_contracts, karaoke_engine"` sale con código 0.
- [ ] **Paso 4:** commit «Set up a uv workspace for the v3 Python packages» (con OK).

### Task 4: contrato `karaoke.json`

**Ficheros:**
- Crear: `packages/contracts/src/karaoke_contracts/doc.py`, `validate.py`.
- Test: `packages/contracts/tests/test_doc.py`, `test_validate.py`; fixture
  `fixtures/packages/demo-sintetico/karaoke.json`.

**Interfaces:**
- Produce (`karaoke_contracts`):
  - `SCHEMA_VERSION = "1.0.0"`.
  - Modelos pydantic `Part(text, start, end)` y
    `Word(text, start, end, confidence: float | None, parts: list[Part])`.
  - `Line(id, start, end, singer: str | None, words: list[Word] min 1)` y
    `Singer(id, name: str | None, color: str | None)` (color `#RRGGBB`).
  - `AudioRefs(instrumental: str, vocals: str | None, loudness_lufs: float | None)` y
    `VideoRefs(background: str | None)`.
  - `LanguageFallback(step, requested, used, reason)`.
  - `Provenance(lyrics_source: Literal["user","asr","lrclib"], separation_model, asr_model,
    align_model: str | None, engine_version: str, language_fallbacks: list[LanguageFallback])`.
  - `KaraokeDoc(schema_version, id, title, artist: str | None, language` (patrón `^[a-z]{2,3}$`)`,
    duration > 0, audio, video: VideoRefs | None, cover: str | None, singers, lines, provenance,
    edited: bool = False)`.
  - `Issue(path: str, message: str)` (dataclass congelada).
  - `validate_doc(doc: KaraokeDoc) -> list[Issue]`.
  - `load_doc(path: Path) -> KaraokeDoc`.
  - `dump_doc(doc: KaraokeDoc, path: Path) -> None` (UTF-8, `ensure_ascii` desactivado, sangría 2).
  - `validate_package(package_dir: Path) -> list[Issue]` (esquema + reglas + ficheros referenciados
    que existen y quedan dentro del paquete).
- Reglas de `validate_doc` (tolerancia `TIME_EPS = 0.001`):
  - En todo tramo, `end ≥ start`.
  - Las palabras quedan dentro de su línea y van en orden de `start` no decreciente.
  - Las partes quedan dentro de su palabra, en orden, y `"".join(p.text) == word.text` si hay
    partes.
  - Los `start` de las líneas no decrecen; se permite que dos líneas se solapen.
  - Todos los tiempos son ≤ `duration` + `TIME_EPS`.
  - Los `id` de líneas y de cantantes son únicos, y `line.singer` existe en `singers`.
  - El major de `schema_version` es 1 (un 2.x da error al cargar o validar).
- Fixture: canción sintética de unos 30 s, en gallego, con letra original (no de nadie). Lleva
  `parts` silábicas, un hueco instrumental de más de 5 s antes de la última línea (para probar la
  cuenta atrás), dos cantantes (`s1`, `s2`) y `instrumental.wav` / `vocals.wav` como medios.

- [ ] **Paso 1: tests (fallan).** En `test_doc.py` y `test_validate.py`:
  - `test_demo_fixture_is_valid`: `validate_package(demo_dir_with_generated_media)` y
    `validate_doc(load_doc(fixture)) == []`.
  - `test_dump_keeps_galician_text`: `"Ñ á ç ’ «»"` aparece literal en el fichero y no aparece `\u00`.
  - `test_word_outside_line_is_reported` y `test_rounding_within_1ms_is_accepted`
    (palabra.end = línea.end + 0,0005 → `[]`; + 0,01 → un `Issue`).
  - `test_overlapping_lines_are_allowed`.
  - `test_parts_must_spell_the_word` (`["O", "la"]` para `"Ola,"` → `Issue`).
  - `test_unknown_singer_and_duplicate_ids_are_reported`.
  - `test_newer_minor_with_extra_field_is_accepted` (1.3.0 + campo `foo`) y
    `test_major_2_is_rejected` (lanza `ValueError` o un `Issue`).
  - `test_media_path_outside_package_is_rejected` (con `../x.wav` y `/etc/x.wav`) y
    `test_missing_media_is_reported`.
- [ ] **Paso 2:** `uv run pytest packages/contracts -q` → falla al importar.
- [ ] **Paso 3:** implementar `doc.py` y `validate.py` con las firmas de arriba.
- [ ] **Paso 4:** `uv run pytest packages/contracts -q` y `make lint typecheck` → verde. (La prueba
  del fixture con medios generados se completa en la tarea 6; aquí se usa un `tmp_path` con WAV
  vacíos.)
- [ ] **Paso 5:** commit «Add the v0 karaoke document contract» (con OK).

### Task 5: contrato de tema y exportación de JSON Schema

**Ficheros:**
- Crear: `packages/contracts/src/karaoke_contracts/theme.py` y `schema_export.py`;
  `schemas/karaoke.schema.json` y `schemas/theme.schema.json` (generados y versionados);
  `fixtures/themes/basico.json`.
- Test: `packages/contracts/tests/test_theme.py` y `test_schemas.py`.

**Interfaces:**
- Produce:
  - Modelos `ThemeFont(family, weight=700` (100..900)`, file: str | None)`,
    `ThemeColors(sung, unsung, outline: Color, shadow: Color | None, box: Color | None)` (Color =
    `#RRGGBB` o `#RRGGBBAA`) y
    `ThemeLayout(visible_lines=2` (1..4)`, position: Literal["bottom","center","top"]="bottom",
    font_size=0.06` (0.02..0.2, fracción del alto)`, line_spacing=1.3)`.
  - `ThemeAnimation(fill: Literal["wipe","word"]="wipe", countdown_min_gap=5.0` (≥ 0; 0 lo
    desactiva)`)`.
  - `Theme(schema_version, id, name, font, colors, layout, animation)`.
  - `export_schemas(out_dir: Path) -> list[Path]` y `main()` (escribe en `schemas/`), invocado por
    `make contracts`.
- [ ] **Paso 1: tests.**
  - `test_basic_theme_fixture_is_valid`.
  - `test_invalid_color_is_rejected` (`"amarillo"`, `"#FFF"`).
  - `test_committed_schemas_are_up_to_date`: exportar a `tmp_path` y comparar byte a byte con
    `schemas/`.
- [ ] **Paso 2:** comprobar que fallan.
- [ ] **Paso 3:** implementar. Cada schema lleva `$id` (`https://github.com/gaelfernandez1/KaraokeProject/schemas/<nombre>.schema.json`)
  y `title`; JSON ordenado, sangría 2 y salto de línea final.
- [ ] **Paso 4:** `make contracts && uv run pytest packages/contracts -q` → verde.
- [ ] **Paso 5:** commit «Add the theme contract and export JSON Schemas» (con OK).

### Task 6: motor — interfaces de pasos, paquete de ejemplo y CLI

**Ficheros:**
- Crear: `packages/engine/src/karaoke_engine/steps.py`, `demo.py` y `cli.py`.
- Test: `packages/engine/tests/test_steps.py`, `test_demo.py` y `test_cli.py`.

**Interfaces:**
- Produce (`karaoke_engine.steps`):
  - Dataclasses congeladas `Stems(vocals: Path, instrumental: Path)`,
    `TranscriptSegment(start: float, end: float, text: str)` y
    `Transcript(language: str, segments: tuple[TranscriptSegment, ...])`.
  - Protocolos `@runtime_checkable`, cada uno con atributo `name: str`:
    - `Separator.separate(audio: Path, work_dir: Path) -> Stems`
    - `Transcriber.transcribe(vocals: Path, language: str) -> Transcript`
    - `Segmenter.segment(transcript: Transcript) -> list[str]`
    - `Aligner.align(vocals: Path, lyrics_lines: Sequence[str], language: str) -> list[Line]`
- Produce (`karaoke_engine.demo`): `build_demo_package(out_dir: Path) -> Path`. Copia el
  `karaoke.json` del fixture y sintetiza con la stdlib (`wave`, `math`; 22 050 Hz, mono, 16 bits)
  `instrumental.wav` (acorde suave continuo) y `vocals.wav` (un tono por cada `part`, con su inicio
  y su fin). Las dos pistas duran `duration`. Devuelve `out_dir`.
- Produce (CLI `karaoke`, entry point `karaoke_engine.cli:main`, con argparse):
  - `karaoke validate <ruta>`: carpeta o `karaoke.json`; imprime los `Issue`; exit 0/1.
  - `karaoke demo <out_dir>`.
- [ ] **Paso 1: tests.**
  - `test_fake_aligner_satisfies_protocol` (una clase con `name` y `align` cumple
    `isinstance(x, Aligner)`).
  - `test_demo_package_validates` (`validate_package(build_demo_package(tmp_path)) == []`).
  - `test_demo_audio_matches_duration` (la duración WAV queda a ±0,05 s de `doc.duration`).
  - `test_cli_validate_exit_codes` (0 con el demo; 1 con una palabra fuera de su línea).
- [ ] **Paso 2:** comprobar que fallan.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** `uv run pytest -q`, `uv run karaoke demo fixtures/packages/demo-sintetico` y
  `uv run karaoke validate fixtures/packages/demo-sintetico` → exit 0.
- [ ] **Paso 5:** commit «Add engine step interfaces and a synthetic demo package» (con OK).

### Task 7: web SvelteKit y tipos TS generados

**Ficheros:**
- Crear `web/` con `pnpm dlx sv@1.1.1 create` (plantilla mínima, TypeScript; añadir prettier,
  eslint y vitest; `adapter-static` con `fallback: "index.html"`).
- Crear `web/src/lib/contracts/clock.ts`, `web/src/lib/contracts/index.ts` y
  `web/src/lib/contracts/generated/{karaoke,theme}.ts` (generados).
- Script `gen:contracts` en `web/package.json` (json2ts desde `../schemas`).
- Página mínima `web/src/routes/+page.svelte` («Karaoke v3 — en construción»).
- Test: `web/src/lib/contracts/contracts.test.ts`.

**Interfaces:**
- Produce: `export interface PlaybackClock { now(): number }` (segundos de audio con la latencia ya
  compensada); tipos `KaraokeDoc` y `Theme` reexportados desde `$lib/contracts`.
- Consume: `schemas/*.schema.json` (Task 5).
- [ ] **Paso 1:** crear el proyecto (comprobar las flags con `pnpm dlx sv@1.1.1 create --help`).
- [ ] **Paso 2: test.** `contracts.test.ts` importa el fixture del demo, lo tipa como `KaraokeDoc`
  y comprueba que `doc.lines.length > 0` y que cada palabra con `parts` cumple
  `parts.map(p => p.text).join("") === word.text`.
- [ ] **Paso 3:** `pnpm gen:contracts` y reexportar.
- [ ] **Paso 4:** `pnpm install && pnpm lint && pnpm check && pnpm test --run && pnpm build` →
  verde; `make contracts` regenera sin diff.
- [ ] **Paso 5:** commit «Scaffold the SvelteKit web app with generated contract types» (con OK).

### Task 8: entorno GPU, ffmpeg y guía de desarrollo

**Ficheros:**
- Crear: `scripts/check_env.py` (stdlib) y `docs/desarrollo.md`.
- Modificar: `Makefile` (`check-env`).

**Interfaces:**
- Produce: `make check-env`. Comprueba y muestra en una tabla OK/FALTA:
  - `ffmpeg` con el encoder `h264_nvenc` y el filtro `ass`;
  - `uv`, `node` 22, `pnpm` y `nvidia-smi`;
  - y, si está el extra `ml`, torch con CUDA, el nombre de la GPU, la VRAM y una matmul en GPU.
  Exit 1 si falta algo obligatorio.
- [ ] **Paso 1:** pedir al usuario que ejecute `! sudo apt update && sudo apt install -y ffmpeg`.
- [ ] **Paso 2:** probar NVENC de verdad:
  `ffmpeg -f lavfi -i testsrc=d=2:s=1280x720 -c:v h264_nvenc -y /tmp/claude-1000/nvenc.mp4`.
  Esperado: fichero creado. Si NVENC no funciona en WSL, anotarlo para C6.
- [ ] **Paso 3:** `uv sync --extra ml` y `make check-env` → todo OK (torch 2.14.x+cu130, RTX 3050,
  unos 4 GB).
- [ ] **Paso 4:** `docs/desarrollo.md` (español): requisitos (Windows + WSL2 Ubuntu, driver
  NVIDIA), instalación paso a paso (apt ffmpeg, uv, pnpm, `make setup`, `make check-env`), comandos
  diarios, problemas conocidos (WSL ve unos 7–8 GB de RAM; 4 GB de VRAM: un modelo a la vez).
- [ ] **Paso 5:** commit «Add an environment check and a development guide» (con OK).

### Task 9: CI de GitHub Actions

**Ficheros:** crear `.github/workflows/ci.yml`.

- [ ] **Paso 1:** workflow `CI` (push a `main` y `v3/**`; PR a `main`):
  - **python** (ubuntu-latest): `astral-sh/setup-uv` con versión fijada, `uv sync --locked`, ruff
    format --check, ruff check, mypy y pytest.
  - **web**: `pnpm/action-setup`, `actions/setup-node` 22 con caché pnpm,
    `pnpm install --frozen-lockfile`, lint, check, test y build.
  - **contracts**: regenerar los schemas (uv) y los tipos (pnpm) y `git diff --exit-code schemas
    web/src/lib/contracts/generated`.
- [ ] **Verificación:** YAML válido (`uv run pre-commit run check-yaml --all-files`) y `make ci` en
  local en verde. La ejecución real en GitHub se comprueba en la tarea 12.
- [ ] **Paso 2:** commit «Add CI for the v3 workspace and web app» (con OK).

### Task 10: comodidades de Claude Code

**Ficheros:**
- Crear: `.claude/settings.json` (hook PostToolUse) y `.claude/hooks/format.sh`, siguiendo la skill
  `update-config`.
- Crear: `.mcp.json` (context7 HTTP `https://mcp.context7.com/mcp`; playwright stdio
  `npx @playwright/mcp@0.0.83`).

- [ ] **Paso 1:** hook en Edit|Write. `format.sh` lee el JSON de stdin, saca `tool_input.file_path`
  y actúa así:
  - `.py` fuera de `legacy/` → `uv run ruff format`;
  - dentro de `web/` (`.ts`, `.svelte`, `.js`, `.json`, `.css`) → `pnpm --dir web exec prettier --write`.
  Nunca falla la edición: siempre `exit 0`.
- [ ] **Paso 2:** probar el hook a mano:
  `echo '{"tool_input":{"file_path":"packages/engine/src/karaoke_engine/cli.py"}}' | .claude/hooks/format.sh`
  → exit 0, fichero formateado.
- [ ] **Paso 3:** `gh` sin sudo: descargar la última release de GitHub CLI para Linux amd64 a
  `~/.local/bin`. Pedir al usuario `! gh auth login`. Verificación: `gh auth status`.
- [ ] **Paso 4:** decir al usuario que, al abrir la próxima sesión, apruebe los MCP del proyecto
  (context7, playwright).
- [ ] **Paso 5:** commit «Add Claude Code formatting hook and project MCP servers» (con OK).

### Task 11: CLAUDE.md, decisiones, estado y memoria

**Ficheros:**
- Crear: `CLAUDE.md` (≤ 100 líneas, español, versionado),
  `docs/plan-v3/decisiones/001-estructura-y-herramientas.md` y `002-contratos-v0.md`.
- Modificar: `docs/plan-v3/ESTADO.md` y `docs/plan-v3/00-vision.md` (solo si una decisión cambia
  algo: p. ej. la CLI de §6.5).
- Memoria: borrar `project_test_environment.md` (describe el entorno Docker v2) y actualizar
  `MEMORY.md`.

- [ ] **Paso 1:** escribir CLAUDE.md:
  - qué es y punteros a `plan-v3`;
  - mapa del repo;
  - comandos (`make …`, `uv run karaoke …`, `pnpm …`);
  - reglas (idioma, commits, OK del usuario, Opus, autenticaciones, secretos, áreas por
    conversación);
  - qué es `legacy/`.
- [ ] **Paso 2:** escribir las decisiones.
  - **001**: workspace uv; solo `contracts` y `engine` creados (C2 crea `bench` y C8 crea `server`
    en `packages/`); una CLI por paquete; Python 3.12; mypy (ty sigue en 0.0.x); pre-commit; make;
    SvelteKit 3 + pnpm; torch cu130 solo en el extra `ml` (C3/C4 pueden cambiar versión e índice);
    `legacy/`; política de docs versionados.
  - **002**: dónde viven los contratos, cómo se generan y comprueban, reglas de versionado y
    validación.
- [ ] **Paso 3:** fila de C1 en ESTADO.md: hecho e interfaces expuestas (rutas exactas). Borrar la
  nota «no hay worktrees».
- [ ] **Verificación:** `wc -l CLAUDE.md` ≤ 100; `make ci` en verde.
- [ ] **Paso 4:** commit «Write the v3 CLAUDE.md and record the foundation decisions» (con OK).

### Task 12: revisión, push y PR

- [ ] **Paso 1:** `/code-review` sobre la rama y corregir lo que salga.
- [ ] **Paso 2:** `superpowers:verification-before-completion`: `make ci`, `make check-env` y
  `uv run karaoke validate fixtures/packages/demo-sintetico`.
- [ ] **Paso 3:** pedir el OK del usuario para lo remoto. Si lo da:
  - `git push origin main --follow-tags` (main con f13 y las etiquetas);
  - `git push origin --delete carrubranch feature/f10-passwordless-auth`;
  - `git push -u origin v3/c1-cimientos`.
- [ ] **Paso 4:** `gh pr create` hacia `main` (cuerpo en inglés, tono humano, sin la línea
  «🤖 Generated with»). Esperar al CI verde y hacer merge con el OK del usuario.
- [ ] **Paso 5:** dejar ESTADO.md con C1 «hecho» y C2 como siguiente.
