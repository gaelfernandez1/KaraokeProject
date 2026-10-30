from collections.abc import Sequence

import pytest

from karaoke_contracts import KaraokeDoc, Line, Part, Provenance, Singer, Theme, Word
from karaoke_engine.subtitles.layout import (
    Layout,
    build_layout,
    scroll_focus,
    scroll_offset,
    scroll_opacity,
    wrap,
)
from karaoke_engine.subtitles.metrics import FontMetrics
from karaoke_engine.subtitles.themes import load_theme

# Every character is half an em wide: widths are easy to work out by hand.
MONO = FontMetrics(
    upem=1000,
    ascender=900,
    descender=-300,
    win_ascent=1000,
    win_descent=250,
    default_advance=500,
    average_lowercase=500,
    advances={},
)
# With the classic theme on a 1000x1000 screen: margins of 50, usable width 900,
# font 75 px (0.075 x 1000; 22 letters would allow 81.8), rows of 93.75 px, 24 letters per row.
SIZE = 1000


def _theme(**layout: object) -> Theme:
    theme = load_theme("clasico")
    return theme.model_copy(update={"layout": theme.layout.model_copy(update=layout)})


def _line(
    line_id: str,
    start: float,
    end: float,
    text: str = "la",
    role: str = "lead",
    singer: str | None = "s1",
    parts: Sequence[tuple[str, float, float]] = (),
) -> Line:
    texts = text.split()
    step = (end - start) / len(texts)
    words = [
        Word(text=t, start=start + i * step, end=start + (i + 1) * step)
        for i, t in enumerate(texts)
    ]
    if parts:
        words[0] = words[0].model_copy(
            update={"parts": [Part(text=p, start=s, end=e) for p, s, e in parts]}
        )
    return Line.model_validate(
        {"id": line_id, "start": start, "end": end, "singer": singer, "role": role, "words": words}
    )


def _doc(*lines: Line, singers: int = 1) -> KaraokeDoc:
    return KaraokeDoc(
        id="test",
        title="Test",
        language="gl",
        duration=120.0,
        audio={"instrumental": "instrumental.m4a"},
        singers=[Singer(id=f"s{i + 1}") for i in range(singers)],
        lines=list(lines),
        provenance=Provenance(lyrics_source="user", engine_version="test"),
    )


def _layout(*lines: Line, theme: Theme | None = None, singers: int = 1) -> Layout:
    return build_layout(_doc(*lines, singers=singers), theme or _theme(), SIZE, SIZE, MONO)


def test_wrap_one_row_when_it_fits() -> None:
    assert wrap(["Ola", "que", "tal"], 75, 900, 2, MONO) == ([[0, 1, 2]], 1.0)


def test_wrap_balances_two_rows() -> None:
    words = ["aaaaa", "bbbbb", "ccccc", "ddddd", "eeeee", "fffff"]

    assert wrap(words, 75, 900, 2, MONO) == ([[0, 1, 2], [3, 4, 5]], 1.0)


def test_wrap_prefers_break_after_comma() -> None:
    plain = ["uno", "dous", "tres", "catro", "cinco", "seis", "sete"]
    comma = ["uno", "dous", "tres,", "catro", "cinco", "seis", "sete"]

    assert wrap(plain, 75, 900, 2, MONO)[0] == [[0, 1, 2, 3], [4, 5, 6]]
    assert wrap(comma, 75, 900, 2, MONO)[0] == [[0, 1, 2], [3, 4, 5, 6]]


def test_wrap_shrinks_when_two_rows_do_not_fit() -> None:
    rows, scale = wrap(["a" * 20, "b" * 20, "c" * 20], 75, 900, 2, MONO)

    assert rows == [[0], [1, 2]]
    assert scale == 0.6


def test_wrap_shrinks_a_single_long_word() -> None:
    assert wrap(["a" * 30], 75, 900, 2, MONO) == ([[0]], 0.8)


def test_wrap_keeps_one_row_when_max_rows_is_one() -> None:
    assert wrap(["a" * 15, "b" * 15], 75, 900, 1, MONO) == ([[0, 1]], 900 / (31 * 37.5))


def test_pages_alternate_slots() -> None:
    layout = _layout(
        _line("l1", 10, 12), _line("l2", 12.5, 14), _line("l3", 14.5, 16), _line("l4", 16.5, 18)
    )

    assert layout.font_px == 75
    assert [g.slot for g in layout.groups] == [0, 1, 0, 1]
    assert [g.show for g in layout.groups] == pytest.approx([7, 7, 12.4, 14.4])
    assert [g.hide for g in layout.groups] == pytest.approx([12.4, 14.4, 18.8, 18.8])
    # Two bands of 93.75 px stacked on the bottom margin (950): the rows meet in the middle.
    assert [g.rows[0].y for g in layout.groups] == pytest.approx(
        [809.375, 903.125, 809.375, 903.125]
    )
    assert all(g.rows[0].x == 500 for g in layout.groups)


