"""JSON in and out of each step, so steps can run in their own process."""

from pathlib import Path
from typing import Any

from karaoke_bench.pipeline import StepKind
from karaoke_contracts import Line
from karaoke_engine.steps import Stems, Transcript, TranscriptSegment


def encode_output(kind: StepKind, value: Any) -> Any:
    if kind == "separator":
        return {"vocals": str(value.vocals), "instrumental": str(value.instrumental)}
    if kind == "transcriber":
        return {
            "language": value.language,
            "segments": [{"start": s.start, "end": s.end, "text": s.text} for s in value.segments],
        }
    if kind == "segmenter":
        return list(value)
    return [line.model_dump(mode="json") for line in value]


def decode_output(kind: StepKind, data: Any) -> Any:
    if kind == "separator":
        return Stems(vocals=Path(data["vocals"]), instrumental=Path(data["instrumental"]))
    if kind == "transcriber":
        segments = tuple(
            TranscriptSegment(s["start"], s["end"], s["text"]) for s in data["segments"]
        )
        return Transcript(language=data["language"], segments=segments)
    if kind == "segmenter":
        return [str(line) for line in data]
    return [Line.model_validate(line) for line in data]


def invoke(kind: StepKind, step: Any, args: dict[str, Any], work_dir: Path) -> Any:
    """Calls the step's method with JSON arguments decoded into the protocol's types."""
    if kind == "separator":
        return step.separate(Path(args["audio"]), work_dir)
    if kind == "transcriber":
        return step.transcribe(Path(args["vocals"]), args["language"])
    if kind == "segmenter":
        return step.segment(decode_output("transcriber", args["transcript"]))
    if "lyrics" in args:
        return step.align_text(Path(args["vocals"]), args["lyrics"], args["language"])
    return step.align(Path(args["vocals"]), list(args["lines"]), args["language"])
