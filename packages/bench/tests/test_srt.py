from collections.abc import Callable
from pathlib import Path

import pytest

from karaoke_bench.cli import main
from karaoke_bench.reference import load_reference
from karaoke_bench.srt import SrtEntry, parse_srt, reference_from_srt

SRT = """1
00:00:00,010 --> 00:00:09,000

2
00:00:12,000 --> 00:00:12,500
Vou cantar

3
00:00:00:20,250 --> 00:00:21,700
mañá,
"""


def _reference(entries: list[SrtEntry], lyrics: list[str]):  # type: ignore[no-untyped-def]
    return reference_from_srt(entries, lyrics, "song", "gl", 200.0)


def test_parse_srt_skips_empty_entries() -> None:
    assert [entry.text for entry in parse_srt(SRT)] == ["Vou cantar", "mañá,"]


def test_parse_srt_tolerates_an_extra_hour_field() -> None:
    entry = parse_srt(SRT)[1]

    assert entry.start == pytest.approx(20.25)
    assert entry.end == pytest.approx(21.7)


def test_parse_srt_reads_windows_line_endings() -> None:
    assert len(parse_srt(SRT.replace("\n", "\r\n"))) == 2


def test_multiword_entry_is_split_evenly() -> None:
    ref = _reference([SrtEntry(12.0, 12.5, "Vou cantar")], ["Vou cantar"])

    words = ref.lines[0].words
    assert [(w.start, w.end) for w in words] == [(12.0, 12.25), (12.25, 12.5)]


def test_fragments_merge_into_the_lyrics_word() -> None:
    entries = [
        SrtEntry(4.0, 4.2, "cami"),
        SrtEntry(4.3, 4.5, "ña"),
        SrtEntry(4.5, 5.1, "ndo"),
    ]

    ref = _reference(entries, ["camiñando"])

    word = ref.lines[0].words[0]
    assert (word.text, word.start, word.end) == ("camiñando", 4.0, 5.1)


def test_lines_follow_the_lyrics() -> None:
    entries = [
        SrtEntry(float(i), i + 0.5, text) for i, text in enumerate(["a", "b", "c", "d", "e"])
    ]

    ref = _reference(entries, ["A b", "c, d", "e"])

    assert [line.text for line in ref.lines] == ["A b", "c, d", "e"]
    assert [[w.text for w in line.words] for line in ref.lines] == [["A", "b"], ["c,", "d"], ["e"]]
    assert ref.lines[1].start == 2.0
    assert ref.lines[1].end == 3.5


def test_reference_is_approximate_and_approved() -> None:
    ref = _reference([SrtEntry(1.0, 2.0, "ola")], ["ola"])

    assert ref.timing == "approximate"
    assert ref.approved
    assert ref.lines[0].status == "ok"


def test_mismatch_names_the_word() -> None:
    with pytest.raises(ValueError, match="adios"):
        _reference([SrtEntry(1.0, 2.0, "adios")], ["hola"])


def test_leftover_entries_are_an_error() -> None:
    with pytest.raises(ValueError, match="after the lyrics"):
        _reference([SrtEntry(1.0, 2.0, "ola"), SrtEntry(2.0, 3.0, "mar")], ["ola"])


@pytest.mark.usefixtures("ffmpeg")
def test_import_srt_writes_the_private_reference(
    tmp_path: Path, make_tone: Callable[..., Path]
) -> None:
    song = tmp_path / "data" / "private" / "song"
    make_tone("data/private/song/audio.wav", 3.0)
    (song / "meta.toml").write_text('title = "Song"\nlanguage = "gl"\n', encoding="utf-8")
    (song / "lyrics.txt").write_text("Vou cantar\nmañá,\n", encoding="utf-8")
    srt = tmp_path / "song.srt"
    srt.write_text(SRT, encoding="utf-8")

    code = main(["--bench-dir", str(tmp_path), "import-srt", "private/song", str(srt)])

    assert code == 0
    ref = load_reference(song / "reference.json")
    assert [line.text for line in ref.lines] == ["Vou cantar", "mañá,"]
    assert ref.duration == pytest.approx(3.0, abs=0.01)


def test_import_srt_refuses_public_sets(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    srt = tmp_path / "song.srt"
    srt.write_text(SRT, encoding="utf-8")

    code = main(["--bench-dir", str(tmp_path), "import-srt", "gl/song", str(srt)])

    assert code == 1
    assert "private" in capsys.readouterr().err
