"""Reference timings a run is scored against.

The same shape serves the three sources: JamendoLyrics (manual word timings, Jam-ALT line
texts), the Galician set (drafted by an aligner, then validated by ear line by line) and
private songs. Line text and word texts may differ (JamendoLyrics words are plain lowercase),
which is why this does not reuse the contract's Line and Word.
"""

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from karaoke_bench.files import write_text_atomic
from karaoke_contracts import KaraokeDoc

Seconds = Annotated[float, Field(ge=0)]
# draft: not reviewed yet (or changed since); ok: approved by ear; wrong: flagged, waiting for a
# realign; unsure: the reviewer could not tell, so it is left out of the scores.
LineStatus = Literal["draft", "ok", "wrong", "unsure"]
# manual: timed by hand with care (JamendoLyrics); semiautomatic: drafted by an aligner and
# checked by ear line by line; approximate: timed by hand in a subtitle editor, good to a few
# tenths of a second.
Timing = Literal["manual", "semiautomatic", "approximate"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class RefWord(_Model):
    text: Annotated[str, Field(min_length=1)]
    start: Seconds
    end: Seconds


class RefLine(_Model):
    text: Annotated[str, Field(min_length=1)]
    start: Seconds
    end: Seconds
    words: list[RefWord]
    status: LineStatus = "ok"
    anchor: Seconds | None = Field(
        default=None, description="True line start marked by the reviewer while listening."
    )
    note: str | None = None
    revised: bool = Field(default=False, description="Realigned since the last review.")


class Reference(_Model):
    song_id: Annotated[str, Field(min_length=1)]
    language: Annotated[str, Field(pattern=r"^[a-z]{2,3}$")]
    duration: Annotated[float, Field(gt=0)]
    timing: Timing
    approved: bool = False
    lines: list[RefLine]

    def lyrics_text(self) -> str:
        return "\n".join(line.text for line in self.lines)

    def scored_lines(self) -> list[RefLine]:
        return [line for line in self.lines if line.status == "ok"]

    def scored_words(self) -> list[RefWord]:
        return [word for line in self.scored_lines() for word in line.words]

    def scored_share(self) -> float:
        total = sum(len(line.words) for line in self.lines)
        return len(self.scored_words()) / total if total else 0.0


def load_reference(path: Path) -> Reference:
    return Reference.model_validate_json(path.read_bytes())


def dump_reference(ref: Reference, path: Path) -> None:
    text = json.dumps(ref.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
    write_text_atomic(path, text)


def reference_from_doc(doc: KaraokeDoc, timing: Timing) -> Reference:
    """A karaoke.json someone corrected by hand is a valid reference for its song."""
    lines = [
        RefLine(
            text=" ".join(word.text for word in line.words),
            start=line.start,
            end=line.end,
            words=[RefWord(text=w.text, start=w.start, end=w.end) for w in line.words],
        )
        for line in doc.lines
    ]
    return Reference(
        song_id=doc.id,
        language=doc.language,
        duration=doc.duration,
        timing=timing,
        approved=True,
        lines=lines,
    )
