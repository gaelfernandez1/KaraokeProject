"""Puts the web lyrics and the video (libass) lyrics of the same moments one above the other.

    pnpm --dir web dev --port 5181 &          # the web player, once
    uv run python scripts/side_by_side.py fixtures/packages/demo-sintetico --times 4.5,13

For each time it writes `<out>/<package>-<theme>-<size>-<t>.png`: the browser on top, libass in
the middle and their difference below (black where they agree). Needs ffmpeg and the Playwright
Chromium (`pnpm --dir web exec playwright install chromium --only-shell`).
"""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

from karaoke_contracts import load_doc
from karaoke_engine.subtitles.ass import build_ass
from karaoke_engine.subtitles.themes import fonts_dir, load_theme

ROOT = Path(__file__).resolve().parents[1]
BACKGROUND = "0x141428"  # the plain background of /proba-letra?fondo=liso


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("package", type=Path)
    parser.add_argument("--theme", default="clasico")
    parser.add_argument("--size", default="1920x1080")
    parser.add_argument("--times", required=True, help="comma-separated seconds")
    parser.add_argument("--url", default="http://localhost:5181")
    parser.add_argument("--out", type=Path, default=ROOT / "bench/data/c5")
    args = parser.parse_args()

    width, height = (int(v) for v in args.size.split("x"))
    theme = load_theme(args.theme)
    doc = load_doc(args.package / "karaoke.json")
    times = [float(t) for t in args.times.split(",")]
    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"{args.package.name}-{theme.id}-{args.size}"

    with tempfile.TemporaryDirectory() as work:
        folder = Path(work)
        (folder / "lyrics.ass").write_text(build_ass(doc, theme, width, height), encoding="utf-8")
        (folder / "fonts").symlink_to(fonts_dir())
        page = f"{args.url}/proba-letra?paquete={args.package.name}&tema={theme.id}&fondo=liso"
        shots = [f"{t}={folder / f'web-{i}.png'}" for i, t in enumerate(times)]
        subprocess.run(
            ["node", "e2e/capture.mjs", page, str(width), str(height), theme.font.family, *shots],
            cwd=ROOT / "web",
            check=True,
            env=os.environ,
        )
        for i, t in enumerate(times):
            libass = folder / f"ass-{i}.png"
            subprocess.run(
                [
                    "ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                    "-i", f"color=c={BACKGROUND}:s={width}x{height}:r=100:d={t + 1:.2f}",
                    "-vf", "subtitles=lyrics.ass:fontsdir=fonts", "-ss", f"{t:.2f}",
                    "-frames:v", "1", str(libass),
                ],
                cwd=folder,
                check=True,
            )  # fmt: skip
            out = args.out / f"{stem}-{t:g}.png"
            subprocess.run(
                [
                    "ffmpeg", "-v", "error", "-y", "-i", str(folder / f"web-{i}.png"),
                    "-i", str(libass), "-filter_complex",
                    "[0:v]format=rgb24,split[w1][w2];[1:v]format=rgb24,split[a1][a2];"
                    "[w2][a2]blend=all_mode=difference[d];[w1][a1][d]vstack=inputs=3",
                    str(out),
                ],
                check=True,
            )  # fmt: skip
            print(out)


if __name__ == "__main__":
    main()
