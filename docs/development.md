# Development guide

How to set up a machine to work on the project and which commands are used every day. Reference
machine: the project's laptop (Windows 11 + WSL 2 with Ubuntu 26.04, RTX 3050 Laptop with 4 GB).

## Requirements

- Windows with WSL 2 and an Ubuntu distribution. On native Linux, the same without the Windows part.
- To make karaokes, an NVIDIA GPU from the RTX 20 series on (PyTorch's CUDA 13 build needs compute
  capability 7.5), with its driver installed **on Windows** (not inside WSL). Inside WSL,
  `nvidia-smi` must show the GPU. The tests, the server and the web app run without one.
- Node 22 or newer.

## Installing with one command

From the repository's folder:

```bash
make install        # or scripts/install.sh --no-models to skip the models for now
make serve          # and open http://localhost:8765
```

`make install` (`scripts/install.sh`) is safe to run again: it only does what is missing. It never
uses sudo: if ffmpeg (with libass) or Node 22 is missing, it prints the exact command and stops. It
installs uv and pnpm for the user if they are not there; with an NVIDIA GPU it installs the engine
with CUDA and downloads the Galician models (a few GB, once); it builds the web app and ends with
`karaoke-server doctor`, which says what is still missing (for example, the WSL network for
phones). The CI runs it twice on a clean Ubuntu, with Node 22 (which brings corepack) and with
Node 26 (which no longer does: pnpm comes from npm there).

To develop, also run `make setup` (pre-commit hooks and the quality tools).

## Installing step by step

1. **ffmpeg** (with libass for the subtitles and NVENC to encode on the GPU):
   ```bash
   sudo apt update && sudo apt install -y ffmpeg
   ```
2. **uv** (the Python package manager; no sudo needed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. **pnpm** (the web app's package manager), through corepack, which comes with Node 22 and 24:
   ```bash
   corepack install -g pnpm@10.33.0
   ```
   Ubuntu's corepack (0.24) cannot install pnpm 11 or newer, so version 10 is pinned. With Node 26,
   which no longer ships corepack: `npm install --global --prefix ~/.local pnpm@10.33.0`.
4. **The project's dependencies**, from the repository's root:
   ```bash
   make setup                 # Python (without the GPU stack), pre-commit hooks and the web app
   uv sync --extra ml         # also torch with CUDA (a few GB), only on the GPU machine
   ```
   Beware: a manual `uv sync` without `--extra ml` uninstalls torch (`make setup` does not, because
   it uses `--inexact`). On the GPU machine, always sync by hand with `--extra ml`.
5. **Check that everything is in place:**
   ```bash
   make check-env
   ```
   Everything required must say `OK`. NVENC and torch show as `warning` if missing: the tests, the
   server and the web app work without a GPU, but making karaokes needs one.

## Everyday commands

| What | Command |
|---|---|
| Every CI check, locally | `make ci` |
| Format the Python code | `make format` |
| Python tests | `make test`: in parallel, about 60 s (or `uv run pytest packages/engine -q`) |
| The tests that load models (with the GPU free) | `make test-models` |
| The quality rules (format, lint, dependencies, boundaries, versions, licences) | `make lint` (guide: [`quality.md`](quality.md)) |
| The web app in development mode | `pnpm --dir web dev` |
| The server with the built web app (for phones and the TV) | `make serve` (guide: [`server.md`](server.md)) |
| What the server still needs (network, GPU, models…) | `uv run karaoke-server doctor` |
| A server without a GPU, with pretend karaokes | `uv run karaoke-server serve --fake-engine` |
| Regenerate the JSON Schema and TS types after changing a contract | `make contracts` |
| Validate a karaoke package | `uv run karaoke validate <folder>` |
| Synthetic audio for the example package | `uv run karaoke demo fixtures/packages/demo-sintetico` |
| Download the benchmark's songs (once) | `uv run karaoke-bench fetch --set all` |
| Measure a change to the engine (quick check) | `uv run karaoke-bench run --pipeline bench/pipelines/<x>.toml --set quick` |
| Compare two measurements | `uv run karaoke-bench compare bench/results/<a> bench/results/<b>` |
| Check a Galician reference by ear | `uv run karaoke-bench review gl/<id> --pipeline bench/pipelines/draft-gl.toml` |
| Bump the version | `uv run python scripts/release.py set X.Y.Z` (guide: [`releasing.md`](releasing.md)) |

The benchmark has its own guide: [`benchmark.md`](benchmark.md).

## Known issues

- **WSL sees less RAM than Windows** (about 7–8 GB of 16). Large models are loaded one at a time.
- **4 GB of VRAM**: one model on the GPU at a time, in int8 or float16, freed before the next one.
- **Root-owned caches** (`.mypy_cache/3.10`, `input/`, `output/`) left by the previous version's
  Docker setup: git ignores them; if they get in the way, `sudo rm -rf` them.
- **Do not run the test suite while a karaoke is being made**: the GPU job already uses 4–5 GB of
  RAM.
