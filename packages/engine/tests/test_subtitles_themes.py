from pathlib import Path

import pytest

from karaoke_engine.subtitles.themes import (
    font_file,
    fonts_dir,
    load_theme,
    theme_metrics,
    theme_names,
)

BASIC_THEME = Path(__file__).resolve().parents[3] / "fixtures/themes/basico.json"


def test_theme_names() -> None:
    assert theme_names() == ["clasico", "contraste", "moderno"]


@pytest.mark.parametrize("name", ["clasico", "contraste", "moderno"])
def test_bundled_themes_are_valid(name: str) -> None:
    theme = load_theme(name)
    path = font_file(theme)

    assert theme.id == name
    assert theme.schema_version == "1.1.0"
    assert path is not None
    assert path.is_file()
    assert path.parent == fonts_dir()
    assert theme_metrics(theme).advances["ñ"] > 0


def test_load_theme_by_path() -> None:
    assert load_theme(BASIC_THEME).id == "basico"


def test_unknown_theme_lists_known() -> None:
    with pytest.raises(ValueError, match="clasico"):
        load_theme("disco")


def test_theme_without_bundled_font_uses_default_metrics() -> None:
    basic = load_theme(BASIC_THEME)

    assert font_file(basic) is None
    assert theme_metrics(basic) == theme_metrics(load_theme("clasico"))


def test_theme_naming_a_font_that_is_not_bundled_uses_default_metrics() -> None:
    clasico = load_theme("clasico")
    custom = clasico.model_copy(
        update={
            "font": clasico.font.model_copy(update={"family": "Mi Fonte", "file": "MiFonte.ttf"})
        }
    )

    assert font_file(custom) is None
    assert theme_metrics(custom) == theme_metrics(clasico)
