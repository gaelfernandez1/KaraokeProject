import re
import subprocess
from itertools import pairwise
from pathlib import Path

import pytest

from karaoke_contracts import KaraokeDoc, Line, Part, Provenance, Singer, Word
from karaoke_engine.cli import main
from karaoke_engine.subtitles.ass import ass_color, build_ass
from karaoke_engine.subtitles.layout import build_layout
from karaoke_engine.subtitles.themes import fonts_dir, load_theme, theme_metrics


def _line(
    line_id: str,
    words: list[tuple[str, float, float]],
    role: str = "lead",
    singer: str | None = "s1",
    parts: dict[int, list[tuple[str, float, float]]] | None = None,
) -> Line:
    built = [
        Word(
            text=text,
            start=start,
            end=end,
            parts=[Part(text=t, start=s, end=e) for t, s, e in (parts or {}).get(i, [])],
        )
        for i, (text, start, end) in enumerate(words)
    ]
    return Line.model_validate(
        {
            "id": line_id,
            "start": built[0].start,
            "end": built[-1].end,
            "singer": singer,
            "role": role,
            "words": built,
        }
    )


def _doc(*lines: Line, singers: int = 1) -> KaraokeDoc:
    return KaraokeDoc(
        id="test",
        title="Test",
        language="gl",
        duration=60.0,
        audio={"instrumental": "instrumental.m4a"},
        singers=[Singer(id=f"s{i + 1}") for i in range(singers)],
        lines=list(lines),
        provenance=Provenance(lyrics_source="user", engine_version="test"),
    )


def _events(ass: str, style: str = "Lead") -> list[str]:
    return [
        line
        for line in ass.splitlines()
        if line.startswith("Dialogue: 0,") and f",{style}," in line
    ]


def _cs(stamp: str) -> int:
    hours, minutes, rest = stamp.split(":")
    seconds, hundredths = rest.split(".")
    return ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 100 + int(hundredths)


def _karaoke(event: str) -> list[tuple[str, int, str]]:
    """(tag, centiseconds, text) for every karaoke syllable of an event."""
    text = event.split(",", 9)[9]
    return [(m[0], int(m[1]), m[2]) for m in re.findall(r"\{[^}]*\\(kf|k)(\d+)\}([^{]*)", text)]


SONG = _doc(
    _line(
        "l1",
        [("Bailamos", 10.0, 10.62), ("sempre", 10.8, 11.6)],
        parts={0: [("Bai", 10.0, 10.2), ("la", 10.2, 10.5), ("mos", 10.5, 10.62)]},
    ),
    _line("l2", [("Collín", 12.0, 12.4), ("flores", 12.5, 12.6)]),
)


def test_ass_has_one_event_per_row() -> None:
    theme = load_theme("clasico")
    layout = build_layout(SONG, theme, 1920, 1080, theme_metrics(theme))

    ass = build_ass(SONG, theme, 1920, 1080)

    assert len(_events(ass)) == sum(len(g.rows) for g in layout.groups) == 2
    assert "PlayResX: 1920" in ass
    assert "PlayResY: 1080" in ass
    assert "WrapStyle: 2" in ass


def test_ass_syllables_follow_the_parts() -> None:
    first = _events(build_ass(SONG, load_theme("clasico"), 1920, 1080))[0]

    assert [(tag, text) for tag, _, text in _karaoke(first)] == [
        ("k", ""),
        ("kf", "Bai"),
        ("kf", "la"),
        ("kf", "mos"),
        ("k", " "),
        ("kf", "sempre"),
    ]
    assert [cs for _, cs, _ in _karaoke(first)][1:] == [20, 30, 12, 18, 80]


def test_ass_karaoke_durations_do_not_drift() -> None:
    words = [(f"la{i}", 5.0 + i / 3, 5.0 + (i + 1) / 3) for i in range(9)]
    doc = _doc(_line("l1", words))

    (event,) = _events(build_ass(doc, load_theme("clasico"), 1920, 1080))
    start = _cs(event.split(",")[1])
    total = sum(cs for _, cs, _ in _karaoke(event))

    # The last syllable ends at 8.0 s, 0.05 s early (anticipation): 795 cs from the event start.
    assert start + total == 795


def test_ass_word_without_parts_uses_one_syllable() -> None:
    (event,) = _events(
        build_ass(_doc(_line("l1", [("Ola", 10, 11)])), load_theme("clasico"), 1920, 1080)
    )

    assert [(tag, text) for tag, _, text in _karaoke(event)] == [("k", ""), ("kf", "Ola")]


def test_ass_word_mode_uses_k() -> None:
    (event,) = _events(
        build_ass(_doc(_line("l1", [("Ola", 10, 11)])), load_theme("contraste"), 1920, 1080)
    )

    assert [tag for tag, _, _ in _karaoke(event)] == ["k", "k"]


