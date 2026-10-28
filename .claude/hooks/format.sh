#!/usr/bin/env bash
# PostToolUse hook: format the file Claude just edited (ruff for Python, prettier for the web).
# It never blocks or fails the edit: formatter output and errors are discarded.
set -u
root="$(cd "$(dirname "$0")/../.." && pwd)"
file="$(python3 -c 'import json, sys
d = json.load(sys.stdin)
print((d.get("tool_input") or {}).get("file_path") or (d.get("tool_response") or {}).get("filePath") or "")' 2>/dev/null)"
[ -n "$file" ] || exit 0
case "$file" in /*) ;; *) file="$root/$file" ;; esac
rel="${file#"$root"/}"
[ "$rel" != "$file" ] || exit 0  # outside this repo
cd "$root" || exit 0
case "$rel" in
  legacy/*) ;;
  *.py) uv run --quiet ruff format "$file" >/dev/null 2>&1 ;;
  web/*.ts | web/*.js | web/*.svelte | web/*.json | web/*.css | web/*.html)
    pnpm --dir web exec prettier --write --ignore-unknown "$file" >/dev/null 2>&1 ;;
esac
exit 0
