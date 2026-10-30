"""Visual theme tokens shared by the web lyrics renderer and the ASS video export."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from karaoke_contracts.doc import NonEmptyStr, _Model

THEME_SCHEMA_VERSION = "1.1.0"

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
    singers: list[Color] = Field(
        default_factory=list,
        description="Sung colour of each singer, in order, when a song has two or more.",
    )


class ThemeLayout(_Model):
    visible_lines: Annotated[int, Field(ge=1, le=4)] = 2
    position: Literal["bottom", "center", "top"] = "bottom"
    font_size: Annotated[
        float, Field(ge=0.02, le=0.2, description="Fraction of screen height.")
    ] = 0.06
    line_spacing: Annotated[float, Field(gt=0)] = 1.3
    mode: Literal["pages", "scroll"] = Field(
        default="pages",
        description="pages: fixed rows that take turns (classic); scroll: a list that moves up.",
    )
    margin: Annotated[
        float, Field(ge=0, le=0.2, description="Safe margin on each side, fraction of the screen.")
    ] = 0.05
    min_row_chars: Annotated[
        int, Field(ge=8, le=60, description="The font shrinks so a row fits this many letters.")
    ] = 22
    max_rows: Annotated[
        int, Field(ge=1, le=2, description="Rows a long line may wrap into before shrinking.")
    ] = 2
    outline_width: Annotated[float, Field(ge=0, description="Fraction of the font size.")] = 0.06
    shadow_offset: Annotated[float, Field(ge=0, description="Fraction of the font size.")] = 0.04
    shadow_blur: Annotated[float, Field(ge=0, description="Fraction of the font size.")] = 0.0


class ThemeBacking(_Model):
    """How backing vocals (lines with role "backing") look."""

    scale: Annotated[float, Field(ge=0.4, le=1)] = 0.72
    brackets: bool = True
    opacity: Annotated[float, Field(ge=0, le=1)] = 0.85


class ThemeAnimation(_Model):
    fill: Literal["wipe", "word"] = "wipe"
    countdown_min_gap: Annotated[
        float, Field(ge=0, description="Instrumental gap (s) that triggers a countdown; 0 = off.")
    ] = 5.0
    lead_in: Annotated[
        float, Field(ge=0, description="Seconds a block of lines shows before it is sung.")
    ] = 3.0
    hold: Annotated[
        float, Field(ge=0, description="Seconds a sung line stays before its slot is reused.")
    ] = 0.4
    transition: Annotated[
        float, Field(ge=0, le=2, description="Seconds of fades and scrolling.")
    ] = 0.25
    anticipation: Annotated[
        float,
        Field(ge=0, le=0.3, description="Seconds the highlight runs ahead of the sound."),
    ] = 0.05
    countdown_dots: Annotated[int, Field(ge=0, le=5)] = 3
    countdown_step: Annotated[float, Field(gt=0, le=2, description="Seconds per dot.")] = 1.0
    break_bar_min: Annotated[
        float, Field(ge=0, description="Gaps this long (s) show a progress bar; 0 = never.")
    ] = 8.0


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
    backing: ThemeBacking = Field(default_factory=ThemeBacking)
