#!/usr/bin/env bash
# Starts the real karaoke server for the browser tests in e2e/server: the freshly built web app,
# the fake engine (no GPU) and a new library with the fixture packages, in a scratch folder on
# disk (/tmp is in RAM on the laptop). Usage: e2e/server/serve.sh [port]
set -euo pipefail
cd "$(dirname "$0")/../.."

port=${1:-8785}
data="${XDG_CACHE_HOME:-$HOME/.cache}/karaoke/e2e-server"
server=../.venv/bin/karaoke-server

rm -rf "$data"
pnpm build >/dev/null
# The fixtures' audio is not in git: the synthetic song's is made here; the real songs' comes from
# `uv run karaoke-bench package` (docs/benchmark.md, «Paquetes de ejemplo con canciones reales»).
demo=../fixtures/packages/demo-sintetico
[ -f "$demo/vocals.wav" ] || ../.venv/bin/karaoke demo "$demo" >/dev/null
if ! "$server" --data "$data" import ../fixtures/packages/* >/dev/null; then
  echo "e2e/server: a fixture package has no audio yet; make it with karaoke-bench package" >&2
  exit 1
fi
# Slow enough for the progress to show, quick enough for the tests.
export KARAOKE_FAKE_STAGE_SECONDS=0.3
exec "$server" --data "$data" serve --port "$port" --fake-engine
