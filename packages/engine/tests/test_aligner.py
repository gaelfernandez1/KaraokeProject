import math
import wave
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pytest

from karaoke_engine.align.aligner import LyricsAligner
from karaoke_engine.align.emissions import Emissions, Vocab, compact
from karaoke_engine.steps import Aligner, TextAligner

RATE = 16000
HOP = 0.02
ALPHABET = "abcdefghijklmnopqrstuvwxyzñ"
pytestmark = pytest.mark.usefixtures("ffmpeg")


class ScriptedModel:
    """Emissions where each listed letter peaks at its frame and the blank wins elsewhere."""

    def __init__(self, peaks: Sequence[tuple[str, int]]) -> None:
        mapping = {"<pad>": 0, "|": 1, **{ch: i + 2 for i, ch in enumerate(ALPHABET)}}
        self.vocab = Vocab.from_mapping(mapping, blank=0, fallbacks={})
        self.peaks = list(peaks)

    def load(self) -> None:
        pass

    def unload(self) -> None:
        pass

    def emissions(self, samples: np.ndarray, ids: Sequence[int]) -> Emissions:
        frames = len(samples) // round(HOP * RATE)
        lp = np.full((frames, len(ALPHABET) + 2), -8.0, dtype=np.float32)
        lp[:, 0] = -0.01
        for ch, frame in self.peaks:
            lp[frame, :] = -8.0
            lp[frame, self.vocab.ids[ch]] = -0.01
        return Emissions(compact(lp, 0, ids), HOP)


def _vocals(tmp_path: Path, voiced: Sequence[tuple[float, float]], seconds: float = 6.0) -> Path:
    samples = np.zeros(round(seconds * RATE), dtype=np.float32)
    t = np.arange(len(samples)) / RATE
    for start, end in voiced:
        inside = (t >= start) & (t < end)
        samples[inside] = 0.5 * np.sin(2 * np.pi * 220 * t[inside])
    path = tmp_path / "vocals.wav"
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((samples * 32767).astype("<i2").tobytes())
    return path


def _spell(text: str, first: int, step: int = 3) -> list[tuple[str, int]]:
    letters = [ch for ch in text if ch.isalpha()]
    return [(ch, first + i * step) for i, ch in enumerate(letters)]


def _aligner(peaks: Sequence[tuple[str, int]], **params: object) -> LyricsAligner:
    return LyricsAligner(emission_model=ScriptedModel(peaks), **params)  # type: ignore[arg-type]


def test_lyrics_aligner_is_both_kinds_of_aligner() -> None:
    aligner = LyricsAligner(emission_model=ScriptedModel([]))

    assert isinstance(aligner, Aligner)
    assert isinstance(aligner, TextAligner)


