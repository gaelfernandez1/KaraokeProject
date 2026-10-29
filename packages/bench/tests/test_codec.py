import json
from pathlib import Path

from karaoke_bench.baseline.segment import SegmentPerLine
from karaoke_bench.codec import decode_output, encode_output, invoke
from karaoke_contracts import Line, Word
from karaoke_engine.steps import Stems, Transcript, TranscriptSegment


def _through_json(kind: str, value: object) -> object:
    return decode_output(kind, json.loads(json.dumps(encode_output(kind, value))))  # type: ignore[arg-type]


def test_codec_roundtrip_lines() -> None:
    lines = [Line(id="l1", start=1.0, end=2.0, words=[Word(text="Ribeira,", start=1.0, end=2.0)])]

    assert _through_json("aligner", lines) == lines


def test_codec_roundtrip_stems_transcript_and_text() -> None:
    stems = Stems(vocals=Path("/a/v.wav"), instrumental=Path("/a/i.wav"))
    transcript = Transcript(language="gl", segments=(TranscriptSegment(0.0, 1.5, "Ola, mar"),))

    assert _through_json("separator", stems) == stems
    assert _through_json("transcriber", transcript) == transcript
    assert _through_json("segmenter", ["ola", "mar"]) == ["ola", "mar"]


def test_invoke_segmenter_decodes_its_transcript(tmp_path: Path) -> None:
    transcript = Transcript(language="gl", segments=(TranscriptSegment(0.0, 1.0, " ola "),))

    result = invoke(
        "segmenter",
        SegmentPerLine(),
        {"transcript": encode_output("transcriber", transcript)},
        tmp_path,
    )

    assert result == ["ola"]
