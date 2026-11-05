"""Builds the fonts of the web app's interface, from Google Fonts sources pinned to one commit.

Run it only to add or change a font; the results are versioned:

    uv run --with fonttools --with brotli python scripts/build_web_fonts.py

Unlike the lyrics fonts (`build_fonts.py`), these stay variable: browsers handle variable fonts
well, and one file per family covers every weight the interface uses. Each one is limited to the
weights (and optical size) the interface needs and cut down to Latin, so the files stay small.
"""

import json
import shutil
import sys
import urllib.request
from io import BytesIO
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

COMMIT = "6157dfaa640ca5738b4d1a7070fe389c3036d7fc"
SOURCE = f"https://raw.githubusercontent.com/google/fonts/{COMMIT}"
OUT = Path(__file__).resolve().parents[1] / "web/src/lib/ui/fonts"
# Advance widths of the poster titles' face, so a title can be fitted before the font loads.
METRICS = Path(__file__).resolve().parents[1] / "web/src/lib/poster/display-metrics.json"
METRICS_WEIGHT = 900

# (output stem, google/fonts directory, variable file, axis limits)
FONTS = [
    # Condensed poster type for titles and big numbers, at its display optical size.
    (
        "BigShoulders",
        "ofl/bigshoulders",
        "BigShoulders[opsz,wght].ttf",
        {"opsz": 72, "wght": (600, 900)},
    ),
    # Interface text, built for legibility at a distance.
    (
        "AtkinsonHyperlegibleNext",
        "ofl/atkinsonhyperlegiblenext",
        "AtkinsonHyperlegibleNext[wght].ttf",
        {"wght": (400, 800)},
    ),
]

# Latin for Galician, Portuguese, Spanish and every other Latin-script language, combining marks,
# general punctuation, the euro, the trade mark sign and arrows for keyboard hints.
UNICODES = [
    *range(0x0020, 0x007F),
    *range(0x00A0, 0x0250),
    *range(0x0300, 0x0370),
    *range(0x1E00, 0x1F00),
    *range(0x2010, 0x2070),
    0x20AC,
    0x2122,
    *range(0x2190, 0x2194),
]


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        data: bytes = response.read()
        return data


def build(stem: str, directory: str, file: str, limits: dict[str, object]) -> None:
    font = TTFont(
        BytesIO(_download(f"{SOURCE}/{directory}/{file.replace('[', '%5B').replace(']', '%5D')}"))
    )
    font = instancer.instantiateVariableFont(font, limits)
    # A round trip through bytes loads every table eagerly: the subsetter needs it after instancing.
    buffer = BytesIO()
    font.save(buffer)
    buffer.seek(0)
    font = TTFont(buffer)
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.notdef_outline = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=UNICODES)
    subsetter.subset(font)
    out = OUT / f"{stem}.woff2"
    font.flavor = "woff2"
    font.save(out)
    licence = _download(f"{SOURCE}/{directory}/OFL.txt")
    (OUT / f"OFL-{stem}.txt").write_bytes(licence)
    print(f"{out.name}: {out.stat().st_size / 1024:.0f} kB", file=sys.stderr)


def write_metrics() -> None:
    """Advance width (in em) of every character of the poster titles at their weight."""
    url = f"{SOURCE}/ofl/bigshoulders/BigShoulders%5Bopsz,wght%5D.ttf"
    font = instancer.instantiateVariableFont(
        TTFont(BytesIO(_download(url))), {"opsz": 72, "wght": METRICS_WEIGHT}
    )
    units = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    advances = font["hmtx"].metrics
    widths = {
        chr(code): round(advances[cmap[code]][0] / units, 4)
        for code in [*range(0x20, 0x7F), *range(0xA0, 0x180), *range(0x2010, 0x2027)]
        if code in cmap
    }
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    METRICS.write_text(json.dumps({"weight": METRICS_WEIGHT, "widths": widths}, ensure_ascii=False))


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for stem, directory, file, limits in FONTS:
        build(stem, directory, file, limits)
    write_metrics()


if __name__ == "__main__":
    main()