def test_slot_reused_after_hold() -> None:
    layout = _layout(_line("l1", 10, 12), _line("l2", 12.1, 12.5), _line("l3", 12.6, 14))

    # l3 needs l1's slot half a second before it is sung, even if l1's hold is not over.
    assert layout.groups[0].hide == pytest.approx(12.1)
    assert layout.groups[2].show == pytest.approx(12.1)


def test_a_line_stays_until_it_is_sung_even_with_one_slot() -> None:
    layout = _layout(_line("l1", 2, 4), _line("l2", 4.2, 6), theme=_theme(visible_lines=1))

    assert layout.groups[0].hide == pytest.approx(4)
    assert layout.groups[1].show == pytest.approx(4)


def test_break_starts_new_block_with_countdown() -> None:
    layout = _layout(_line("l1", 10, 12), _line("l2", 20, 22))

    assert [g.block for g in layout.groups] == [0, 1]
    assert [g.slot for g in layout.groups] == [0, 0]
    assert layout.groups[0].hide == pytest.approx(12.8)
    assert layout.groups[1].show == pytest.approx(17)
    assert [(c.block, c.start, c.end) for c in layout.countdowns] == [(0, 7, 10), (1, 17, 20)]
    assert layout.bars == []


def test_countdown_dots_turn_off_right_to_left() -> None:
    (countdown,) = _layout(_line("l1", 10, 12, "Ola")).countdowns
    row = _layout(_line("l1", 10, 12, "Ola")).groups[0].rows[0]

    assert [d.off for d in countdown.dots] == pytest.approx([10, 9, 8])
    left = row.x - row.width / 2
    assert [d.x for d in countdown.dots] == pytest.approx([left + 15, left + 56.25, left + 97.5])
    assert all(d.y == pytest.approx(row.y - row.height / 2 - 33.75) for d in countdown.dots)
    assert all(d.r == pytest.approx(10.5) for d in countdown.dots)


def test_first_line_at_zero() -> None:
    layout = _layout(_line("l1", 0, 1))

    assert layout.groups[0].show == 0
    assert layout.countdowns == []


def test_break_bar_on_long_gaps() -> None:
    layout = _layout(_line("l1", 10, 12), _line("l2", 30, 32))

    (bar,) = layout.bars
    assert (bar.start, bar.end) == pytest.approx((12.8, 27))
    assert bar.x == 500
    assert bar.width == pytest.approx(270)
    assert bar.height == pytest.approx(6)


def test_long_intro_gets_a_bar() -> None:
    (bar,) = _layout(_line("l1", 30, 32)).bars

    assert (bar.start, bar.end) == pytest.approx((0, 27))


def test_backing_joins_overlapping_lead() -> None:
    layout = _layout(_line("l1", 10, 14, "Ola amor"), _line("b1", 12, 13.5, "ei", role="backing"))

    (group,) = layout.groups
    lead, backing = group.rows
    assert backing.text == "[ei]"
    assert backing.words[0].parts[0].text == "[ei]"
    assert backing.scale == pytest.approx(0.72)
    assert backing.height == pytest.approx(75 * 0.72 * 1.25)
    assert backing.y == pytest.approx(lead.y + lead.height / 2 + backing.height / 2)


def test_backing_right_after_its_lead_joins_it() -> None:
    layout = _layout(_line("l1", 10, 14), _line("b1", 14.5, 15, role="backing"))

    assert len(layout.groups) == 1


def test_backing_alone_forms_group() -> None:
    layout = _layout(_line("l1", 10, 11), _line("b1", 20, 21, "ei", role="backing"))

    assert [[r.line_id for r in g.rows] for g in layout.groups] == [["l1"], ["b1"]]
    assert layout.groups[1].block == 1


def test_brackets_go_around_the_parts() -> None:
    line = _line(
        "b1", 10, 12, "vente xa", role="backing", parts=[("ven", 10, 10.5), ("te", 10.5, 11)]
    )
    (row,) = _layout(_line("l1", 9, 12), line).groups[0].rows[1:]

    assert [p.text for p in row.words[0].parts] == ["[ven", "te"]
    assert [p.text for p in row.words[1].parts] == ["xa]"]


def test_overlapping_lead_lines_use_both_slots() -> None:
    layout = _layout(_line("l1", 10, 13, singer="s1"), _line("l2", 11, 14, singer="s2"), singers=2)

    assert [g.slot for g in layout.groups] == [0, 1]
    assert [g.show for g in layout.groups] == [7, 7]
    assert [g.rows[0].color for g in layout.groups] == ["#FFC531", "#4FD1FF"]


