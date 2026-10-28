"""Fake steps for tests and smoke runs. EvenSplitAligner doubles as the dumbest baseline."""

from collections.abc import Sequence
from pathlib import Path

from karaoke_bench.audio import duration
from karaoke_contracts import Line, Word
from karaoke_engine.steps import Stems, Transcript, TranscriptSegment


class PassthroughSeparator:
    """No separation: the mix plays the vocals and the instrumental."""

    name = "passthrough"
    version = "1"

    def separate(self, audio: Path, work_dir: Path) -> Stems:
        return Stems(vocals=audio, instrumental=audio)


class FixedTranscriber:
    name = "fixed"
    version = "1"

    def __init__(self, text: str, language: str | None = None) -> None:
        self.text = text
        self.language = language

    def transcribe(self, vocals: Path, language: str) -> Transcript:
        segment = TranscriptSegment(0.0, 1.0, self.text)
        return Transcript(language=self.language or language, segments=(segment,))


class EvenSplitAligner:
    """Spreads every word evenly over the whole song."""

    name = "even-split"
    version = "1"

    def align(self, vocals: Path, lyrics_lines: Sequence[str], language: str) -> list[Line]:
        words_per_line = [line.split() for line in lyrics_lines]
        total = sum(len(words) for words in words_per_line)
        step = duration(vocals) / max(total, 1)
        lines, n = [], 0
        for i, texts in enumerate(words_per_line):
            words = [
                Word(text=text, start=(n + k) * step, end=(n + k + 1) * step)
                for k, text in enumerate(texts)
            ]
            n += len(texts)
            lines.append(Line(id=f"l{i + 1}", start=words[0].start, end=words[-1].end, words=words))
        return lines


class FailingAligner(EvenSplitAligner):
    """Fails on songs whose audio file name contains `fail_on`, to test error isolation."""

    name = "failing"

    def __init__(self, fail_on: str) -> None:
        self.fail_on = fail_on

    def align(self, vocals: Path, lyrics_lines: Sequence[str], language: str) -> list[Line]:
        if self.fail_on in vocals.name:
            raise RuntimeError(f"failing on purpose for {vocals.name}")
        return super().align(vocals, lyrics_lines, language)
