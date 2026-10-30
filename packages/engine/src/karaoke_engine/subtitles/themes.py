"""The bundled lyrics themes and their fonts (the web imports the same files)."""

from functools import cache
from pathlib import Path

from karaoke_contracts import Theme
from karaoke_engine.subtitles.metrics import FontMetrics

THEMES_DIR = Path(__file__).resolve().parent / "themes"
# Themes whose font is not bundled break lines with the default theme's metrics.
DEFAULT_THEME = "clasico"


def theme_names() -> list[str]:
    return sorted(path.stem for path in THEMES_DIR.glob("*.json"))


def load_theme(name_or_path: str | Path) -> Theme:
    """A bundled theme by id (`clasico`), or a theme.json anywhere by path."""
    path = Path(name_or_path)
    if not path.is_file():
        path = THEMES_DIR / f"{name_or_path}.json"
    if not path.is_file():
        raise ValueError(f"unknown theme {name_or_path!r}; known: {', '.join(theme_names())}")
    return Theme.model_validate_json(path.read_bytes())


def fonts_dir() -> Path:
    """What libass gets as `fontsdir`."""
    return THEMES_DIR / "fonts"


def font_file(theme: Theme) -> Path | None:
    """The bundled font file of a theme, or None if its font is not bundled here.

    A theme may name a font installed on the machine instead (libass then finds it through
    fontconfig, and the browser among the system fonts); it is measured with the default metrics,
    as the web does.
    """
    if theme.font.file is None:
        return None
    path = fonts_dir() / theme.font.file
    return path if path.is_file() else None


@cache
def _metrics(path: Path) -> FontMetrics:
    return FontMetrics.load(path)


def theme_metrics(theme: Theme) -> FontMetrics:
    path = font_file(theme) or font_file(load_theme(DEFAULT_THEME))
    assert path is not None
    return _metrics(path.with_suffix(".metrics.json"))