def test_ass_rows_sit_where_the_browser_centres_them() -> None:
    theme = load_theme("clasico")
    metrics = theme_metrics(theme)
    layout = build_layout(SONG, theme, 1920, 1080, metrics)
    row = layout.groups[0].rows[0]

    first = _events(build_ass(SONG, theme, 1920, 1080))[0]

    y = row.y - metrics.ass_center_shift(layout.font_px * row.scale)
    assert f"\\pos({row.x:g},{y:.2f}".rstrip("0").rstrip(".") in first


def test_ass_times_run_ahead_by_the_anticipation() -> None:
    theme = load_theme("clasico")
    layout = build_layout(SONG, theme, 1920, 1080, theme_metrics(theme))

    first = _events(build_ass(SONG, theme, 1920, 1080))[0]

    assert _cs(first.split(",")[1]) == round((layout.groups[0].show - 0.05) * 100)
    assert _cs(first.split(",")[2]) == round((layout.groups[0].hide - 0.05) * 100)


def test_ass_singer_colors() -> None:
    doc = _doc(
        _line("l1", [("Ti", 10, 11)], singer="s1"),
        _line("l2", [("eu", 11.5, 12)], singer="s2"),
        singers=2,
    )

    first, second = _events(build_ass(doc, load_theme("clasico"), 1920, 1080))

    assert "\\1c&H31C5FF&" in first
    assert "\\1c&HFFD14F&" in second


def test_ass_color_converts_alpha() -> None:
    assert ass_color("#FFC531") == ("&H31C5FF&", "&H00&")
    assert ass_color("#FFFFFF70") == ("&HFFFFFF&", "&H8F&")


def test_ass_backing_style_smaller() -> None:
    theme = load_theme("clasico")
    doc = _doc(_line("l1", [("Ola", 10, 12)]), _line("b1", [("ei", 10.5, 11)], role="backing"))
    layout = build_layout(doc, theme, 1920, 1080, theme_metrics(theme))
    backing = layout.groups[0].rows[1]

    (event,) = _events(build_ass(doc, theme, 1920, 1080), "Backing")

    size = theme_metrics(theme).ass_font_size(layout.font_px * backing.scale)
    assert f"\\fs{size:.2f}" in event
    assert "[ei]" in event


def test_ass_escapes_override_braces() -> None:
    (event,) = _events(
        build_ass(_doc(_line("l1", [("{ola}", 10, 11)])), load_theme("clasico"), 1920, 1080)
    )

    assert "(ola)" in event


def test_ass_countdown_dots() -> None:
    ass = build_ass(_doc(_line("l1", [("Ola", 10, 11)])), load_theme("clasico"), 1920, 1080)

    dots = [line for line in ass.splitlines() if ",Dots," in line]
    assert len(dots) == 3
    # Each dot from 6.95 s until its own moment, rightmost first.
    assert [d.split(",")[1:3] for d in dots] == [
        ["0:00:06.95", "0:00:09.95"],
        ["0:00:06.95", "0:00:08.95"],
        ["0:00:06.95", "0:00:07.95"],
    ]


def test_cli_subtitles_writes_file(bare_package: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.ass"

    assert main(["subtitles", str(bare_package), "--size", "1080x1920", "-o", str(out)]) == 0
    assert "PlayResY: 1920" in out.read_text(encoding="utf-8")


def test_cli_subtitles_rejects_a_bad_size(
    bare_package: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["subtitles", str(bare_package), "--size", "big"]) == 2
    assert "size" in capsys.readouterr().err


# Pure red for what is sung and pure blue for what is not, no outline or shadow: easy to find.
TEST_THEME = load_theme("clasico").model_copy(
    update={
        "colors": load_theme("clasico").colors.model_copy(
            update={"sung": "#FF0000", "unsung": "#0000FF", "shadow": None}
        ),
        "layout": load_theme("clasico").layout.model_copy(update={"outline_width": 0.0}),
    }
)
WIDTH, HEIGHT = 640, 360


def _frame(ass_path: Path, t: float) -> list[bytes]:
    raw = subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", f"color=black:s={WIDTH}x{HEIGHT}:d=20:r=100",
            "-vf", f"subtitles={ass_path}:fontsdir={fonts_dir()}", "-ss", f"{t:.3f}",
            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ],
        capture_output=True,
        check=True,
    ).stdout  # fmt: skip
    return [raw[y * WIDTH * 3 : (y + 1) * WIDTH * 3] for y in range(HEIGHT)]


def _rightmost_red(rows: list[bytes]) -> int:
    right = -1
    for row in rows:
        for x in range(WIDTH):
            red, blue = row[3 * x], row[3 * x + 2]
            if red > 160 and blue < 90 and x > right:
                right = x
    return right


