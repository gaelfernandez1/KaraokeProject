"""The lyrics aligner: pasted lyrics and separated vocals in, timed lines and words out.

It reads the lyrics the way a lyrics site writes them (parse_lyrics), turns each word into the
letters a singer says (spoken), and lets the CTC path rest between lines, skip lines nobody
sings and keep letters out of the instrumental breaks (align_segments). After the path, line
starts move back to where the voice really starts (CTC tends to place the first letter late)
and word ends are kept out of silence.
"""

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import numpy.typing as npt

from karaoke_contracts import Line, Part, Word
from karaoke_engine.align.activity import vocal_activity
from karaoke_engine.align.audio import SAMPLE_RATE, load_mono16k
from karaoke_engine.align.ctc import Segment, align_segments
from karaoke_engine.align.emissions import EmissionModel, Emissions, Vocab
from karaoke_engine.align.lyrics import LyricLine, parse_lyrics, singer_id
from karaoke_engine.align.models import DEFAULT_BY_LANGUAGE, FALLBACK_MODEL, MODELS
from karaoke_engine.align.spoken import spoken
from karaoke_engine.align.syllables import syllables

_HOP = 0.02
# A line start moves back to the voice onset only if the voice was silent this long before it,
# and the onset is at most this far back.
_ONSET_SILENCE = 0.2
_ONSET_REACH = 0.5
_END_SLACK = 0.1
_END_GAP = 0.3
# A backing part may start this long before the lead line it answers.
_BACKING_MARGIN = 0.5


class _Model(Protocol):
    @property
    def vocab(self) -> Vocab: ...

    def load(self) -> None: ...

    def emissions(self, samples: npt.NDArray[np.float32], ids: Sequence[int]) -> Emissions: ...

    def unload(self) -> None: ...


@dataclass(frozen=True)
class _Tokens:
    ids: tuple[int, ...]  # vocabulary ids, with delimiters between words
    owner: tuple[int, ...]  # word index per token, -1 for delimiters


