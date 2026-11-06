#!/usr/bin/env bash
# Keeps the karaoke server running. Windows starts it hidden at logon (karaoke-server autostart):
# while it runs, WSL stays up. If the server stops with an error it starts again after 5 s.
set -u
cd "$(dirname "$0")/.." || exit 1
# Started from Windows there is no login shell: settings such as KARAOKE_BACKUP_DIR live here.
SETTINGS="${XDG_CONFIG_HOME:-$HOME/.config}/karaoke/server.env"
if [ -f "$SETTINGS" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$SETTINGS"
  set +a
fi
DATA="${KARAOKE_DATA:-${XDG_DATA_HOME:-$HOME/.local/share}/karaoke}"
LOG="$DATA/logs/forever.log"
mkdir -p "$DATA/logs"
export PATH="$HOME/.local/bin:$PATH"
while true; do
  # Small: the server keeps its own detailed log in server.log.
  if [ -f "$LOG" ] && [ "$(stat -c %s "$LOG")" -gt 5000000 ]; then mv "$LOG" "$LOG.1"; fi
  echo "$(date -Is) starting" >>"$LOG"
  # Not `uv run`: it would sync the environment and drop the GPU extras.
  .venv/bin/karaoke-server serve >>"$LOG" 2>&1
  code=$?
  echo "$(date -Is) stopped (exit $code)" >>"$LOG"
  # Stopped on purpose (Ctrl+C or SIGTERM): stay stopped.
  case "$code" in 0 | 130 | 143) exit 0 ;; esac
  sleep 5
done
