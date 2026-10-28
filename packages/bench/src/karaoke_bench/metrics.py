"""Scores: transcript errors (WER, CER) and word timing errors against a reference.

Timing errors use only the words that pair up with the reference (same folded key, aligned
by Levenshtein), and always report how many reference words that covers. The start metrics
match the AAE and PCO used in the JamendoLyrics papers, so numbers compare with published work.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean, median

import jiwer
from pydantic import BaseModel

from karaoke_bench.reference import RefLine, RefWord
from karaoke_bench.textnorm import match_key, normalize
from karaoke_contracts import Line, Word


class TextErrors(BaseModel):
    wer: float
    cer: float
    ref_words: int
    ref_chars: int


def text_errors(reference: str, hypothesis: str) -> TextErrors:
    ref, hyp = normalize(reference), normalize(hypothesis)
    return TextErrors(
        wer=float(jiwer.wer(ref, hyp)),
        cer=float(jiwer.cer(ref, hyp)),
        ref_words=len(ref.split()),
        ref_chars=len(ref),
    )


@dataclass(frozen=True)
class WordPair:
    ref: RefWord
    hyp_start: float
    hyp_end: float


def pair_words(ref_words: Sequence[RefWord], hyp_words: Sequence[Word]) -> list[WordPair]:
    refs = [(key, word) for word in ref_words if (key := match_key(word.text))]
    hyps = [(key, word) for word in hyp_words if (key := match_key(word.text))]
    if not refs or not hyps:
        return []
    output = jiwer.process_words(" ".join(k for k, _ in refs), " ".join(k for k, _ in hyps))
    pairs = []
    for chunk in output.alignments[0]:
        if chunk.type != "equal":
            continue
        for offset in range(chunk.ref_end_idx - chunk.ref_start_idx):
            ref = refs[chunk.ref_start_idx + offset][1]
            hyp = hyps[chunk.hyp_start_idx + offset][1]
            pairs.append(WordPair(ref=ref, hyp_start=hyp.start, hyp_end=hyp.end))
    return pairs


class TimingErrors(BaseModel):
    """Signed errors (prediction minus reference) of the paired words of one song."""

    start: list[float]
    end: list[float]
    ref_words: int


def timing_errors(pairs: Sequence[WordPair], ref_words: int) -> TimingErrors:
    return TimingErrors(
        start=[p.hyp_start - p.ref.start for p in pairs],
        end=[p.hyp_end - p.ref.end for p in pairs],
        ref_words=ref_words,
    )


class TimingStats(BaseModel):
    words: int
    coverage: float
    start_median: float
    start_mean: float
    start_within: float
    end_median: float
    end_mean: float
    start_bias: float


def timing_stats(errors: Sequence[TimingErrors], tolerance: float = 0.3) -> TimingStats | None:
    """Pools the words of every song given; None when nothing paired."""
    starts = [e for song in errors for e in song.start]
    ends = [e for song in errors for e in song.end]
    if not starts:
        return None
    abs_starts = [abs(e) for e in starts]
    abs_ends = [abs(e) for e in ends]
    ref_words = sum(song.ref_words for song in errors)
    return TimingStats(
        words=len(starts),
        coverage=len(starts) / ref_words if ref_words else 0.0,
        start_median=median(abs_starts),
        start_mean=mean(abs_starts),
        start_within=sum(e <= tolerance for e in abs_starts) / len(starts),
        end_median=median(abs_ends),
        end_mean=mean(abs_ends),
        start_bias=mean(starts),
    )


def line_start_errors(
    ref_lines: Sequence[RefLine], hyp_lines: Sequence[Line]
) -> list[float] | None:
    """Signed line start errors, paired by position; None if the line counts differ."""
    if len(ref_lines) != len(hyp_lines):
        return None
    return [hyp.start - ref.start for ref, hyp in zip(ref_lines, hyp_lines, strict=True)]