class LyricsAligner:
    name = "lyrics-ctc"
    # Bumped when a default changes too: defaults are not part of the bench cache key.
    version = "10"

    # Defaults measured on the quick, stress, private and jamendo sets (decision 005). Skip costs
    # are per letter: a flat cost per line rewarded cramming many short lines into the audio.
    # Cheap skips at the edges help clips but can drop a whole sung verse, so they are off.
    # Moving line starts to the voice onset made JamendoLyrics worse (its starts follow the
    # vowel).
    def __init__(
        self,
        model: str | None = None,
        filler_penalty: float = 3.0,
        skip_penalty: float = 6.0,
        backing_skip_penalty: float = 4.0,
        overlap_absent_penalty: float = 6.0,
        backing_min_confidence: float = 0.05,
        edge_skip_penalty: float = math.inf,
        silence_penalty: float = 4.0,
        refine_onsets: bool = False,
        parts: bool = True,
        char_map: dict[str, str] | None = None,
        device: str = "cuda",
        dtype: str = "float16",
        emission_model: Any = None,
    ) -> None:
        self.model = model
        self.filler_penalty = filler_penalty
        self.skip_penalty = skip_penalty
        self.backing_skip_penalty = backing_skip_penalty
        self.overlap_absent_penalty = overlap_absent_penalty
        self.backing_min_confidence = backing_min_confidence
        self.edge_skip_penalty = edge_skip_penalty
        self.silence_penalty = silence_penalty
        self.refine_onsets = refine_onsets
        self.parts = parts
        self.char_map = char_map or {}
        self.device = device
        self.dtype = dtype
        self._injected: _Model | None = emission_model
        self._loaded: tuple[str, _Model] | None = None

    def load(self) -> None:
        """Loads the chosen model ahead of time; without one, it waits to know the language."""
        if self._injected is None and self.model is not None:
            self._model_for("")

    def align(self, vocals: Path, lyrics_lines: Sequence[str], language: str) -> list[Line]:
        return self.align_text(vocals, "\n".join(lyrics_lines), language)

    def align_text(self, vocals: Path, lyrics: str, language: str) -> list[Line]:
        lines = parse_lyrics(lyrics)
        model = self._model_for(language)
        vocab = model.vocab
        tokens = [self._tokens(line, vocab, language) for line in lines]
        used = sorted({token for line in tokens for token in line.ids})
        column = {token: i + 2 for i, token in enumerate(used)}

        samples = load_mono16k(vocals)
        emissions = model.emissions(samples, used)
        active = vocal_activity(samples, SAMPLE_RATE, _HOP)
        frame_active = _resample(active, emissions.log_probs.shape[0], emissions.frame_seconds)
        penalty = np.where(frame_active, 0.0, self.silence_penalty).astype(np.float32)

        # One path through every line, backing parts in their written place (mostly echoes and
        # answers right after the lead). A backing part that does not fit there may be sung over
        # the lead: it then gets a second chance alone in the stretch around its lead line.
        order = [i for i in range(len(lines)) if tokens[i].ids]
        segments = {i: self._segment(lines[i], tokens[i], column) for i in order}
        paths = align_segments(
            emissions.log_probs, [segments[i] for i in order], self.filler_penalty, penalty
        )
        placed = {i: p.spans for i, p in zip(order, paths, strict=True) if p.spans is not None}
        first_pass = set(placed)
        leads = [i for i in order if not lines[i].backing]
        for i in (i for i in order if lines[i].backing and i not in placed):
            first, last = _backing_window(i, leads, placed, len(emissions.log_probs),
                                          emissions.frame_seconds)  # fmt: skip
            cost = self.overlap_absent_penalty * len(tokens[i].ids)
            alone = Segment(segments[i].tokens, segments[i].owner, cost, cost)
            [path] = align_segments(
                emissions.log_probs[first:last], [alone], self.filler_penalty, penalty[first:last]
            )
            if path.spans is not None:
                placed[i] = [(a + first, b + first) for a, b in path.spans]

        out: list[Line] = []
        for i, spans in placed.items():
            words = self._words(lines[i], tokens[i], spans, emissions, column, active, language)
            overlapped = lines[i].backing and i not in first_pass
            if overlapped and _mean_confidence(words) < self.backing_min_confidence:
                continue  # placed over the lead voice by chance, not sung
            singer = lines[i].singer
            out.append(
                Line(
                    id="l",
                    start=words[0].start,
                    end=max(word.end for word in words),
                    singer=singer_id(singer) if singer else None,
                    role="backing" if lines[i].backing else "lead",
                    words=words,
                )
            )
        out.sort(key=lambda line: line.start)
        return [line.model_copy(update={"id": f"l{k + 1}"}) for k, line in enumerate(out)]

    def _segment(self, line: LyricLine, tokens: _Tokens, column: dict[int, int]) -> Segment:
        count = len(tokens.ids)
        rate = self.backing_skip_penalty if line.backing else self.skip_penalty
        return Segment(
            tokens=tuple(column[t] for t in tokens.ids),
            owner=tokens.owner,
            skip_penalty=rate * count,
            edge_skip_penalty=min(rate, self.edge_skip_penalty) * count,
        )

    def _tokens(self, line: LyricLine, vocab: Vocab, language: str) -> _Tokens:
        ids: list[int] = []
        owner: list[int] = []
        for index, word in enumerate(line.words):
            said = "".join(self.char_map.get(ch, ch) for ch in spoken(word, language))
            for piece in said.split():
                encoded = vocab.encode(piece)
                if not encoded:
                    continue
                if ids and vocab.delimiter is not None:
                    ids.append(vocab.delimiter)
                    owner.append(-1)
                ids += encoded
                owner += [index] * len(encoded)
        return _Tokens(tuple(ids), tuple(owner))

    def _words(
        self,
        line: LyricLine,
        tokens: _Tokens,
        spans: Sequence[tuple[int, int]],
        emissions: Emissions,
        column: dict[int, int],
        active: npt.NDArray[np.bool_],
        language: str,
    ) -> list[Word]:
        seconds = emissions.frame_seconds
        lp = emissions.log_probs
        found: list[tuple[float, float, float] | None] = [None] * len(line.words)
        letter_starts: list[list[float]] = [[] for _ in line.words]
        for word in range(len(line.words)):
            mine = [k for k, owner in enumerate(tokens.owner) if owner == word]
            if not mine:
                continue
            letter_starts[word] = [spans[k][0] * seconds for k in mine]
            first, last = spans[mine[0]][0], spans[mine[-1]][1]
            total = sum(
                float(lp[spans[k][0] : spans[k][1] + 1, column[tokens.ids[k]]].sum()) for k in mine
            )
            count = sum(spans[k][1] - spans[k][0] + 1 for k in mine)
            found[word] = (first * seconds, (last + 1) * seconds, math.exp(total / count))
        times = _fill_gaps(found)
        words: list[Word] = []
        for text, (start, end, confidence) in zip(line.words, times, strict=True):
            end = _trim_end(start, end, active)
            if self.refine_onsets and confidence > 0:
                previous_end = words[-1].end if words else 0.0
                start = max(_voice_onset(start, active), min(start, previous_end))
            end = max(end, start)
            parts = self._parts(text, letter_starts[len(words)], start, end, language)
            words.append(
                Word(text=text, start=round(start, 3), end=round(end, 3),
                     confidence=round(confidence, 3), parts=parts)
            )  # fmt: skip
        return words

    def _parts(
        self, text: str, letter_starts: Sequence[float], start: float, end: float, language: str
    ) -> list[Part]:
        """Syllables timed by their first letter, when each letter has its own token."""
        if not self.parts:
            return []
        pieces = syllables(text, language)
        if pieces is None or len(letter_starts) != sum(ch.isalpha() for ch in text):
            return []
        bounds = [start]
        letters = 0
        for piece in pieces[:-1]:
            letters += sum(ch.isalpha() for ch in piece)
            bounds.append(min(max(letter_starts[letters], bounds[-1]), end))
        bounds.append(end)
        return [
            Part(text=piece, start=round(a, 3), end=round(b, 3))
            for piece, (a, b) in zip(pieces, itertools.pairwise(bounds), strict=True)
        ]

    def model_for_language(self, language: str) -> str:
        """The model this aligner uses for a language, as repo@revision (for provenance)."""
        spec = MODELS[self.model or DEFAULT_BY_LANGUAGE.get(language, FALLBACK_MODEL)]
        return f"{spec.repo}@{spec.revision[:12]}"

    def unload(self) -> None:
        """Frees the loaded model, so the next step has the GPU and the memory."""
        if self._loaded is not None:
            self._loaded[1].unload()
            self._loaded = None

    def _model_for(self, language: str) -> _Model:
        if self._injected is not None:
            return self._injected
        name = self.model or DEFAULT_BY_LANGUAGE.get(language, FALLBACK_MODEL)
        if self._loaded is not None and self._loaded[0] == name:
            return self._loaded[1]
        if self._loaded is not None:
            self._loaded[1].unload()
        model = EmissionModel(MODELS[name], device=self.device, dtype=self.dtype)
        model.load()
        self._loaded = (name, model)
        return model


