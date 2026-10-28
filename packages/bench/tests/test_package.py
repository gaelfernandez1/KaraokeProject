from pathlib import Path

import pytest

from karaoke_bench.package import build_package, display_words, slug
from karaoke_bench.paths import BenchPaths
from karaoke_bench.reference import RefLine, RefWord
from karaoke_bench.sets import load_set
from karaoke_contracts import validate_package
from karaoke_engine.steps import Stems


def test_display_words_keep_jamalt_text_with_manual_times() -> None:
    line = RefLine(
        text="Disparan, la línea",
        start=1.0,
        end=3.0,
        words=[
            RefWord(text="disparan", start=1.0, end=1.6),
            RefWord(text="la", start=1.6, end=1.8),
            RefWord(text="linea", start=1.8, end=3.0),
        ],
    )

    words = display_words(line)

    assert words is not None
    assert [(w.text, w.start, w.end) for w in words] == [
        ("Disparan,", 1.0, 1.6),
        ("la", 1.6, 1.8),
        ("línea", 1.8, 3.0),
    ]


def test_display_words_interpolate_unmatched() -> None:
    line = RefLine(
        text="Ola (eh) (oh) mar",
        start=1.0,
        end=3.0,
        words=[RefWord(text="ola", start=1.0, end=1.5), RefWord(text="mar", start=2.5, end=3.0)],
    )

    words = display_words(line)

    assert words is not None
    assert [(w.text, w.start, w.end) for w in words] == [
        ("Ola", 1.0, 1.5),
        ("(eh)", 1.5, 2.0),
        ("(oh)", 2.0, 2.5),
        ("mar", 2.5, 3.0),
    ]


def test_display_words_none_without_reference_words() -> None:
    assert display_words(RefLine(text="Doo-doo", start=0.0, end=1.0, words=[])) is None


def test_slug() -> None:
    assert slug("10._Disparan_-_criatura") == "10-disparan-criatura"
    assert slug("Mère_nature_-_Law'") == "mere-nature-law"


@pytest.mark.usefixtures("ffmpeg")
def test_build_package_validates(demo_bench: BenchPaths, tmp_path: Path) -> None:
    [song] = load_set("private/demo", demo_bench)
    ref = song.load_reference()
    assert ref is not None
    out = tmp_path / "pkg"

    doc = build_package(
        song, ref, Stems(vocals=song.audio, instrumental=song.audio), out, credits="Demo\n"
    )

    assert validate_package(out) == []
    assert doc.id == "demo"
    assert doc.provenance.lyrics_source == "user"
    assert (out / "LICENSE").read_text(encoding="utf-8") == "Demo\n"
    assert len(doc.lines) == len(ref.lines)
