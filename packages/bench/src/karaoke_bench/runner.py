"""Runs a pipeline over a song set and writes a comparable report.

Steps run one after another for all songs (each in its own process, see stage.py). In lyrics
mode the aligner gets the lyrics a user would paste; in asr mode it gets the transcriber's lines
and the language the transcriber reported, which is how the v2 system behaved.
"""

import hashlib
import json
import platform
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from importlib import metadata
from pathlib import Path
from statistics import median
from typing import Any

from karaoke_bench import __version__
from karaoke_bench.audio import duration, file_sha256
from karaoke_bench.cache import cache_key
from karaoke_bench.codec import encode_output
from karaoke_bench.files import write_text_atomic
from karaoke_bench.metrics import (
    TimingErrors,
    line_start_errors,
    pair_words,
    text_errors,
    timing_errors,
    timing_stats,
)
from karaoke_bench.paths import BenchPaths
from karaoke_bench.pipeline import Mode, Pipeline, StepKind, step_version
from karaoke_bench.reference import Reference
from karaoke_bench.report import render_report
from karaoke_bench.results import RunResults, SongResult, SongStep, StageRecord, summarize
from karaoke_bench.sets import SetError, Song, load_set
from karaoke_bench.stage import ItemOutcome, StageItem, StageOutcome, run_stage
from karaoke_bench.textnorm import NORMALIZATION_VERSION, lyrics_lines
from karaoke_contracts import Line
from karaoke_engine.steps import Stems, Transcript

# Aligners may overshoot the end of the audio slightly; more than this is a bug.
_END_SLACK = 0.5
_PACKAGES = ("torch", "transformers", "faster-whisper", "ctranslate2", "demucs", "numpy", "jiwer")


@dataclass(frozen=True)
class RunOptions:
    pipeline: Pipeline
    set_name: str
    mode: Mode
    songs: Sequence[str] | None = None
    use_cache: bool = True


@dataclass
class _SongState:
    song: Song
    reference: Reference | None
    duration: float
    steps: dict[str, SongStep]
    lines_in: list[str] | None = None
    vocals: Path | None = None
    vocals_fp: str = ""
    transcript: Transcript | None = None
    aligned: list[Line] | None = None
    error: str | None = None


def run(options: RunOptions, paths: BenchPaths) -> Path:
    """Runs the pipeline and returns the results folder (report.md and results.json)."""
    options.pipeline.check(options.mode)
    songs = load_set(options.set_name, paths)
    if options.songs is not None:
        known = {song.song_id for song in songs}
        unknown = [song_id for song_id in options.songs if song_id not in known]
        if unknown:
            raise SetError(f"not in set '{options.set_name}': {', '.join(unknown)}")
        songs = [song for song in songs if song.song_id in set(options.songs)]

    notes: list[str] = []
    states = []
    for song in songs:
        reference = song.load_reference()
        lyrics = song.lyrics_text()
        if options.mode == "lyrics" and not lyrics:
            notes.append(f"{song.song_id}: sin letra, se salta en modo lyrics")
            continue
        states.append(
            _SongState(
                song=song,
                reference=reference,
                duration=reference.duration if reference else duration(song.audio),
                steps={},
                lines_in=lyrics_lines(lyrics) if lyrics else None,
            )
        )

    stages = _run_steps(states, options, paths)
    timing: dict[str, TimingErrors] = {}
    line_errors: dict[str, list[float]] = {}
    results = [_score(state, options.mode, timing, line_errors) for state in states]
    stage_records = {
        kind: StageRecord(
            load_seconds=outcome.load_seconds,
            vram_peak_mb=outcome.vram_peak_mb,
            ram_peak_mb=outcome.ram_peak_mb,
        )
        for kind, outcome in stages.items()
    }
    groups = {"all": results}
    for language in sorted({r.language for r in results}):
        groups[language] = [r for r in results if r.language == language]
    summary = {
        name: summarize(group, timing, line_errors, stage_records) for name, group in groups.items()
    }
    run_results = RunResults(
        bench_version=__version__,
        normalization_version=NORMALIZATION_VERSION,
        created=datetime.now().astimezone().isoformat(timespec="seconds"),
        git_commit=_git_commit(),
        pipeline=_describe(options.pipeline),
        set_name=options.set_name,
        mode=options.mode,
        environment=_environment(),
        reference_kind=_reference_kind(states),
        stages=stage_records,
        songs=results,
        summary=summary,
        notes=notes,
    )
    return _write(run_results, states, timing, paths)


