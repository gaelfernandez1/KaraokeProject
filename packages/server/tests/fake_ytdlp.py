"""Stands in for yt-dlp in tests: same options, a canned answer from FAKE_YTDLP (JSON)."""

import json
import os
import sys
import time
from pathlib import Path

args = sys.argv[1:]
config = json.loads(os.environ.get("FAKE_YTDLP", "{}"))
if config.get("fail"):
    print(f"ERROR: {config['fail']}", file=sys.stderr)
    sys.exit(1)
if "--dump-single-json" in args:
    info = {
        "title": "Pandeireta (Videoclip Oficial)",
        "uploader": "Banda - Topic",
        "artist": None,
        "track": None,
        "duration": 45.0,
        "is_live": False,
    }
    info.update(config.get("info", {}))
    print(json.dumps(info))
    sys.exit(0)
template = args[args.index("-o") + 1]
path = Path(template.replace("%(ext)s", "mkv"))
# As the real one: --print makes it quiet, so progress shows only with --progress, and a
# «download:» at the start of --progress-template names the kind of line, it is not printed.
progress = "%(progress._percent_str)s"
if "--progress-template" in args:
    progress = args[args.index("--progress-template") + 1].removeprefix("download:")
show = "--progress" in args or "--print" not in args
for percent in ("  0.0%", " 50.0%", "100.0%") * int(config.get("parts", 1)):
    if show:
        print(progress.replace("%(progress._percent_str)s", percent), flush=True)
    time.sleep(float(config.get("pause", 0)))
path.write_bytes(b"video")
print(str(path), flush=True)
