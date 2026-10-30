"""Builds the fonts the lyrics themes use, from Google Fonts sources pinned to one commit.

Run it only to add or change a font; the results are versioned:

    uv run --with fonttools --with brotli python scripts/build_fonts.py

Each variable font is downloaded, fixed at the weight its theme uses (libass does not pick
instances of variable fonts reliably), renamed to a family of its own (so the web and libass ask
for the same name and nothing synthesises bold), cut down to the scripts lyrics need, and saved as
TTF (for libass) and WOFF2 (for browsers). A metrics file with every character's advance width
lets the web and the video export break lines in exactly the same places.
"""

import json
import sys
import urllib.request
from io import BytesIO
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

COMMIT = "6157dfaa640ca5738b4d1a7070fe389c3036d7fc"
SOURCE = f"https://raw.githubusercontent.com/google/fonts/{COMMIT}"
OUT = (
    Path(__file__).resolve().parents[1]
    / "packages/engine/src/karaoke_engine/subtitles/themes/fonts"
)

# (file stem, family name, google/fonts directory, variable file, axis values)
FONTS = [
    ("Nunito-Black", "Nunito Black", "ofl/nunito", "Nunito[wght].ttf", {"wght": 900}),
    (
        "Inter-ExtraBold",
        "Inter ExtraBold",
        "ofl/inter",
        "Inter[opsz,wght].ttf",
        {"wght": 800, "opsz": 32},
    ),
    (
        "AtkinsonHyperlegibleNext-ExtraBold",
        "Atkinson Hyperlegible Next ExtraBold",
        "ofl/atkinsonhyperlegiblenext",
        "AtkinsonHyperlegibleNext[wght].ttf",
        {"wght": 800},
    ),
]

# Latin (with Galician, Portuguese and every other Latin-script language), Greek, Cyrillic,
# combining marks and the punctuation lyrics use.
UNICODES = [
    *range(0x0020, 0x007F),
    *range(0x00A0, 0x0250),
    *range(0x0300, 0x0370),
    *range(0x0370, 0x0400),
    *range(0x0400, 0x0500),
    *range(0x1E00, 0x1F00),
    *range(0x2010, 0x2070),
    0x20AC,
]


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        data: bytes = response.read()
        return data


def _rename(font: TTFont, family: str) -> None:
    """A single-face family: family `family`, style Regular, no typographic family names."""
    name = font["name"]
    postscript = family.replace(" ", "")
    for record in list(name.names):
        if record.nameID in (16, 17, 21, 22, 25):
            name.removeNames(nameID=record.nameID)
    for name_id, value in ((1, family), (2, "Regular"), (4, family), (6, postscript)):
        name.setName(value, name_id, 3, 1, 0x409)
        name.setName(value, name_id, 1, 0, 0)
    font["OS/2"].usWeightClass = 400
    font["OS/2"].fsSelection = (font["OS/2"].fsSelection & ~0b1100001) | 0b1000000
    font["head"].macStyle = 0


def _metrics(font: TTFont) -> dict[str, object]:
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    advances = {chr(cp): hmtx[glyph][0] for cp, glyph in sorted(cmap.items())}
    lowercase = [advances[c] for c in "abcdefghijklmnopqrstuvwxyz"]
    upem = font["head"].unitsPerEm
    return {
        "upem": upem,
        "ascender": font["hhea"].ascent,
        "descender": font["hhea"].descent,
        "win_ascent": font["OS/2"].usWinAscent,
        "win_descent": font["OS/2"].usWinDescent,
        # Characters the font lacks are drawn by a fallback font of unknown width; one em keeps
        # them from overflowing (CJK is about that wide).
        "default_advance": upem,
        "average_lowercase": sum(lowercase) / len(lowercase),
        "advances": advances,
    }


def build(stem: str, family: str, directory: str, filename: str, axes: dict[str, float]) -> None:
    variable = TTFont(BytesIO(_download(f"{SOURCE}/{directory}/{filename}")))
    font = instancer.instantiateVariableFont(variable, axes)
    _rename(font, family)
    options = subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.hinting = False
    options.notdef_outline = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=UNICODES)
    subsetter.subset(font)
    font.flavor = None
    font.save(OUT / f"{stem}.ttf")
    font.flavor = "woff2"
    font.save(OUT / f"{stem}.woff2")
    font.flavor = None
    metrics = _metrics(TTFont(OUT / f"{stem}.ttf"))
    text = json.dumps(metrics, ensure_ascii=False, separators=(",", ":"))
    (OUT / f"{stem}.metrics.json").write_text(text + "\n", encoding="utf-8")
    licence = _download(f"{SOURCE}/{directory}/OFL.txt")
    (OUT / f"OFL-{stem.split('-')[0]}.txt").write_bytes(licence)
    print(f"{stem}: {(OUT / f'{stem}.woff2').stat().st_size // 1024} KB woff2", file=sys.stderr)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for font in FONTS:
        build(*font)


if __name__ == "__main__":
    main()