def _mean_confidence(words: Sequence[Word]) -> float:
    rated = [w.confidence for w in words if w.confidence]
    return math.exp(sum(math.log(c) for c in rated) / len(rated)) if rated else 0.0


def _backing_window(
    index: int,
    leads: Sequence[int],
    placed: dict[int, list[tuple[int, int]]],
    frames: int,
    frame_seconds: float,
) -> tuple[int, int]:
    """Frames from just before the lead line before a backing part to the second one after it."""
    before = [i for i in leads if i < index and i in placed]
    after = [i for i in leads if i > index and i in placed]
    margin = round(_BACKING_MARGIN / frame_seconds)
    first = max(placed[before[-1]][0][0] - margin, 0) if before else 0
    last = placed[after[1]][0][0] if len(after) > 1 else frames
    return first, max(last, first)


def _fill_gaps(
    found: Sequence[tuple[float, float, float] | None],
) -> list[tuple[float, float, float]]:
    """Words the model could not spell sit at their neighbour's edge, with confidence 0."""
    out: list[tuple[float, float, float]] = []
    for i, item in enumerate(found):
        if item is not None:
            out.append(item)
            continue
        later = (f[0] for f in found[i + 1 :] if f is not None)
        point = out[-1][1] if out else next(later, 0.0)
        out.append((point, point, 0.0))
    return out


def _resample(active: npt.NDArray[np.bool_], frames: int, seconds: float) -> npt.NDArray[np.bool_]:
    """Activity at the model's frame rate (nearest activity frame for each model frame)."""
    if not len(active):
        return np.zeros(frames, dtype=bool)
    index = np.minimum((np.arange(frames) * seconds / _HOP).astype(int), len(active) - 1)
    resampled: npt.NDArray[np.bool_] = active[index]
    return resampled


def _voice_onset(start: float, active: npt.NDArray[np.bool_]) -> float:
    """Where the voice run holding `start` begins, if it follows a silence and is close."""
    index = min(round(start / _HOP), len(active) - 1)
    if index < 0 or not active[index]:
        return start
    onset = index
    while onset > 0 and active[onset - 1]:
        onset -= 1
    silence = round(_ONSET_SILENCE / _HOP)
    if onset < silence or active[onset - silence : onset].any():
        return start
    return onset * _HOP if start - onset * _HOP <= _ONSET_REACH else start


def _trim_end(start: float, end: float, active: npt.NDArray[np.bool_]) -> float:
    """Ends a word where its voice stops: at the first pause longer than _END_GAP after it starts.

    The release after the voice stops keeps a little of the fade.
    """
    first = min(round(start / _HOP), len(active))
    last = min(round(end / _HOP), len(active))
    gap = round(_END_GAP / _HOP)
    voiced_end = None
    silent = 0
    for frame in range(first, last):
        if active[frame]:
            voiced_end = frame + 1
            silent = 0
            continue
        silent += 1
        if voiced_end is not None and silent > gap:
            break
    if voiced_end is None:
        return end
    return min(end, voiced_end * _HOP + _END_SLACK)
