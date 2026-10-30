"""ASS subtitles for the video export, drawn from the same layout as the web player.

Every row of the layout becomes one event at its place and time, with a `\\kf` wipe per syllable
(or `\\k` per word), so libass fills each syllable across its real width at its real time. The
countdown dots and the break bar are vector drawings. Times run `anticipation` seconds ahead of
the song, as on the web.

Render with ffmpeg's `subtitles` filter and `fontsdir=` set to `themes.fonts_dir()`.
"""

from itertools import pairwise

from karaoke_contracts import KaraokeDoc, Theme
from karaoke_engine.subtitles.layout import (
    BreakBar,
    Countdown,
    Group,
    Layout,
    Row,
    build_layout,
    scroll_focus,
    scroll_offset,
    scroll_opacity,
)
from karaoke_engine.subtitles.metrics import FontMetrics
from karaoke_engine.subtitles.themes import theme_metrics

# Bezier handle length for a quarter circle.
KAPPA = 0.5523
# Drawings use \p3: coordinates in quarters of a pixel, so they can be whole numbers.
DRAW_SCALE = 4
BAR_TRACK_OPACITY = 0.4
# Straight pieces that follow the eased scroll of the list (libass moves in straight lines).
SCROLL_PIECES = 4


def ass_color(color: str) -> tuple[str, str]:
    """`#RRGGBB[AA]` as an ASS colour (`&HBBGGRR&`) and alpha (`&HAA&`, 00 = opaque)."""
    red, green, blue = color[1:3], color[3:5], color[5:7]
    opacity = int(color[7:9], 16) if len(color) == 9 else 255
    return f"&H{blue}{green}{red}&".upper(), f"&H{255 - opacity:02X}&"


def _alpha(color: str, opacity: float) -> str:
    _, alpha = ass_color(color)
    visible = (255 - int(alpha[2:4], 16)) * opacity
    return f"&H{255 - round(visible):02X}&"


def _cs(seconds: float) -> int:
    return max(0, round(seconds * 100))


def _stamp(cs: int) -> str:
    hours, rest = divmod(cs, 360000)
    minutes, rest = divmod(rest, 6000)
    seconds, hundredths = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{hundredths:02d}"


def _one_line(text: str) -> str:
    """ASS is one record per line: a line break inside a field would start a new one."""
    return " ".join(text.splitlines())


def _escape(text: str) -> str:
    # Braces open override blocks and a backslash starts a tag: neither may reach libass raw.
    return _one_line(text).replace("{", "(").replace("}", ")").replace("\\", "/")


