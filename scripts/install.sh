#!/usr/bin/env bash
# Installs Proxecto Karaoke en Galego on this machine, from the folder of the repository: `make install`.
#
#   scripts/install.sh [--no-models]
#
# Safe to run again (it only does what is missing) and it never uses sudo: what needs the system
# (ffmpeg, Node) is reported with the command to run, and the script stops. uv and pnpm are
# installed for the user if missing. With an NVIDIA GPU it installs the engine with CUDA and
# downloads the Galician models (several GB, once). Without one, the server and the web app run,
# but making karaokes needs an NVIDIA GPU (RTX 20 series or newer).
set -euo pipefail

UV_VERSION=0.13.6
# The oldest uv that reads this project's uv.lock the same way.
UV_MIN=0.13.0
NODE_MAJOR=22

models=1
for arg in "$@"; do
  case "$arg" in
    --no-models) models=0 ;;
    -h | --help)
      sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown option: $arg (try --help)" >&2
      exit 2
      ;;
  esac
done

cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

step() { printf '\n==> %s\n' "$*"; }
# True when version $1 is $2 or newer.
at_least() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -1)" = "$2" ]; }

step "Checking the system"
missing=()
if [ "$(uname -s)" != "Linux" ]; then
  missing+=("Linux (on Windows, inside WSL 2 with Ubuntu: wsl --install -d Ubuntu)")
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  missing+=("ffmpeg:   sudo apt update && sudo apt install -y ffmpeg")
# Read in full first: with pipefail, `grep -q` closing the pipe early would count as a failure.
elif ! grep -qw ass <<<"$(ffmpeg -hide_banner -filters 2>/dev/null || true)"; then
  missing+=("ffmpeg built with libass (subtitles):   sudo apt install -y ffmpeg")
fi
node_major=$(node --version 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/' || true)
if [ -z "$node_major" ] || [ "$node_major" -lt "$NODE_MAJOR" ]; then
  missing+=("Node $NODE_MAJOR or newer:   https://nodejs.org/en/download (the nvm option needs no sudo)")
fi
if ! command -v curl >/dev/null 2>&1 && ! command -v uv >/dev/null 2>&1; then
  missing+=("curl:   sudo apt install -y curl")
fi
if [ ${#missing[@]} -gt 0 ]; then
  echo "Install these first, then run this again:" >&2
  printf '  - %s\n' "${missing[@]}" >&2
  exit 1
fi
echo "ffmpeg and Node $node_major are ready."

if ! command -v uv >/dev/null 2>&1; then
  step "Installing uv $UV_VERSION (Python and its packages) in ~/.local/bin"
  curl -LsSf "https://astral.sh/uv/$UV_VERSION/install.sh" | sh
fi
uv_version=$(uv --version | awk '{print $2}')
if ! at_least "$uv_version" "$UV_MIN"; then
  echo "This uv is $uv_version and the project needs $UV_MIN or newer. Update it with:" >&2
  echo "  uv self update      (or with pip, pipx or brew, if it was installed that way)" >&2
  exit 1
fi

# The pnpm that web/package.json pins, made corepack's default so it is also the one used
# outside web/ (the corepack of Ubuntu cannot install the newest pnpm it would pick otherwise).
pnpm_version=$(sed -nE 's/.*"packageManager": "pnpm@([^"]+)".*/\1/p' web/package.json)
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0
if ! command -v pnpm >/dev/null 2>&1; then
  mkdir -p "$HOME/.local/bin"
  if command -v corepack >/dev/null 2>&1; then
    step "Enabling pnpm $pnpm_version (the web app's package manager) in ~/.local/bin"
    corepack enable --install-directory "$HOME/.local/bin" pnpm
  else
    # Node 25 and newer no longer bring corepack: npm installs pnpm for the user instead.
    step "Installing pnpm $pnpm_version (the web app's package manager) in ~/.local"
    npm install --global --prefix "$HOME/.local" "pnpm@$pnpm_version"
  fi
fi
if command -v corepack >/dev/null 2>&1; then
  corepack install -g "pnpm@$pnpm_version" >/dev/null
fi

gpu=0
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  gpu=1
fi

if [ "$gpu" = 1 ]; then
  step "Installing the engine with CUDA for $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"
  # --inexact keeps what is already installed (torch, or the tools of `make setup`); --no-dev
  # leaves the development tools out.
  uv sync --locked --inexact --no-dev --extra ml
else
  step "Installing the server and the web app (no NVIDIA GPU found: making karaokes needs one)"
  uv sync --locked --inexact --no-dev
fi

step "Building the web app"
pnpm --dir web install --frozen-lockfile
pnpm --dir web build

if [ "$gpu" = 1 ] && [ "$models" = 1 ]; then
  step "Downloading the models for Galician (several GB the first time)"
  # Not `uv run`: it would sync the environment again without the GPU extra.
  .venv/bin/karaoke-server prepare --lang gl
fi

step "What the server still needs"
.venv/bin/karaoke-server doctor || true

cat <<'EOF'

Proxecto Karaoke en Galego is installed. Start it with:

    make serve

and open http://localhost:8765 on this machine. The guide for phones, the TV and using it away
from home is docs/server.md.
EOF