def run_lyrics_stages(
    songs: Sequence[Song],
    pipeline: Pipeline,
    paths: BenchPaths,
    use_cache: bool = True,
    lines: dict[str, list[str]] | None = None,
) -> tuple[dict[str, Stems], dict[str, ItemOutcome], dict[str, StageOutcome]]:
    """Separator (if any) and aligner with the songs' lyrics; for drafts and packages."""
    states = []
    for song in songs:
        given = lines[song.song_id] if lines else lyrics_lines(song.lyrics_text() or "")
        states.append(_SongState(song, None, 0.0, {}, lines_in=given))
    options = RunOptions(pipeline, "", "lyrics", use_cache=use_cache)
    stages = _run_steps(states, options, paths)
    stems = {
        s.song.song_id: Stems(vocals=s.vocals, instrumental=_instrumental(s, stages))
        for s in states
        if s.vocals is not None
    }
    aligned = stages["aligner"].items if "aligner" in stages else {}
    return stems, aligned, stages


def _run_steps(
    states: list[_SongState], options: RunOptions, paths: BenchPaths
) -> dict[str, StageOutcome]:
    pipeline, cache = options.pipeline, options.use_cache
    stages: dict[str, StageOutcome] = {}
    args: dict[str, dict[str, Any]]
    for state in states:
        state.vocals = state.song.audio
        state.vocals_fp = file_sha256(state.song.audio)

    if "separator" in pipeline.steps:
        spec = pipeline.steps["separator"]
        version = step_version(spec)
        items = [
            StageItem(s.song.song_id, {"audio": str(s.song.audio)}, s.vocals_fp) for s in states
        ]
        outcome = stages["separator"] = run_stage(spec, items, paths, cache)
        for state in states:
            result = _take(state, "separator", outcome)
            if result is not None:
                state.vocals = result.vocals
                state.vocals_fp = cache_key(spec, version, state.vocals_fp) + ":vocals"

    if options.mode == "asr":
        live = [s for s in states if s.error is None]
        args = {
            s.song.song_id: {"vocals": str(s.vocals), "language": s.song.language} for s in live
        }
        outcome = stages["transcriber"] = _stage(pipeline, "transcriber", live, args, paths, cache)
        for state in live:
            state.transcript = _take(state, "transcriber", outcome)
        live = [s for s in live if s.error is None]
        args = {
            s.song.song_id: {"transcript": encode_output("transcriber", s.transcript)} for s in live
        }
        outcome = stages["segmenter"] = _stage(pipeline, "segmenter", live, args, paths, cache)
        for state in live:
            state.lines_in = _take(state, "segmenter", outcome)

    live = [s for s in states if s.error is None and s.lines_in]
    args = {
        s.song.song_id: {
            "vocals": str(s.vocals),
            "lines": s.lines_in,
            "language": s.transcript.language if s.transcript else s.song.language,
        }
        for s in live
    }
    outcome = stages["aligner"] = _stage(pipeline, "aligner", live, args, paths, cache)
    for state in live:
        state.aligned = _take(state, "aligner", outcome)
    return stages


def _stage(
    pipeline: Pipeline,
    kind: StepKind,
    states: list[_SongState],
    args: dict[str, dict[str, Any]],
    paths: BenchPaths,
    use_cache: bool,
) -> StageOutcome:
    items = [
        StageItem(s.song.song_id, args[s.song.song_id], _fingerprint(args[s.song.song_id], s))
        for s in states
    ]
    return run_stage(pipeline.steps[kind], items, paths, use_cache)


def _fingerprint(args: dict[str, Any], state: _SongState) -> str:
    """Hash of the inputs, with the vocals file standing for its content, not its path."""
    content = {**args, "vocals": state.vocals_fp} if "vocals" in args else args
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def _take(state: _SongState, kind: str, outcome: StageOutcome) -> Any:
    item = outcome.items[state.song.song_id]
    state.steps[kind] = SongStep(seconds=item.seconds, cached=item.cached, error=item.error)
    if item.error:
        state.error = f"{kind}: {item.error}"
    return item.output


def _instrumental(state: _SongState, stages: dict[str, StageOutcome]) -> Path:
    if "separator" in stages:
        output = stages["separator"].items[state.song.song_id].output
        if output is not None:
            return Path(output.instrumental)
    return state.song.audio


