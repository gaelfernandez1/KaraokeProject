"""Advance widths of a theme's font, so the web and the video break lines in the same places."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FontMetrics:
    """What `scripts/build_fonts.py` writes next to each font (`*.metrics.json`)."""

    upem: int
    ascender: float
    descender: float
    win_ascent: float
    win_descent: float
    default_advance: float
    average_lowercase: float
    advances: dict[str, float]

    @classmethod
    def load(cls, path: Path) -> "FontMetrics":
        return cls(**json.loads(path.read_text(encoding="utf-8")))

    def width(self, text: str, px: float) -> float:
        """Width of `text` at `px` pixels per em, without kerning (a hair wider than drawn).

        The sum runs in text order and is scaled once at the end, exactly as the web does, so
        both get the same floating-point result.
        """
        total = 0.0
        for char in text:
            total += self.advances.get(char, self.default_advance)
        return total * px / self.upem

    def ass_font_size(self, px: float) -> float:
        """ASS font size whose em is `px` pixels: libass sizes fonts by winAscent + winDescent."""
        return px * (self.win_ascent + self.win_descent) / self.upem

    def ass_center_shift(self, px: float) -> float:
        """How far below the browser libass centres a line of `px` pixels per em.

        Browsers centre text in its line box on the hhea ascender and descender; libass centres
        `\\an5` text on winAscent and winDescent. Raising ASS rows by this much puts their text
        where the web draws it.
        """
        win_center = (self.win_ascent - self.win_descent) / 2
        css_center = (self.ascender + self.descender) / 2
        return (win_center - css_center) * px / self.upem