@pytest.mark.usefixtures("ffmpeg")
def test_libass_fill_edge_follows_the_syllable(tmp_path: Path) -> None:
    # One word of one syllable, sung from 10 to 12 s.
    doc = _doc(_line("l1", [("MMMMMM", 10.0, 12.0)]))
    ass_path = tmp_path / "t.ass"
    ass_path.write_text(build_ass(doc, TEST_THEME, WIDTH, HEIGHT), encoding="utf-8")

    (row,) = build_layout(doc, TEST_THEME, WIDTH, HEIGHT, theme_metrics(TEST_THEME)).groups[0].rows
    band = slice(round(row.y - row.height / 2), round(row.y + row.height / 2))

    def edge(t: float) -> int:
        # Only the row's band: the countdown dots above it are drawn in the sung colour too.
        return _rightmost_red(_frame(ass_path, t)[band])

    # Times on screen run 0.05 s ahead of the song.
    before, start, middle, end = edge(9.5), edge(9.97), edge(10.95), edge(11.97)
    assert before == -1
    assert end - start > 100
    assert abs(middle - (start + end) / 2) <= 0.06 * (end - start)


@pytest.mark.usefixtures("ffmpeg")
def test_cli_preview_writes_a_video(bare_package: Path, tmp_path: Path) -> None:
    from karaoke_engine.demo import synthesize_package_audio

    synthesize_package_audio(bare_package)
    out = tmp_path / "preview.mp4"

    code = main(
        ["preview", str(bare_package), "--size", "320x180", "--start", "4", "--duration", "2",
         "-o", str(out)]
    )  # fmt: skip

    assert code == 0
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
         "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
        capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    assert "video,320,180" in probe
    assert "audio" in probe
    assert abs(float(probe.strip().splitlines()[-1]) - 2.0) < 0.2


SCROLLING = _doc(
    _line("l1", [("Ola", 10, 12)]),
    _line("l2", [("mar", 12.5, 14)]),
    _line("l3", [("de", 14.5, 16)]),
    _line("l4", [("Vigo", 25, 27)]),
)


def test_ass_scroll_rows_follow_the_list() -> None:
    theme = load_theme("moderno")
    metrics = theme_metrics(theme)
    layout = build_layout(SCROLLING, theme, 1080, 1920, metrics)
    assert layout.scroll is not None
    ass = build_ass(SCROLLING, theme, 1080, 1920)

    events = [e for e in _events(ass) if e.endswith("de")]
    stamps = [(_cs(e.split(",")[1]), _cs(e.split(",")[2])) for e in events]
    group = layout.groups[2]
    shift = 0.05
    # One unbroken run of events from when the row shows until it hides.
    assert stamps[0][0] == max(0, round((group.show - shift) * 100))
    assert stamps[-1][1] == round((group.hide - shift) * 100)
    assert all(a[1] == b[0] for a, b in pairwise(stamps))
    # Still while the list rests, moving while it scrolls.
    assert any("\\pos(" in e for e in events)
    moves = [e for e in events if "\\move(" in e]
    assert len(moves) >= 4
    assert all("\\fad" not in e for e in events)


def _syllable_starts(event: str) -> list[int]:
    """Absolute start (cs) of every non-empty syllable, following \\kt and the durations."""
    text = event.split(",", 9)[9]
    clock = _cs(event.split(",")[1])
    kt = re.search(r"\\kt(-?\d+)", text)
    if kt:
        clock += int(kt[1])
    starts = []
    for _tag, cs, syllable in re.findall(r"\{[^}]*\\(kf|k)(\d+)\}([^{]*)", text):
        if syllable.strip():
            starts.append(clock)
        clock += int(cs)
    return starts


def test_ass_scroll_karaoke_continues_across_cuts() -> None:
    duo = _doc(
        _line("l1", [("Ti", 6.0, 6.5), ("cantas", 6.6, 7.5)], singer="s1"),
        _line("l2", [("eu", 7.0, 7.4), ("respondo", 7.5, 8.6)], singer="s2"),
        _line("l3", [("xuntos", 9.0, 10.0)], singer="s1"),
        singers=2,
    )
    events = [
        e for e in _events(build_ass(duo, load_theme("moderno"), 1920, 1080)) if "cantas" in e
    ]

    assert len(events) > 1
    # Wherever an event of the row starts, each syllable keeps its own start: 5.95 and 6.55 s.
    assert {tuple(_syllable_starts(e)) for e in events} == {(595, 655)}


def test_ass_keeps_every_field_on_its_line() -> None:
    clasico = load_theme("clasico")
    theme = clasico.model_copy(
        update={"font": clasico.font.model_copy(update={"family": "Nunito, Black"})}
    )
    doc = _doc(_line("l1", [("Ola\nmar", 10, 11)])).model_copy(update={"title": "Dúas\nliñas"})

    ass = build_ass(doc, theme, 1920, 1080)

    assert all(
        line == "" or line.startswith(("[", ";", "Script", "Play", "Wrap", "Scaled", "YCbCr",
                                       "Format:", "Style:", "Dialogue:"))
        for line in ass.splitlines()
    )  # fmt: skip
    assert all(line.count(",") == 22 for line in ass.splitlines() if line.startswith("Style:"))