def _num(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _karaoke(row: Row, start_cs: int, theme: Theme) -> str:
    """Karaoke tags for a row whose event starts at `start_cs` (song time, already shifted)."""
    shift = theme.animation.anticipation
    word_mode = theme.animation.fill == "word"
    out: list[str] = []
    cursor = start_cs
    first = _cs(row.words[0].parts[0].start - shift)
    if first < start_cs:
        # The row was already being sung when this event starts (scroll mode cuts a row into
        # pieces): \kt sets the syllable clock back, so the wipe carries on instead of restarting.
        out.append(f"{{\\kt{first - start_cs}}}")
        cursor = first
    for i, word in enumerate(row.words):
        spans = (
            [(word.parts[0].start, word.parts[-1].end, "".join(p.text for p in word.parts))]
            if word_mode
            else [(p.start, p.end, p.text) for p in word.parts]
        )
        for j, (start, end, text) in enumerate(spans):
            begin, finish = _cs(start - shift), _cs(end - shift)
            gap = max(0, begin - cursor)
            if j == 0 and i > 0:
                out.append(f"{{\\k{gap}}} ")
            elif gap > 0:
                out.append(f"{{\\k{gap}}}")
            cursor = max(cursor, begin)
            tag = "k" if word_mode else "kf"
            out.append(f"{{\\{tag}{max(0, finish - cursor)}}}{_escape(text)}")
            cursor = max(cursor, finish)
    return "".join(out)


def _look(row: Row, row_px: float, theme: Theme, m: FontMetrics) -> str:
    """Size, sung colour, border and shadow of a row (its alphas go apart: they can change)."""
    colors = theme.colors
    sung, _ = ass_color(row.color)
    tags = f"\\fs{m.ass_font_size(row_px):.2f}\\1c{sung}"
    if colors.box is not None:
        return tags + f"\\bord{_num(0.18 * row_px)}\\shad0"
    if theme.layout.outline_width > 0:
        tags += f"\\bord{_num(theme.layout.outline_width * row_px)}"
        if colors.shadow is not None and theme.layout.shadow_offset > 0:
            return tags + f"\\shad{_num(theme.layout.shadow_offset * row_px)}"
        return tags + "\\shad0"
    if colors.shadow is not None and theme.layout.shadow_blur > 0:
        # A soft halo: a border in the shadow colour, blurred (the web uses a blurred text-shadow).
        blur = theme.layout.shadow_blur * row_px
        shadow, _ = ass_color(colors.shadow)
        return tags + f"\\bord{_num(blur)}\\3c{shadow}\\blur{_num(blur)}\\shad0"
    return tags + "\\bord0\\shad0"


def _alphas(row: Row, theme: Theme, opacity: float) -> str:
    """The four alphas of a row drawn at `opacity` (backing rows are fainter still)."""
    if row.role == "backing":
        opacity *= theme.backing.opacity
    colors = theme.colors
    if colors.box is not None:
        border = colors.box
    elif theme.layout.outline_width > 0:
        border = colors.outline
    else:
        border = colors.shadow or colors.outline
    shadow = colors.shadow or "#00000000"
    return (
        f"\\1a{_alpha(row.color, opacity)}\\2a{_alpha(colors.unsung, opacity)}"
        f"\\3a{_alpha(border, opacity)}\\4a{_alpha(shadow, opacity)}"
    )


def _dialogue(row: Row, start: int, end: int, tags: str, theme: Theme) -> str:
    style = "Backing" if row.role == "backing" else "Lead"
    text = "{" + tags + "}" + _karaoke(row, start, theme)
    return f"Dialogue: 0,{_stamp(start)},{_stamp(end)},{style},,0,0,0,,{text}"


def _page_event(
    row: Row, show: float, hide: float, font_px: float, theme: Theme, m: FontMetrics
) -> str:
    shift = theme.animation.anticipation
    start, end = _cs(show - shift), _cs(hide - shift)
    fade = min(round(theme.animation.transition * 1000), (end - start) * 5)
    row_px = font_px * row.scale
    y = row.y - m.ass_center_shift(row_px)
    tags = (
        f"\\an5\\pos({_num(row.x)},{_num(y)})\\fad({fade},{fade})"
        + _look(row, row_px, theme, m)
        + _alphas(row, theme, 1.0)
    )
    return _dialogue(row, start, end, tags, theme)


def _scroll_events(
    layout: Layout, group: Group, row: Row, theme: Theme, m: FontMetrics
) -> list[str]:
    """A row in scroll mode: still while the list rests, sliding (in short straight pieces that
    follow the ease) while it moves, and as faint as its distance from the line being sung."""
    plan = layout.scroll
    assert plan is not None
    shift = theme.animation.anticipation
    row_px = layout.font_px * row.scale
    y = row.y - m.ass_center_shift(row_px)
    look = _look(row, row_px, theme, m)
    cuts = {group.show, group.hide}
    for switch in plan.switches:
        for i in range(SCROLL_PIECES + 1):
            cut = switch + plan.transition * i / SCROLL_PIECES
            if group.show < cut < group.hide:
                cuts.add(cut)
    times = sorted(cuts)
    events = []
    for a, b in pairwise(times):
        start, end = _cs(a - shift), _cs(b - shift)
        if end <= start:
            continue
        first, last = scroll_offset(layout, a), scroll_offset(layout, b)
        middle = scroll_offset(layout, (a + b) / 2)
        before = scroll_opacity(group.index - scroll_focus(layout, a), plan.visible)
        after = scroll_opacity(group.index - scroll_focus(layout, b), plan.visible)
        if abs(first - last) < 0.01 and abs(middle - first) < 0.01:
            place = f"\\an5\\pos({_num(row.x)},{_num(y + first)})"
        else:
            place = f"\\an5\\move({_num(row.x)},{_num(y + first)},{_num(row.x)},{_num(y + last)})"
        tags = place + look + _alphas(row, theme, before)
        if abs(after - before) > 0.005:
            tags += f"\\t({_alphas(row, theme, after)})"
        events.append(_dialogue(row, start, end, tags, theme))
    return events


def _circle(r: float) -> str:
    """A circle of radius `r` with its top-left corner at the origin, in \\p3 units."""
    s = r * DRAW_SCALE
    k = s * KAPPA
    points: list[tuple[str, list[tuple[float, float]]]] = [
        ("m", [(s, 0)]),
        ("b", [(s + k, 0), (2 * s, s - k), (2 * s, s)]),
        ("b", [(2 * s, s + k), (s + k, 2 * s), (s, 2 * s)]),
        ("b", [(s - k, 2 * s), (0, s + k), (0, s)]),
        ("b", [(0, s - k), (s - k, 0), (s, 0)]),
    ]
    return " ".join(
        f"{cmd} " + " ".join(f"{round(x)} {round(y)}" for x, y in pts) for cmd, pts in points
    )


def _pill(width: float, height: float) -> str:
    """A rounded bar with its top-left corner at the origin, in \\p3 units."""
    w, h = width * DRAW_SCALE, height * DRAW_SCALE
    r = h / 2
    k = r * KAPPA
    path: list[tuple[str, list[tuple[float, float]]]] = [
        ("m", [(r, 0)]),
        ("l", [(w - r, 0)]),
        ("b", [(w - r + k, 0), (w, r - k), (w, r)]),
        ("b", [(w, r + k), (w - r + k, h), (w - r, h)]),
        ("l", [(r, h)]),
        ("b", [(r - k, h), (0, r + k), (0, r)]),
        ("b", [(0, r - k), (r - k, 0), (r, 0)]),
    ]
    return " ".join(
        f"{cmd} " + " ".join(f"{round(x)} {round(y)}" for x, y in pts) for cmd, pts in path
    )


def _dot_events(countdown: Countdown, font_px: float, theme: Theme) -> list[str]:
    shift = theme.animation.anticipation
    sung, sung_alpha = ass_color(theme.colors.sung)
    outline, outline_alpha = ass_color(theme.colors.outline)
    border = theme.layout.outline_width * font_px
    events = []
    for dot in countdown.dots:
        start, end = _cs(countdown.start - shift), _cs(dot.off - shift)
        if end <= start:
            continue
        tags = (
            f"\\an7\\pos({_num(dot.x - dot.r)},{_num(dot.y - dot.r)})\\p3"
            f"\\1c{sung}\\1a{sung_alpha}\\3c{outline}\\3a{outline_alpha}"
            f"\\bord{_num(border)}\\shad0"
        )
        events.append(
            f"Dialogue: 1,{_stamp(start)},{_stamp(end)},Dots,,0,0,0,,"
            f"{{{tags}}}{_circle(dot.r)}{{\\p0}}"
        )
    return events


def _bar_events(bar: BreakBar, theme: Theme) -> list[str]:
    shift = theme.animation.anticipation
    start, end = _cs(bar.start - shift), _cs(bar.end - shift)
    x0, y0 = bar.x - bar.width / 2, bar.y - bar.height / 2
    shape = _pill(bar.width, bar.height)
    track, _ = ass_color(theme.colors.unsung)
    sung, sung_alpha = ass_color(theme.colors.sung)
    place = f"\\an7\\pos({_num(x0)},{_num(y0)})\\p3\\bord0\\shad0"
    clip_from = f"\\clip({_num(x0)},{_num(y0)},{_num(x0)},{_num(y0 + bar.height)})"
    clip_to = f"\\clip({_num(x0)},{_num(y0)},{_num(x0 + bar.width)},{_num(y0 + bar.height)})"
    duration = (end - start) * 10
    return [
        f"Dialogue: 1,{_stamp(start)},{_stamp(end)},Dots,,0,0,0,,"
        f"{{{place}\\1c{track}\\1a{_alpha(theme.colors.unsung, BAR_TRACK_OPACITY)}}}"
        f"{shape}{{\\p0}}",
        f"Dialogue: 2,{_stamp(start)},{_stamp(end)},Dots,,0,0,0,,"
        f"{{{place}\\1c{sung}\\1a{sung_alpha}{clip_from}\\t(0,{duration},{clip_to})}}"
        f"{shape}{{\\p0}}",
    ]


def _style(name: str, theme: Theme, size: float) -> str:
    sung, sung_alpha = ass_color(theme.colors.sung)
    unsung, unsung_alpha = ass_color(theme.colors.unsung)
    outline, outline_alpha = ass_color(theme.colors.box or theme.colors.outline)
    shadow, shadow_alpha = ass_color(theme.colors.shadow or "#00000000")
    border_style = 3 if theme.colors.box is not None else 1

    def full(color: str, alpha: str) -> str:
        return f"&H{alpha[2:4]}{color[2:8]}"

    # Style fields are separated by commas, so the family name cannot carry one.
    family = _one_line(theme.font.family).replace(",", " ")
    return (
        f"Style: {name},{family},{size:.2f},{full(sung, sung_alpha)},"
        f"{full(unsung, unsung_alpha)},{full(outline, outline_alpha)},{full(shadow, shadow_alpha)},"
        f"0,0,0,0,100,100,0,0,{border_style},0,0,5,0,0,0,1"
    )


def layout_to_ass(layout: Layout, doc: KaraokeDoc, theme: Theme, metrics: FontMetrics) -> str:
    size = metrics.ass_font_size(layout.font_px)
    lines = [
        "[Script Info]",
        f"; {_one_line(doc.title)} — lyrics by karaoke-engine, theme {theme.id}",
        "ScriptType: v4.00+",
        f"PlayResX: {round(layout.width)}",
        f"PlayResY: {round(layout.height)}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        _style("Lead", theme, size),
        _style("Backing", theme, size * theme.backing.scale),
        _style("Dots", theme, size),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for group in layout.groups:
        for row in group.rows:
            if layout.scroll is None:
                lines.append(
                    _page_event(row, group.show, group.hide, layout.font_px, theme, metrics)
                )
            else:
                lines += _scroll_events(layout, group, row, theme, metrics)
    for countdown in layout.countdowns:
        lines += _dot_events(countdown, layout.font_px, theme)
    for bar in layout.bars:
        lines += _bar_events(bar, theme)
    return "\n".join(lines) + "\n"


def build_ass(doc: KaraokeDoc, theme: Theme, width: int, height: int) -> str:
    metrics = theme_metrics(theme)
    layout = build_layout(doc, theme, width, height, metrics)
    return layout_to_ass(layout, doc, theme, metrics)