def test_one_singer_uses_the_sung_colour() -> None:
    assert _layout(_line("l1", 10, 12)).groups[0].rows[0].color == "#FFC531"


def test_rows_never_overlap_in_a_block() -> None:
    long = "unha liña moi longa que non cabe nunha soa fila da pantalla"
    layout = _layout(
        _line("l1", 10, 13, long),
        _line("b1", 11, 12, "eh eh", role="backing"),
        _line("l2", 13.5, 15, "curta"),
        _line("l3", 15.5, 18, long),
        _line("l4", 18.5, 20, "outra curta"),
    )

    boxes = {
        g.index: [(r.y - r.height / 2, r.y + r.height / 2) for r in g.rows] for g in layout.groups
    }
    slot0 = [box for g in layout.groups if g.slot == 0 for box in boxes[g.index]]
    slot1 = [box for g in layout.groups if g.slot == 1 for box in boxes[g.index]]
    assert max(bottom for _, bottom in slot0) <= min(top for top, _ in slot1) + 1e-9
    assert all(top >= 50 - 1e-9 and bottom <= 950 + 1e-9 for top, bottom in slot0 + slot1)
    assert len(layout.groups[0].rows) == 3


def test_layout_accepts_doc_without_singers() -> None:
    doc = _doc(_line("l1", 10, 12, singer=None)).model_copy(update={"singers": []})

    row = build_layout(doc, _theme(), SIZE, SIZE, MONO).groups[0].rows[0]
    assert row.singer is None
    assert row.color == "#FFC531"


def test_narrow_screen_shrinks_font_to_fit_letters() -> None:
    layout = build_layout(_doc(_line("l1", 10, 12)), _theme(), 390, 844, MONO)

    # Usable width 351 px for 22 letters of half an em.
    assert layout.font_px == pytest.approx(351 / 11)


def _scroll(**layout: object) -> Theme:
    return _theme(mode="scroll", visible_lines=3, position="center", **layout)


SCROLL_LINES = (
    _line("l1", 10, 12),
    _line("l2", 12.5, 14),
    _line("l3", 14.5, 16),
    _line("l4", 25, 27),
)


def _scroll_theme() -> Theme:
    theme = _scroll()
    return theme.model_copy(
        update={"animation": theme.animation.model_copy(update={"transition": 0.4})}
    )


def test_scroll_switches_focus_before_the_next_line() -> None:
    layout = _layout(*SCROLL_LINES, theme=_scroll_theme())

    assert layout.scroll is not None
    # 0.65 s before the next line, unless the hold of the line before ends sooner.
    assert layout.scroll.switches == pytest.approx([11.85, 13.85, 16.4])


def test_scroll_offsets_put_the_focus_line_on_the_anchor() -> None:
    layout = _layout(*SCROLL_LINES, theme=_scroll_theme())

    # Rows of 93.75 px with gaps of 26.25: group k is centred at 120 k + 46.875 in the list,
    # and the anchor is at 42 % of the height.
    assert layout.scroll is not None
    assert layout.scroll.offsets == pytest.approx([373.125 - 120 * k for k in range(4)])
    assert [g.rows[0].y for g in layout.groups] == pytest.approx(
        [46.875 + 120 * k for k in range(4)]
    )


def test_scroll_groups_show_while_within_reach_of_the_focus() -> None:
    layout = _layout(*SCROLL_LINES, theme=_scroll_theme())

    assert [g.show for g in layout.groups] == pytest.approx([0, 0, 0, 11.85])
    assert [g.hide for g in layout.groups] == pytest.approx([14.25, 16.8, 27.8, 27.8])


def test_scroll_offset_eases_between_lines() -> None:
    layout = _layout(*SCROLL_LINES, theme=_scroll_theme())

    assert scroll_offset(layout, 11) == pytest.approx(373.125)
    assert scroll_offset(layout, 12.05) == pytest.approx(373.125 - 120 * 0.875)
    assert scroll_offset(layout, 13) == pytest.approx(253.125)
    assert scroll_focus(layout, 12.05) == pytest.approx(0.875)


def test_scroll_opacity_by_rank() -> None:
    assert [scroll_opacity(r, 3) for r in (-2, -1, 0, 1, 2, 2.5, 3)] == pytest.approx(
        [0, 0.4, 1, 0.88, 0.76, 0.38, 0]
    )


def test_scroll_countdown_sits_above_its_line_where_the_list_stops() -> None:
    layout = _layout(*SCROLL_LINES, theme=_scroll_theme())

    countdown = layout.countdowns[-1]
    row = layout.groups[3].rows[0]
    assert (countdown.start, countdown.end) == pytest.approx((22, 25))
    assert countdown.dots[0].y == pytest.approx(row.y + 13.125 - row.height / 2 - 33.75)
    assert layout.bars == []
