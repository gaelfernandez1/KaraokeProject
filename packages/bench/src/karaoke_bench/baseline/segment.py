"""The simplest segmenter: one lyric line per transcript segment."""

from karaoke_engine.steps import Transcript


class SegmentPerLine:
    name = "segment-per-line"
    version = "1"

    def segment(self, transcript: Transcript) -> list[str]:
        lines = (" ".join(segment.text.split()) for segment in transcript.segments)
        return [line for line in lines if line]
