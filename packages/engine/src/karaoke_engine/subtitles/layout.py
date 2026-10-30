"""Where and when every lyrics row shows, for any screen size.

This is the reference version of an algorithm the web player runs too
(`web/src/lib/lyrics/layout.ts`): the shared cases in `fixtures/lyrics-layout/` keep both
identical, so a song breaks its lines and takes turns on screen exactly the same in the browser
and in the video. Any change here goes there as well, in the same order of operations (the
floating-point results must match).

Pages mode: `visible_lines` fixed slots take turns. A block of lines (between instrumental breaks)
appears `lead_in` seconds before it is sung, with a countdown; each line gives its slot to the one
`visible_lines` places later once it has been sung. Text never moves while it is being read.
"""

from bisect import bisect_right
from typing import Literal

from pydantic import BaseModel, ConfigDict

from karaoke_contracts import KaraokeDoc, Line, Theme
from karaoke_engine.subtitles.metrics import FontMetrics

# A break that ends one of these characters is a better place to wrap a line.
BREAK_AFTER = ",.;:!?…»)"
# Wrapping prefers a break after punctuation unless it makes the longest row 10 % wider.
PUNCTUATION_BONUS = 0.9
MIN_SCALE = 0.6
# A backing line that overlaps no lead line joins the previous one if it starts this soon after.
BACKING_ATTACH = 1.5
# A line appears at least this long before it is sung, even if the line before in its slot is
# still being held.
MIN_LEAD = 0.5
# Scroll mode: space between groups (fraction of the font size), where the line being sung sits
# (fraction of the height), and how long before a line is sung the list has stopped moving.
SCROLL_GAP = 0.35
SCROLL_ANCHOR = {"top": 0.30, "center": 0.42, "bottom": 0.62}
SCROLL_SETTLE = 0.25


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class PartSpan(_Frozen):
    text: str
    start: float
    end: float


class RowWord(_Frozen):
    """A word as displayed: its syllables, or one part for the whole word."""

    parts: list[PartSpan]


class Row(_Frozen):
    line_id: str
    role: Literal["lead", "backing"]
    singer: str | None
    color: str
    words: list[RowWord]
    text: str
    scale: float
    x: float
    y: float
    width: float
    height: float


class Group(_Frozen):
    """A lead line with the backing lines sung over or right after it, shown together."""

    index: int
    block: int
    slot: int
    start: float
    end: float
    show: float
    hide: float
    rows: list[Row]


class Dot(_Frozen):
    x: float
    y: float
    r: float
    off: float


class Countdown(_Frozen):
    block: int
    start: float
    end: float
    dots: list[Dot]


class BreakBar(_Frozen):
    """Progress through an instrumental break, from the last line shown to the next one."""

    start: float
    end: float
    x: float
    y: float
    width: float
    height: float


class ScrollPlan(_Frozen):
    """Scroll mode: rows are placed in one long list that moves up as the song goes on.

    `offsets[k]` moves the list so that group k sits on the anchor; the list starts moving to
    group k at `switches[k - 1]` and takes `transition` seconds (ease-out).
    """

    offsets: list[float]
    switches: list[float]
    transition: float
    visible: int


class Layout(_Frozen):
    width: float
    height: float
    font_px: float
    mode: Literal["pages", "scroll"]
    groups: list[Group]
    countdowns: list[Countdown]
    bars: list[BreakBar]
    scroll: ScrollPlan | None = None


def wrap(
    words: list[str], px: float, max_width: float, max_rows: int, metrics: FontMetrics
) -> tuple[list[list[int]], float]:
    """Rows (word indices) for a line, and how much to shrink it so the widest row fits."""
    full = metrics.width(" ".join(words), px)
    if full <= max_width:
        return [list(range(len(words)))], 1.0
    if max_rows < 2 or len(words) < 2:
        return [list(range(len(words)))], max(MIN_SCALE, max_width / full)
    best = 1
    best_cost = 0.0
    best_widest = 0.0
    for i in range(1, len(words)):
        widest = max(metrics.width(" ".join(words[:i]), px), metrics.width(" ".join(words[i:]), px))
        cost = widest * PUNCTUATION_BONUS if words[i - 1][-1] in BREAK_AFTER else widest
        if i == 1 or cost < best_cost:
            best, best_cost, best_widest = i, cost, widest
    rows = [list(range(best)), list(range(best, len(words)))]
    if best_widest <= max_width:
        return rows, 1.0
    return rows, max(MIN_SCALE, max_width / best_widest)


