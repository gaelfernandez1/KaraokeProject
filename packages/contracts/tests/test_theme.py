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
