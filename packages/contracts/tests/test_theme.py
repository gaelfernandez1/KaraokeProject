from pathlib import Path

import pytest
from pydantic import ValidationError

from karaoke_contracts import Theme

BASIC_THEME = Path(__file__).resolve().parents[3] / "fixtures" / "themes" / "basico.json"


def test_basic_theme_fixture_is_valid() -> None:
    theme = Theme.model_validate_json(BASIC_THEME.read_bytes())

    assert theme.animation.fill == "wipe"
    assert theme.colors.shadow == "#00000099"


@pytest.mark.parametrize("color", ["amarillo", "#FFF", "FFD400", "#FFD4001"])
def test_invalid_color_is_rejected(color: str) -> None:
    data = Theme.model_validate_json(BASIC_THEME.read_bytes()).model_dump()
    data["colors"]["sung"] = color

    with pytest.raises(ValidationError):
        Theme.model_validate(data)


@pytest.mark.parametrize(("field", "value"), [("visible_lines", 0), ("font_size", 0.5)])
def test_layout_out_of_range_is_rejected(field: str, value: float) -> None:
    data = Theme.model_validate_json(BASIC_THEME.read_bytes()).model_dump()
    data["layout"][field] = value

    with pytest.raises(ValidationError):
        Theme.model_validate(data)


def test_theme_1_0_loads_with_defaults() -> None:
    theme = Theme.model_validate_json(BASIC_THEME.read_bytes())

    assert theme.layout.mode == "pages"
    assert theme.layout.max_rows == 2
    assert theme.backing.scale == 0.72
    assert theme.backing.brackets is True
    assert theme.colors.singers == []
    assert theme.animation.lead_in == 3.0
    assert theme.animation.anticipation == 0.05


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("layout", "mode", "carousel"),
        ("layout", "max_rows", 3),
        ("layout", "margin", 0.3),
        ("backing", "scale", 1.5),
        ("animation", "anticipation", 0.5),
        ("animation", "countdown_dots", 9),
    ],
)
def test_new_fields_out_of_range_are_rejected(section: str, field: str, value: object) -> None:
    data = Theme.model_validate_json(BASIC_THEME.read_bytes()).model_dump()
    data[section][field] = value

    with pytest.raises(ValidationError):
        Theme.model_validate(data)
