"""Shared layout cases: the web player must lay these out exactly as `build_layout` does.

`python -m karaoke_engine.subtitles.conformance --write` rewrites `fixtures/lyrics-layout/` after a
deliberate change to the layout; a Python test fails while the files are stale, and a web test
fails while the TS layout disagrees with them.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from karaoke_contracts import KaraokeDoc, load_doc
from karaoke_engine.subtitles.layout import build_layout
from karaoke_engine.subtitles.themes import load_theme, theme_metrics

ROOT = Path(__file__).resolve().parents[5]
CASES_DIR = ROOT / "fixtures/lyrics-layout"
SIZES = {"tv": (1920, 1080), "phone": (390, 844), "vertical": (1080, 1920)}


def _word(text: str, start: float, end: float, parts: list[Any] | None = None) -> dict[str, Any]:
    return {
        "text": text,
        "start": start,
        "end": end,
        "parts": [{"text": t, "start": s, "end": e} for t, s, e in parts or []],
    }


def _line(
    line_id: str, words: list[dict[str, Any]], role: str = "lead", singer: str | None = "s1"
) -> dict[str, Any]:
    return {
        "id": line_id,
        "start": words[0]["start"],
        "end": words[-1]["end"],
        "singer": singer,
        "role": role,
        "words": words,
    }


def _doc(doc_id: str, lines: list[dict[str, Any]], singers: int = 1) -> dict[str, Any]:
    return {
        "id": doc_id,
        "title": doc_id,
        "language": "gl",
        "duration": 60.0,
        "audio": {"instrumental": "instrumental.m4a"},
        "singers": [{"id": f"s{i + 1}"} for i in range(singers)],
        "lines": lines,
        "provenance": {"lyrics_source": "user", "engine_version": "test"},
    }


def _synthetic() -> dict[str, dict[str, Any]]:
    long_words = [
        "Camiñando",
        "pola",
        "beira",
        "do",
        "mar",
        "escoito",
        "as",
        "ondas",
        "que",
        "me",
        "chaman,",
        "vente",
        "xa",
    ]
    step = 0.4
    long_line = [_word(w, 2.0 + i * step, 2.0 + (i + 1) * step) for i, w in enumerate(long_words)]
    return {
        "coros": _doc(
            "coros",
            [
                _line(
                    "l1",
                    [
                        _word(
                            "Bailamos",
                            8.0,
                            9.0,
                            [("Bai", 8.0, 8.3), ("la", 8.3, 8.6), ("mos", 8.6, 9.0)],
                        ),
                        _word("ata", 9.1, 9.5, [("a", 9.1, 9.3), ("ta", 9.3, 9.5)]),
                        _word("tarde", 9.6, 10.4, [("tar", 9.6, 10.0), ("de", 10.0, 10.4)]),
                    ],
                ),
                _line("b1", [_word("oh", 9.2, 9.8), _word("oh,", 9.8, 10.3)], role="backing"),
                _line("l2", [_word("e", 10.8, 11.0), _word("despois", 11.1, 12.0)]),
                _line("b2", [_word("despois!", 12.2, 13.0)], role="backing"),
                _line("b3", [_word("eh", 30.0, 30.5)], role="backing"),
            ],
        ),
        "lina-longa": _doc("lina-longa", [_line("l1", long_line)]),
        # Fast rap: short lines 0.1 s apart, so a slot is handed over before its hold is over.
        "rap": _doc(
            "rap",
            [
                _line(
                    f"l{i + 1}",
                    [
                        _word(w, 4.0 + i * 0.7 + j * 0.3, 4.0 + i * 0.7 + (j + 1) * 0.3)
                        for j, w in enumerate(["veña", "dálle"])
                    ],
                )
                for i in range(6)
            ],
        ),
        # A line two places later starts right after this one ends: it must wait for it.
        "pegadas": _doc(
            "pegadas",
            [
                _line("l1", [_word("Unha", 4.0, 4.4), _word("liña", 4.5, 5.0)]),
                _line("l2", [_word("eh", 5.0, 5.1)]),
                _line("l3", [_word("outra", 5.2, 6.0)]),
                _line("l4", [_word("máis", 6.1, 7.0)]),
            ],
        ),
        "desde-cero": _doc(
            "desde-cero",
            [
                _line("l1", [_word("Xa", 0.0, 0.4), _word("estamos", 0.5, 1.2)]),
                _line("l2", [_word("aquí", 1.5, 2.2)]),
                _line("l3", [_word("¡vamos!", 2.4, 3.0)]),
            ],
        ),
        "duo": _doc(
            "duo",
            [
                _line("l1", [_word("Ti", 6.0, 6.5), _word("cantas", 6.6, 7.5)], singer="s1"),
                _line("l2", [_word("eu", 7.0, 7.4), _word("respondo", 7.5, 8.6)], singer="s2"),
                _line("l3", [_word("xuntos", 9.0, 10.0)], singer="s1"),
                _line("l4", [_word("ao", 10.2, 10.5), _word("final", 10.5, 11.5)], singer="s2"),
            ],
            singers=2,
        ),
    }


def cases() -> dict[str, dict[str, Any]]:
    """Every case: its input (a document, or the path of one) and the layout it must produce."""
    inputs: list[tuple[str, dict[str, Any] | str, str, str]] = []
    for theme_name in ("clasico", "contraste", "moderno"):
        for size in SIZES:
            inputs.append(
                (
                    f"demo-{theme_name}-{size}",
                    "fixtures/packages/demo-sintetico/karaoke.json",
                    theme_name,
                    size,
                )
            )
    for size in ("tv", "phone"):
        inputs.append(
            (
                f"esencia-clasico-{size}",
                "fixtures/packages/nandomalo-esencia/karaoke.json",
                "clasico",
                size,
            )
        )
    for name, synthetic in _synthetic().items():
        for size in ("tv", "phone"):
            inputs.append((f"{name}-clasico-{size}", synthetic, "clasico", size))
        inputs.append((f"{name}-moderno-phone", synthetic, "moderno", "phone"))
    out: dict[str, dict[str, Any]] = {}
    for case_id, source, theme_id, size in inputs:
        if isinstance(source, str):
            doc = load_doc(ROOT / source)
        else:
            doc = KaraokeDoc.model_validate(source)
        theme = load_theme(theme_id)
        width, height = SIZES[size]
        layout = build_layout(doc, theme, width, height, theme_metrics(theme))
        out[case_id] = {
            "doc": source,
            "theme": theme_id,
            "width": width,
            "height": height,
            "layout": layout.model_dump(mode="json"),
        }
    return out


def write(directory: Path = CASES_DIR) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for old in directory.glob("*.json"):
        old.unlink()
    for case_id, case in cases().items():
        text = json.dumps(case, ensure_ascii=False, separators=(",", ":"))
        (directory / f"{case_id}.json").write_text(text + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="rewrite fixtures/lyrics-layout/")
    args = parser.parse_args()
    if args.write:
        write()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
