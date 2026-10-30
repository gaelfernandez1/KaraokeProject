from pathlib import Path

import pytest

from karaoke_engine.subtitles.metrics import FontMetrics

FONTS = Path(__file__).resolve().parents[1] / "src/karaoke_engine/subtitles/themes/fonts"


def _table(**advances: float) -> FontMetrics:
    return FontMetrics(
        upem=1000,
        ascender=900,
        descender=-300,
        win_ascent=1000,
        win_descent=250,
        default_advance=1000,
        average_lowercase=500,
        advances=advances,
    )


def test_width_sums_advances() -> None:
    assert _table(a=500, b=600).width("ab", 10) == pytest.approx(11.0)


def test_missing_char_uses_default_advance() -> None:
    assert _table(a=500).width("a字", 10) == pytest.approx(15.0)


@pytest.mark.parametrize("path", sorted(FONTS.glob("*.metrics.json")), ids=lambda p: p.stem)
def test_bundled_metrics_cover_galician(path: Path) -> None:
    metrics = FontMetrics.load(path)

    assert all(char in metrics.advances for char in "ñçãõáéíóúüÑÇÁÉÍÓÚ¡¿«»·’…")


def test_ass_font_size_uses_win_metrics() -> None:
    # libass sizes a font by its winAscent + winDescent, not by its em.
    assert _table().ass_font_size(80) == pytest.approx(100.0)


def test_ass_center_shift_matches_css_centering() -> None:
    # Browsers centre a line on the hhea ascender and descender, libass on the win ones:
    # here (1000 - 250)/2 - (900 - 300)/2 = 75 units of 1000, so 7.5 px at 100 px.
    assert _table().ass_center_shift(100) == pytest.approx(7.5)
