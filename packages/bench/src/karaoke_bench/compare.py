"""Side-by-side comparison of two runs, to say whether a change helped."""

from collections.abc import Callable

from karaoke_bench.results import GroupSummary, RunResults, SongResult

# A song "gets worse" past these thresholds (seconds of start median, points of WER).
TIMING_REGRESSION = 0.05
WER_REGRESSION = 0.05

_Metric = tuple[str, Callable[[GroupSummary], float | None], str]
_METRICS: list[_Metric] = [
    ("WER", lambda g: g.wer, "pct"),
    ("CER", lambda g: g.cer, "pct"),
    ("Inicio mediana (s)", lambda g: g.timing.start_median if g.timing else None, "num"),
    ("Inicio ≤ 0,3 s", lambda g: g.timing.start_within if g.timing else None, "pct"),
    ("Cobertura", lambda g: g.timing.coverage if g.timing else None, "pct"),
    ("Cambios de idioma", lambda g: float(g.language_switches), "int"),
    ("Tiempo estimado 4 min (s)", lambda g: g.est_seconds_4min, "num"),
]


def compare_runs(a: RunResults, b: RunResults) -> str:
    out = [
        f"# Comparación: {a.pipeline['name']} → {b.pipeline['name']}",
        "",
        f"- A: {a.created} · {a.set_name} · {a.mode} · commit {a.git_commit or '—'}",
        f"- B: {b.created} · {b.set_name} · {b.mode} · commit {b.git_commit or '—'}",
    ]
    if a.normalization_version != b.normalization_version:
        out.append(
            f"- ⚠ Normalización distinta (v{a.normalization_version} frente a "
            f"v{b.normalization_version}): los WER no son comparables."
        )
    if (a.set_name, a.mode) != (b.set_name, b.mode):
        out.append("- ⚠ Conjunto o modo distintos: compara con cuidado.")
    groups = [g for g in a.summary if g in b.summary and g != "all"] + ["all"]
    for group in groups:
        title = "total" if group == "all" else group
        out += ["", f"## {title}", "", "| Métrica | A | B | Δ |", "|---|---|---|---|"]
        for label, get, kind in _METRICS:
            va, vb = get(a.summary[group]), get(b.summary[group])
            out.append(
                f"| {label} | {_fmt(va, kind)} | {_fmt(vb, kind)} | {_delta(va, vb, kind)} |"
            )
    out += ["", "## Canciones que empeoran", ""]
    worse = _regressions(a.songs, b.songs)
    out += worse or ["(ninguna)"]
    return "\n".join(out) + "\n"


def _regressions(a: list[SongResult], b: list[SongResult]) -> list[str]:
    before = {s.song_id: s for s in a}
    lines = []
    for after in b:
        old = before.get(after.song_id)
        if old is None:
            continue
        reasons = []
        if old.timing and after.timing:
            diff = after.timing.start_median - old.timing.start_median
            if diff >= TIMING_REGRESSION:
                reasons.append(f"inicio mediana {diff:+.3f} s")
        if old.wer is not None and after.wer is not None and after.wer - old.wer >= WER_REGRESSION:
            reasons.append(f"WER {100 * (after.wer - old.wer):+.1f} puntos")
        if after.error and not old.error:
            reasons.append(f"ahora falla: {after.error}")
        if reasons:
            lines.append(f"- {after.song_id}: {', '.join(reasons)}")
    return lines


def _fmt(value: float | None, kind: str) -> str:
    if value is None:
        return "—"
    if kind == "pct":
        return f"{100 * value:.1f} %"
    if kind == "int":
        return str(int(value))
    return f"{value:.3f}"


def _delta(a: float | None, b: float | None, kind: str) -> str:
    if a is None or b is None:
        return "—"
    if kind == "pct":
        return f"{100 * (b - a):+.1f}"
    if kind == "int":
        return f"{int(b - a):+d}"
    return f"{b - a:+.3f}"
