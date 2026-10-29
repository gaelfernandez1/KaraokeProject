import random
from pathlib import Path

import numpy as np
import pytest

from karaoke_bench.paths import BenchPaths
from karaoke_bench.reference import Reference, RefLine, RefWord, dump_reference, load_reference
from karaoke_bench.sets import load_set
from karaoke_bench.stress import (
    build_stress,
    insert_gap,
    overlay,
    perturb_lyrics,
    word_free_spans,
)

RATE = 1000


def _ref() -> Reference:
    def line(text: str, start: float) -> RefLine:
        words = [
            RefWord(text=w, start=start + i * 0.5, end=start + i * 0.5 + 0.4)
            for i, w in enumerate(text.split())
        ]
        return RefLine(text=text, start=words[0].start, end=words[-1].end, words=words)

    lines = [line("ola mar", 2.0), line("vai o vento", 6.0), line("adeus", 12.0)]
    return Reference(song_id="s", language="gl", duration=20.0, timing="manual", lines=lines)


def _audio(seconds: float = 20.0) -> np.ndarray:
    return np.zeros((round(seconds * RATE), 2), dtype=np.float32)


def test_word_free_spans_keep_only_long_pauses() -> None:
    spans = word_free_spans(_ref(), 3.0)

    flat = [t for span in spans for t in span]
    assert flat == pytest.approx([2.9, 6.0, 7.4, 12.0, 12.4, 20.0])


def test_insert_gap_shifts_later_words() -> None:
    _, ref = insert_gap(_audio(), RATE, _ref(), before_line=1, seconds=5.0, filler=(13.0, 15.0))

    assert [w.start for w in ref.lines[1].words] == [11.0, 11.5, 12.0]
    assert ref.lines[1].start == 11.0
    assert ref.lines[2].words[0].start == 17.0
    assert ref.duration == 25.0


def test_insert_gap_keeps_earlier_words() -> None:
    _, ref = insert_gap(_audio(), RATE, _ref(), before_line=1, seconds=5.0, filler=(13.0, 15.0))

    assert ref.lines[0] == _ref().lines[0]


def test_insert_gap_audio_length_grows_by_gap() -> None:
    audio = _audio()
    audio[13 * RATE : 15 * RATE] = 0.25

    out, _ = insert_gap(audio, RATE, _ref(), before_line=1, seconds=5.0, filler=(13.0, 15.0))

    assert out.shape == (25 * RATE, 2)
    # The gap goes halfway between "mar" (ends 2.9) and "vai" (6.0), and plays the filler.
    assert out[round(6.0 * RATE)][0] == pytest.approx(0.25)


def test_overlay_keeps_length_and_adds_the_source() -> None:
    audio = _audio()
    audio[2 * RATE : 3 * RATE] = 0.5

    out = overlay(audio, RATE, source=(2.0, 3.0), at=10.0, gain_db=-6.0)

    assert out.shape == audio.shape
    assert out[round(10.5 * RATE)][0] == pytest.approx(0.5 * 10 ** (-6 / 20), rel=1e-3)
    assert out[round(2.5 * RATE)][0] == pytest.approx(0.5)


def test_x2_collapses_consecutive_repeats() -> None:
    text = perturb_lyrics(["A b", "A b", "C"], ["x2"], random.Random(1), [])

    assert text.splitlines() == ["A b x2", "C"]


def test_missing_line_removes_text_only() -> None:
    lines = [f"line {i}" for i in range(9)]

    text = perturb_lyrics(lines, ["missing-line"], random.Random(1), [])

    kept = text.splitlines()
    assert len(kept) == 8
    assert set(kept) < set(lines)


def test_extra_lines_come_from_foreign() -> None:
    lines = [f"line {i}" for i in range(9)]

    text = perturb_lyrics(lines, ["extra-lines"], random.Random(1), ["other a", "other b"])

    out = text.splitlines()
    assert len(out) == 11
    assert out.index("other b") == out.index("other a") + 1


def test_headers_and_parens_mark_web_lyrics() -> None:
    lines = [f"line {i}" for i in range(8)]

    text = perturb_lyrics(lines, ["headers", "parens"], random.Random(1), [])

    assert text.splitlines()[0] == "[Verso 1]"
    assert "[Estribillo]" in text
    assert sum("(" in line for line in text.splitlines()) == 3


def test_same_seed_same_lyrics() -> None:
    lines = [f"line {i}" for i in range(9)]

    def make(seed: int) -> str:
        return perturb_lyrics(lines, ["missing-line", "parens"], random.Random(seed), [])

    assert make(3) == make(3)


@pytest.mark.usefixtures("ffmpeg")
def test_build_stress_writes_a_scorable_song(tmp_path: Path) -> None:
    paths = BenchPaths(tmp_path / "bench")
    source = paths.data / "jamendo" / "song"
    source.mkdir(parents=True)
    rate = 44100
    t = np.arange(20 * rate) / rate
    tone = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    from karaoke_bench.audio import write_wav

    write_wav(source / "audio.wav", np.stack([tone, tone]), rate)
    (source / "meta.toml").write_text(
        'title = "Song"\nartist = "Band"\nlanguage = "gl"\nlicense = "BY"\n', encoding="utf-8"
    )
    dump_reference(_ref(), source / "reference.json")
    recipe = tmp_path / "stress.toml"
    recipe.write_text(
        'version = 1\n[[songs]]\nid = "gap-song"\nsource = "song"\ngroup = "gap"\nseed = 1\n',
        encoding="utf-8",
    )

    assert build_stress(paths, recipe) == ["gap-song"]

    [song] = load_set("stress", paths)
    assert song.group == "gap"
    ref = load_reference(song.reference)  # type: ignore[arg-type]
    assert ref.duration == pytest.approx(50.0)
    assert ref.lines[-1].words[0].start == pytest.approx(42.0)
    assert song.lyrics_text() == "ola mar\nvai o vento\nadeus\n"


def test_word_free_spans_include_a_long_intro() -> None:
    ref = _ref()
    ref.lines[0].words = [
        RefWord(text="ola", start=4.0, end=4.4),
        RefWord(text="mar", start=4.5, end=5.0),
    ]

    assert word_free_spans(ref, 3.0)[0] == (0.0, 4.0)