def _display_words(line: Line, brackets: bool) -> list[RowWord]:
    words = [
        RowWord(
            parts=[PartSpan(text=p.text, start=p.start, end=p.end) for p in word.parts]
            or [PartSpan(text=word.text, start=word.start, end=word.end)]
        )
        for word in line.words
    ]
    if brackets:
        first = words[0].parts[0]
        words[0].parts[0] = first.model_copy(update={"text": "[" + first.text})
        last = words[-1].parts[-1]
        words[-1].parts[-1] = last.model_copy(update={"text": last.text + "]"})
    return words


def _groups(doc: KaraokeDoc) -> list[list[Line]]:
    """Lead lines with their backing lines attached; lone backing lines are groups of their own."""
    leads = sorted((line for line in doc.lines if line.role == "lead"), key=lambda li: li.start)
    attached: list[list[Line]] = [[] for _ in leads]
    alone: list[Line] = []
    for line in doc.lines:
        if line.role != "backing":
            continue
        target = -1
        best = 0.0
        for i, lead in enumerate(leads):
            overlap = min(line.end, lead.end) - max(line.start, lead.start)
            if overlap > best:
                target, best = i, overlap
        if target < 0:
            previous = -1
            for i, lead in enumerate(leads):
                if lead.end <= line.start and (previous < 0 or lead.end >= leads[previous].end):
                    previous = i
            if previous >= 0 and line.start - leads[previous].end < BACKING_ATTACH:
                target = previous
        if target >= 0:
            attached[target].append(line)
        else:
            alone.append(line)
    groups = [
        [lead, *sorted(extra, key=lambda li: li.start)]
        for lead, extra in zip(leads, attached, strict=True)
    ]
    groups += [[line] for line in alone]
    return sorted(groups, key=lambda g: min(line.start for line in g))


def _colors(doc: KaraokeDoc, theme: Theme) -> dict[str | None, str]:
    colors: dict[str | None, str] = {None: theme.colors.sung}
    palette = theme.colors.singers
    for i, singer in enumerate(doc.singers):
        if singer.color is not None:
            colors[singer.id] = singer.color
        elif len(doc.singers) >= 2 and palette:
            colors[singer.id] = palette[i % len(palette)]
        else:
            colors[singer.id] = theme.colors.sung
    return colors


def _rows(
    lines: list[Line],
    theme: Theme,
    font_px: float,
    usable: float,
    metrics: FontMetrics,
    colors: dict[str | None, str],
) -> list[Row]:
    """The rows of one group, stacked from y = 0 (moved into place later)."""
    rows: list[Row] = []
    top = 0.0
    for line in lines:
        backing = line.role == "backing"
        role_scale = theme.backing.scale if backing else 1.0
        words = _display_words(line, backing and theme.backing.brackets)
        texts = ["".join(p.text for p in word.parts) for word in words]
        indices, wrap_scale = wrap(
            texts, font_px * role_scale, usable, theme.layout.max_rows, metrics
        )
        scale = role_scale * wrap_scale
        row_px = font_px * scale
        height = row_px * theme.layout.line_spacing
        for row_words in indices:
            text = " ".join(texts[i] for i in row_words)
            rows.append(
                Row(
                    line_id=line.id,
                    role=line.role,
                    singer=line.singer,
                    color=colors.get(line.singer, theme.colors.sung),
                    words=[words[i] for i in row_words],
                    text=text,
                    scale=scale,
                    x=0.0,
                    y=top + height / 2,
                    width=metrics.width(text, row_px),
                    height=height,
                )
            )
            top += height
    return rows


def _height(rows: list[Row]) -> float:
    total = 0.0
    for row in rows:
        total += row.height
    return total


def _countdown(
    block: int, row: Row, y_offset: float, start: float, end: float, font_px: float, theme: Theme
) -> Countdown:
    """Dots above the left end of the first row of a block, going out right to left."""
    anim = theme.animation
    left = row.x - row.width / 2
    y = row.y + y_offset - row.height / 2 - 0.45 * font_px
    dots = [
        Dot(
            x=left + 0.2 * font_px + j * 0.55 * font_px,
            y=y,
            r=0.14 * font_px,
            off=end - j * anim.countdown_step,
        )
        for j in range(anim.countdown_dots)
    ]
    return Countdown(block=block, start=start, end=end, dots=dots)


def _ease(u: float) -> float:
    """Ease-out cubic, written as products so Python and JS round alike."""
    v = 1 - u
    return 1 - v * v * v


