"""Markdown report of a run, in Spanish like the rest of the project docs.

The layout never changes, so two reports read side by side (and `compare` can rely on it).
"""

from karaoke_bench.metrics import TimingStats
from karaoke_bench.results import GroupSummary, RunResults, SongResult

_MODES = {"lyrics": "con letra", "asr": "sin letra"}


def render_report(results: RunResults) -> str:
    out = [
        f"# Banco · {results.pipeline['name']} · {results.set_name} · "
        f"{_MODES.get(results.mode, results.mode)}",
        "",
        f"- Fecha: {results.created}",
        f"- Commit: {results.git_commit or '—'}",
        f"- Banco {results.bench_version}, normalización v{results.normalization_version}",
        f"- Referencias: {_reference_kinds(results)}",
        "",
        "## Entorno",
        "",
        "| Clave | Valor |",
        "|---|---|",
        *(f"| {key} | {value} |" for key, value in sorted(results.environment.items())),
        "",
        "## Pipeline",
        "",
        results.pipeline.get("description") or "(sin descripción)",
        "",
        *(
            f"- **{kind}**: `{step['target']}` v{step['version']} {step['params'] or ''}".rstrip()
            for kind, step in results.pipeline["steps"].items()
        ),
        "",
        "## Resumen",
        "",
        "| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s "
        "| Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        *(_summary_row(name, group) for name, group in _ordered(results.summary)),
        "",
        "## Etapas",
        "",
        "| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |",
        "|---|---|---|---|---|",
        *(
            f"| {kind} | {_num(stage.load_seconds, 1)} | {_num(stage.vram_peak_mb, 0)} "
            f"| {_num(stage.ram_peak_mb, 0)} "
            f"| {_num(results.summary['all'].rtf_median.get(kind), 3)} |"
            for kind, stage in results.stages.items()
        ),
        "",
        "## Por canción",
        "",
        "| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | Cobertura "
        "| Idioma devuelto | Tiempo (s) | Error |",
        "|---|---|---|---|---|---|---|---|---|---|",
        *(_song_row(song) for song in results.songs),
        "",
        "## Peores casos",
        "",
        *_worst(results.songs),
        "",
        "## Notas",
        "",
        *_notes(results),
        "",
    ]
    return "\n".join(out)


def _ordered(summary: dict[str, GroupSummary]) -> list[tuple[str, GroupSummary]]:
    return [(k, summary[k]) for k in sorted(summary) if k != "all"] + [("total", summary["all"])]


def _summary_row(name: str, g: GroupSummary) -> str:
    t = g.timing
    cells = [
        name,
        str(g.songs),
        str(g.failed),
        _pct(g.wer),
        _pct(g.cer),
        _num(_stat(t, "start_median")),
        _num(_stat(t, "start_mean")),
        _pct(_stat(t, "start_within")),
        _num(_stat(t, "end_median")),
        _num(_stat(t, "start_bias")),
        _pct(_stat(t, "coverage")),
        _num(g.line_start_median),
        str(g.language_switches),
        _num(g.est_seconds_4min, 0),
    ]
    return _row(cells)


def _song_row(s: SongResult) -> str:
    t = s.timing
    seconds = sum(step.seconds for step in s.steps.values())
    cached = " (caché)" if s.steps and all(step.cached for step in s.steps.values()) else ""
    error = (s.error or "").replace("|", "/").replace("\n", " ")[:120]
    cells = [
        s.song_id,
        s.language,
        _num(s.duration, 0),
        _pct(s.wer),
        _num(_stat(t, "start_median")),
        _pct(_stat(t, "start_within")),
        _pct(_stat(t, "coverage")),
        s.language_reported or "—",
        _num(seconds, 1) + cached,
        error,
    ]
    return _row(cells)


def _row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _worst(songs: list[SongResult]) -> list[str]:
    lines = []
    timed = [(s.song_id, s.timing.start_median) for s in songs if s.timing]
    if timed:
        lines.append("Mayor mediana de error de inicio:")
        lines += [
            f"- {song_id}: {_num(v)} s" for song_id, v in sorted(timed, key=lambda x: -x[1])[:5]
        ]
    transcribed = sorted((s for s in songs if s.wer is not None), key=lambda s: -(s.wer or 0))
    if transcribed:
        lines.append("")
        lines.append("Mayor WER:")
        lines += [f"- {s.song_id}: {_pct(s.wer)}" for s in transcribed[:5]]
    return lines or ["(nada que destacar)"]


def _notes(results: RunResults) -> list[str]:
    notes = [f"- {note}" for note in results.notes]
    failed = [s for s in results.songs if s.error]
    notes += [f"- Falló {s.song_id}: {s.error}" for s in failed]
    semi = [lang for lang, kind in results.reference_kind.items() if kind != "manual"]
    if semi:
        notes.append(
            f"- Referencia semiautomática validada de oído en {', '.join(semi)}: fiable a unos "
            "±0,1 s, así que ahí manda el % ≤ 0,3 s más que la mediana."
        )
    notes.append(
        "- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la "
        "referencia (sin tildes); sesgo = media con signo (positivo = tarde)."
    )
    return notes


def _reference_kinds(results: RunResults) -> str:
    kinds = {"manual": "manual", "semiautomatic": "semiautomática", "mixed": "mixta"}
    items = [f"{lang} {kinds.get(kind, kind)}" for lang, kind in results.reference_kind.items()]
    return ", ".join(items) or "—"


def _stat(stats: TimingStats | None, name: str) -> float | None:
    return None if stats is None else float(getattr(stats, name))


def _num(value: float | None, digits: int = 3) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{100 * value:.1f} %"