def test_align_text_returns_words_in_order(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("ola mar", 20) + _spell("vai vento", 150)

    lines = _aligner(peaks).align_text(vocals, "Ola, mar\nVai vento\n", "gl")

    assert [[w.text for w in line.words] for line in lines] == [["Ola,", "mar"], ["Vai", "vento"]]
    assert lines[0].words[0].start == pytest.approx(20 * HOP)
    assert lines[1].words[0].start == pytest.approx(150 * HOP)
    assert lines[1].start == lines[1].words[0].start
    assert all(0.5 < (w.confidence or 0) <= 1 for line in lines for w in line.words)


def test_unsung_line_is_left_out(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("ola mar", 20) + _spell("adeus", 200)

    aligner = _aligner(peaks, edge_skip_penalty=math.inf)
    lines = aligner.align_text(vocals, "ola mar\nnunca se canta isto\nadeus\n", "gl")

    assert [line.words[0].text for line in lines] == ["ola", "adeus"]


def test_backing_line_is_marked(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("ola", 20) + _spell("mar", 80)

    lines = _aligner(peaks).align_text(vocals, "ola (mar)\n", "gl")

    assert [line.role for line in lines] == ["lead", "backing"]


def test_words_without_tokens_get_neighbour_times(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("ola", 20) + _spell("adeus", 60)

    [line] = _aligner(peaks).align_text(vocals, "ola 123 adeus\n", "de")

    ola, number, adeus = line.words
    assert number.start == number.end == ola.end
    assert number.confidence == 0.0
    assert adeus.start == pytest.approx(60 * HOP)


def test_onset_refinement_moves_line_start_to_voice_onset(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(1.0, 3.0)])
    peaks = _spell("ola", 60)

    [refined] = _aligner(peaks, refine_onsets=True).align_text(vocals, "ola\n", "gl")
    [plain] = _aligner(peaks).align_text(vocals, "ola\n", "gl")

    assert refined.start == pytest.approx(1.0, abs=HOP)
    assert plain.start == pytest.approx(1.2, abs=HOP)


def test_word_end_is_trimmed_to_voice(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 2.0)])
    peaks = [*_spell("ol", 20), *(("a", f) for f in range(40, 131))]

    [line] = _aligner(peaks, silence_penalty=0.0).align_text(vocals, "ola\n", "gl")

    assert line.words[0].end <= 2.1 + HOP


def test_align_matches_align_text_for_plain_lines(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("ola mar", 20) + _spell("vai vento", 150)
    aligner = _aligner(peaks)

    assert aligner.align(vocals, ["ola mar", "vai vento"], "gl") == aligner.align_text(
        vocals, "ola mar\nvai vento", "gl"
    )


def test_onset_refinement_applies_after_a_pause_inside_a_line(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.4, 1.0), (2.4, 3.0)])
    peaks = _spell("ola", 20) + _spell("mar", 130)

    [line] = _aligner(peaks, refine_onsets=True).align_text(vocals, "ola mar\n", "gl")

    assert line.words[1].start == pytest.approx(2.4, abs=HOP)


def test_word_end_stops_at_the_first_long_silence(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 1.0), (3.0, 4.0)])
    peaks = [*_spell("ol", 20), *(("a", f) for f in range(40, 176))]

    [line] = _aligner(peaks, silence_penalty=0.0).align_text(vocals, "ola\n", "gl")

    assert line.words[0].end <= 1.1 + HOP


def test_lyrics_longer_than_the_song_keep_the_lines_that_are_sung(tmp_path: Path) -> None:
    # A clip of a song with the whole song's lyrics: the first lines are sung, the rest is not,
    # and many short lines must not be crammed in instead.
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("primeira longa", 20) + _spell("segunda longa", 120)
    lyrics = "primeira longa\nsegunda longa\n" + "pa pan\n" * 20

    lines = _aligner(peaks).align_text(vocals, lyrics, "gl")

    assert [" ".join(w.text for w in line.words) for line in lines][:2] == [
        "primeira longa",
        "segunda longa",
    ]


def test_parts_follow_letter_times(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = [("c", 20), ("a", 24), ("m", 40), ("i", 44), ("ñ", 60), ("a", 64), ("n", 66),
             ("d", 80), ("o", 84)]  # fmt: skip

    [line] = _aligner(peaks).align_text(vocals, "camiñando\n", "gl")

    parts = line.words[0].parts
    assert [p.text for p in parts] == ["ca", "mi", "ñan", "do"]
    assert [p.start for p in parts] == pytest.approx([20 * HOP, 40 * HOP, 60 * HOP, 80 * HOP])
    assert parts[-1].end == line.words[0].end


def test_parts_skip_words_whose_letters_do_not_map(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("dous mil vinte", 20)

    [line] = _aligner(peaks).align_text(vocals, "2020\n", "gl")

    assert line.words[0].parts == []


def test_model_for_language_names_the_pinned_model() -> None:
    aligner = LyricsAligner()

    assert aligner.model_for_language("gl").startswith(
        "proxectonos/Nos_ASR-wav2vec2-xls-r-300m-gl@"
    )
    assert aligner.model_for_language("eu").startswith("aadel4/omniASR-CTC-300M-v2@")


def test_header_singer_reaches_the_line(tmp_path: Path) -> None:
    from karaoke_engine.align.lyrics import singer_id

    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("ola", 20) + _spell("mar", 120)

    lines = _aligner(peaks).align_text(
        vocals, "[Verso: Ana]\nola\n[Estribillo: Brais]\nmar\n", "gl"
    )

    assert [line.singer for line in lines] == [singer_id("Ana"), singer_id("Brais")]