def _scroll_step(plan: ScrollPlan, t: float) -> tuple[int, float]:
    """The group the list is moving to (or resting on) at `t`, and how far it has got (0-1)."""
    k = bisect_right(plan.switches, t)
    if k == 0:
        return 0, 1.0
    if plan.transition <= 0:
        return k, 1.0
    u = (t - plan.switches[k - 1]) / plan.transition
    return k, _ease(u) if u < 1 else 1.0


def scroll_focus(layout: Layout, t: float) -> float:
    """Which group is on the anchor at `t`, with the fraction of a move in progress."""
    assert layout.scroll is not None
    k, done = _scroll_step(layout.scroll, t)
    return k - 1 + done if k > 0 else 0.0


def scroll_offset(layout: Layout, t: float) -> float:
    """How far down the list is drawn at `t`, in px."""
    assert layout.scroll is not None
    plan = layout.scroll
    k, done = _scroll_step(plan, t)
    if k == 0:
        return plan.offsets[0]
    return plan.offsets[k - 1] + (plan.offsets[k] - plan.offsets[k - 1]) * done


def scroll_opacity(rank: float, visible: int) -> float:
    """Opacity of a group `rank` places after the one on the anchor (negative: already sung)."""
    if rank < 0:
        return max(0.0, 1 + 0.6 * rank)
    if rank <= visible - 1:
        return 1 - 0.12 * rank
    return max(0.0, (1 - 0.12 * (visible - 1)) * (visible - rank))


def _scroll_layout(
    theme: Theme,
    width: float,
    height: float,
    font_px: float,
    rows_by_group: list[list[Row]],
    starts: list[float],
    ends: list[float],
    blocks: list[list[int]],
) -> Layout:
    anim = theme.animation
    visible = theme.layout.visible_lines
    anchor = SCROLL_ANCHOR[theme.layout.position] * height
    n = len(rows_by_group)
    tops: list[float] = []
    top = 0.0
    for rows in rows_by_group:
        tops.append(top)
        top += _height(rows) + SCROLL_GAP * font_px
    offsets = [anchor - (tops[k] + _height(rows_by_group[k]) / 2) for k in range(n)]
    switches: list[float] = []
    for k in range(1, n):
        switch = min(ends[k - 1] + anim.hold, starts[k] - anim.transition - SCROLL_SETTLE)
        if switches:
            switch = max(switch, switches[-1] + anim.transition)
        switches.append(switch)
    plan = ScrollPlan(
        offsets=offsets, switches=switches, transition=anim.transition, visible=visible
    )
    last_hide = max(ends) + 2 * anim.hold if ends else 0.0
    groups: list[Group] = []
    block_of = {k: b for b, members in enumerate(blocks) for k in members}
    for k, rows in enumerate(rows_by_group):
        show = switches[k - visible] if k >= visible else 0.0
        hide = switches[k + 1] + anim.transition if k + 1 < len(switches) else last_hide
        placed = [row.model_copy(update={"x": width / 2, "y": tops[k] + row.y}) for row in rows]
        groups.append(
            Group(
                index=k,
                block=block_of[k],
                slot=0,
                start=starts[k],
                end=ends[k],
                show=show,
                hide=hide,
                rows=placed,
            )
        )
    countdowns: list[Countdown] = []
    previous_end = 0.0
    for b, members in enumerate(blocks):
        first = members[0]
        gap_before = starts[first] - previous_end if b > 0 else starts[first]
        if (
            anim.countdown_min_gap > 0
            and anim.countdown_dots > 0
            and gap_before >= anim.countdown_min_gap
        ):
            start = max(
                starts[first] - anim.countdown_dots * anim.countdown_step, groups[first].show
            )
            countdowns.append(
                _countdown(
                    b, groups[first].rows[0], offsets[first], start, starts[first], font_px, theme
                )
            )
        previous_end = max(ends[k] for k in members)
    return Layout(
        width=width,
        height=height,
        font_px=font_px,
        mode="scroll",
        groups=groups,
        countdowns=countdowns,
        bars=[],
        scroll=plan,
    )


