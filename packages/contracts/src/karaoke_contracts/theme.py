"""Visual theme tokens shared by the web lyrics renderer and the ASS video export."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from karaoke_contracts.doc import NonEmptyStr, _Model

THEME_SCHEMA_VERSION = "1.0.0"

# #RRGGBB or #RRGGBBAA.
Color = Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")]


class ThemeFont(_Model):
    family: NonEmptyStr
    weight: Annotated[int, Field(ge=100, le=900)] = 700
    file: str | None = Field(default=None, description="Font file bundled with the theme, if any.")


class ThemeColors(_Model):
    sung: Color
    unsung: Color
    outline: Color
    shadow: Color | None = None
    box: Color | None = None


class ThemeLayout(_Model):
    visible_lines: Annotated[int, Field(ge=1, le=4)] = 2
    position: Literal["bottom", "center", "top"] = "bottom"
    font_size: Annotated[
        float, Field(ge=0.02, le=0.2, description="Fraction of screen height.")
    ] = 0.06
    line_spacing: Annotated[float, Field(gt=0)] = 1.3


class ThemeAnimation(_Model):
    fill: Literal["wipe", "word"] = "wipe"
    countdown_min_gap: Annotated[
        float, Field(ge=0, description="Instrumental gap (s) that triggers a countdown; 0 = off.")
    ] = 5.0


class Theme(_Model):
    schema_version: Annotated[str, StringConstraints(pattern=r"^1\.\d+\.\d+$")] = (
        THEME_SCHEMA_VERSION
    )
    id: NonEmptyStr
    name: NonEmptyStr
    font: ThemeFont
    colors: ThemeColors
    layout: ThemeLayout = Field(default_factory=ThemeLayout)
    animation: ThemeAnimation = Field(default_factory=ThemeAnimation)
