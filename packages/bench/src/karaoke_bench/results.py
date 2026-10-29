"""What a bench run records (results.json) and how songs add up into group summaries."""

from collections.abc import Sequence
from pathlib import Path
from statistics import median
from typing import Any, Literal

from pydantic import BaseModel

from karaoke_bench.metrics import TimingErrors, TimingStats, timing_stats

FOUR_MINUTES = 240.0


class SongStep(BaseModel):
    seconds: float
    cached: bool
    error: str | None = None


class StageRecord(BaseModel):
    load_seconds: float | None
    vram_peak_mb: float | None
    ram_peak_mb: float | None


class SongResult(BaseModel):
    song_id: str
    set_name: str
    language: str
    duration: float
    mode: Literal["lyrics", "asr"]
    group: str | None = None
    steps: dict[str, SongStep]
    wer: float | None = None
    cer: float | None = None
    ref_words: int | None = None
    ref_chars: int | None = None
    timing: TimingStats | None = None
    scored_share: float | None = None
    # None for manual references; for semiautomatic ones, whether they were validated by ear.
    reference_validated: bool | None = None
    reference_timing: str | None = None
    line_start_median: float | None = None
    language_reported: str | None = None
    language_switch: bool | None = None
    error: str | None = None


class GroupSummary(BaseModel):
    songs: int
    failed: int
    wer: float | None
    cer: float | None
    timing: TimingStats | None
    line_start_median: float | None
    language_switches: int
    rtf_median: dict[str, float]
    est_seconds_4min: float | None


class RunResults(BaseModel):
    bench_version: str
    normalization_version: int
    created: str
    git_commit: str | None
    pipeline: dict[str, Any]
    set_name: str
    mode: str
    environment: dict[str, str]
    reference_kind: dict[str, str]
    stages: dict[str, StageRecord]
    songs: list[SongResult]
    summary: dict[str, GroupSummary]
    notes: list[str] = []


def load_results(path: Path) -> RunResults:
    if path.is_dir():
        path = path / "results.json"
    return RunResults.model_validate_json(path.read_bytes())


def summarize(
    songs: Sequence[SongResult],
    timing: dict[str, TimingErrors],
    line_errors: dict[str, list[float]],
    stages: dict[str, StageRecord],
) -> GroupSummary:
    """One group (a language or everything): corpus WER/CER, pooled timing, median speed."""
    scored = [s for s in songs if s.wer is not None and s.ref_words]
    with_chars = [s for s in scored if s.cer is not None and s.ref_chars]
    rtf: dict[str, float] = {}
    for kind in stages:
        ratios = [
            s.steps[kind].seconds / s.duration
            for s in songs
            if kind in s.steps and s.steps[kind].error is None and s.duration > 0
        ]
        if ratios:
            rtf[kind] = median(ratios)
    loads = sum(stage.load_seconds or 0.0 for stage in stages.values())
    lines = [abs(e) for s in songs for e in line_errors.get(s.song_id, [])]
    return GroupSummary(
        songs=len(songs),
        failed=sum(s.error is not None for s in songs),
        wer=_weighted(scored, "wer", "ref_words"),
        cer=_weighted(with_chars, "cer", "ref_chars"),
        timing=timing_stats([timing[s.song_id] for s in songs if s.song_id in timing]),
        line_start_median=median(lines) if lines else None,
        language_switches=sum(s.language_switch is True for s in songs),
        rtf_median=rtf,
        est_seconds_4min=sum(rtf.values()) * FOUR_MINUTES + loads if rtf else None,
    )


def _weighted(songs: Sequence[SongResult], value: str, weight: str) -> float | None:
    total = sum(getattr(s, weight) for s in songs)
    if not total:
        return None
    return float(sum(getattr(s, value) * getattr(s, weight) for s in songs) / total)