def build_layout(
    doc: KaraokeDoc, theme: Theme, width: float, height: float, metrics: FontMetrics
) -> Layout:
    margin_x = theme.layout.margin * width
    margin_y = theme.layout.margin * height
    usable = width - 2 * margin_x
    font_px = min(
        theme.layout.font_size * height,
        usable / (theme.layout.min_row_chars * metrics.average_lowercase / metrics.upem),
    )
    colors = _colors(doc, theme)
    anim = theme.animation
    slots = theme.layout.visible_lines

    lines_by_group = _groups(doc)
    starts = [min(line.start for line in g) for g in lines_by_group]
    ends = [max(line.end for line in g) for g in lines_by_group]
    rows_by_group = [_rows(g, theme, font_px, usable, metrics, colors) for g in lines_by_group]

    # Blocks: runs of groups between instrumental breaks.
    blocks: list[list[int]] = []
    latest_end = 0.0
    for k in range(len(lines_by_group)):
        gap = starts[k] - latest_end
        if k == 0 or (anim.countdown_min_gap > 0 and gap >= anim.countdown_min_gap):
            blocks.append([])
        blocks[-1].append(k)
        latest_end = ends[k] if k == 0 else max(latest_end, ends[k])

    if theme.layout.mode == "scroll":
        return _scroll_layout(theme, width, height, font_px, rows_by_group, starts, ends, blocks)

    show = [0.0] * len(lines_by_group)
    hide = [0.0] * len(lines_by_group)
    slot_of = [0] * len(lines_by_group)
    block_of = [0] * len(lines_by_group)
    groups: list[Group] = []
    countdowns: list[Countdown] = []
    bars: list[BreakBar] = []
    previous_hide = 0.0
    previous_end = 0.0
    for b, members in enumerate(blocks):
        first = members[0]
        block_start = starts[first]
        block_end = max(ends[k] for k in members)
        block_show = max(block_start - anim.lead_in, previous_hide, 0.0)
        if b + 1 < len(blocks):
            block_hide = min(block_end + 2 * anim.hold, starts[blocks[b + 1][0]])
        else:
            block_hide = block_end + 2 * anim.hold
        for j, k in enumerate(members):
            slot_of[k] = j % slots
            block_of[k] = b
            show[k] = block_show if j < slots else hide[members[j - slots]]
            if j + slots < len(members):
                later = starts[members[j + slots]]
                # The next line in this slot shows MIN_LEAD early, never before this one ends.
                ready = max(later - MIN_LEAD, ends[k])
                hide[k] = max(show[k], min(ends[k] + anim.hold, ready))
            else:
                hide[k] = block_hide

        # Slot bands: as tall as the tallest group they hold in this block.
        bands = [0.0] * slots
        for k in members:
            bands[slot_of[k]] = max(bands[slot_of[k]], _height(rows_by_group[k]))
        total = 0.0
        for band in bands:
            total += band
        if theme.layout.position == "bottom":
            top = height - margin_y - total
        elif theme.layout.position == "top":
            top = margin_y
        else:
            top = height / 2 - total / 2
        band_tops = []
        for band in bands:
            band_tops.append(top)
            top += band
        for k in members:
            slot = slot_of[k]
            group_height = _height(rows_by_group[k])
            if slots == 1 or (slots % 2 == 1 and slot == slots // 2):
                offset = band_tops[slot] + (bands[slot] - group_height) / 2
            elif slot < slots / 2:
                offset = band_tops[slot] + bands[slot] - group_height
            else:
                offset = band_tops[slot]
            rows_by_group[k] = [
                row.model_copy(update={"x": width / 2, "y": offset + row.y})
                for row in rows_by_group[k]
            ]

        gap_before = block_start - previous_end if b > 0 else block_start
        if (
            anim.countdown_min_gap > 0
            and anim.countdown_dots > 0
            and gap_before >= anim.countdown_min_gap
        ):
            start = max(block_start - anim.countdown_dots * anim.countdown_step, block_show)
            countdowns.append(
                _countdown(b, rows_by_group[first][0], 0.0, start, block_start, font_px, theme)
            )

        if anim.break_bar_min > 0 and block_show - previous_hide >= anim.break_bar_min:
            bars.append(
                BreakBar(
                    start=previous_hide,
                    end=block_show,
                    x=width / 2,
                    y=band_tops[0] + total / 2,
                    width=0.3 * usable,
                    height=0.08 * font_px,
                )
            )
        previous_hide = block_hide
        previous_end = block_end

    for k, rows in enumerate(rows_by_group):
        groups.append(
            Group(
                index=k,
                block=block_of[k],
                slot=slot_of[k],
                start=starts[k],
                end=ends[k],
                show=show[k],
                hide=hide[k],
                rows=rows,
            )
        )
    return Layout(
        width=width,
        height=height,
        font_px=font_px,
        mode=theme.layout.mode,
        groups=groups,
        countdowns=countdowns,
        bars=bars,
    )
