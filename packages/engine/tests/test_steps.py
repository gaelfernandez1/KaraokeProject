from collections.abc import Sequence
from pathlib import Path

from karaoke_contracts import Line, Word
from karaoke_engine.steps import Aligner, Separator


class FakeAligner:
    name = "fake"

    def align(self, vocals: Path, lyrics_lines: Sequence[str], language: str) -> list[Line]:
        word = Word(text=lyrics_lines[0], start=0.0, end=1.0)
        return [Line(id="l1", start=0.0, end=1.0, words=[word])]


def test_fake_aligner_satisfies_protocol() -> None:
    aligner = FakeAligner()

    assert isinstance(aligner, Aligner)
    assert not isinstance(aligner, Separator)