def _score(
    state: _SongState,
    mode: Mode,
    timing: dict[str, TimingErrors],
    line_errors: dict[str, list[float]],
) -> SongResult:
    song, ref = state.song, state.reference
    result = SongResult(
        song_id=song.song_id,
        set_name=song.set_name,
        language=song.language,
        duration=state.duration,
        mode=mode,
        steps=state.steps,
        scored_share=ref.scored_share() if ref else None,
        error=state.error,
    )
    if state.transcript is not None:
        result.language_reported = state.transcript.language
        result.language_switch = state.transcript.language != song.language
        lyrics = song.lyrics_text()
        if lyrics:
            hypothesis = " ".join(segment.text for segment in state.transcript.segments)
            errors = text_errors(lyrics, hypothesis)
            result.wer, result.cer = errors.wer, errors.cer
            result.ref_words, result.ref_chars = errors.ref_words, errors.ref_chars
    if state.error or state.aligned is None:
        return result
    problem = _check_aligned(state)
    if problem:
        result.error = f"aligner: {problem}"
        return result
    if ref is not None:
        words = [word for line in state.aligned for word in line.words]
        scored = ref.scored_words()
        timing[song.song_id] = timing_errors(pair_words(scored, words), len(scored))
        result.timing = timing_stats([timing[song.song_id]])
        if mode == "lyrics":
            starts = line_start_errors(ref.lines, state.aligned)
            if starts is not None:
                ok = [e for e, line in zip(starts, ref.lines, strict=True) if line.status == "ok"]
                line_errors[song.song_id] = ok
                result.line_start_median = median(abs(e) for e in ok) if ok else None
    return result


def _check_aligned(state: _SongState) -> str | None:
    aligned = state.aligned or []
    if state.lines_in is not None and len(aligned) != len(state.lines_in):
        return f"returned {len(aligned)} lines for {len(state.lines_in)} lyric lines"
    for line in aligned:
        for word in line.words:
            if word.end < word.start or word.end > state.duration + _END_SLACK:
                return f"word '{word.text}' has times outside the song ({word.start}-{word.end})"
    return None


def _write(
    results: RunResults,
    states: list[_SongState],
    timing: dict[str, TimingErrors],
    paths: BenchPaths,
) -> Path:
    base = (
        f"{date.today().isoformat()}-{results.pipeline['name']}-"
        f"{results.set_name.replace('/', '_')}-{results.mode}"
    )
    name, n = base, 1
    while (paths.results / name).exists():
        n += 1
        name = f"{base}-{n}"
    out = paths.results / name
    out.mkdir(parents=True)
    write_text_atomic(out / "results.json", results.model_dump_json(indent=2) + "\n")
    write_text_atomic(out / "report.md", render_report(results))
    for state in states:
        raw = {
            "lines_in": state.lines_in,
            "transcript": encode_output("transcriber", state.transcript)
            if state.transcript
            else None,
            "aligned": encode_output("aligner", state.aligned) if state.aligned else None,
            "timing_errors": timing[state.song.song_id].model_dump()
            if state.song.song_id in timing
            else None,
        }
        write_text_atomic(
            paths.runs / name / f"{state.song.song_id}.json",
            json.dumps(raw, ensure_ascii=False, indent=1),
        )
    return out


def _describe(pipeline: Pipeline) -> dict[str, Any]:
    return {
        "name": pipeline.name,
        "description": pipeline.description,
        "steps": {
            kind: {"target": spec.target, "params": spec.params, "version": step_version(spec)}
            for kind, spec in pipeline.steps.items()
        },
    }


def _environment() -> dict[str, str]:
    from karaoke_bench.resources import gpu_info

    env = {"python": platform.python_version(), "platform": platform.platform()}
    for package in _PACKAGES:
        try:
            env[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            continue
    return env | gpu_info()


def _reference_kind(states: list[_SongState]) -> dict[str, str]:
    kinds: dict[str, set[str]] = {}
    for state in states:
        if state.reference:
            kinds.setdefault(state.song.language, set()).add(state.reference.timing)
    return {lang: next(iter(k)) if len(k) == 1 else "mixed" for lang, k in sorted(kinds.items())}


def _git_commit() -> str | None:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return f"{head}-dirty" if dirty else head
