"""One job, run in a process of its own: `python -m karaoke_server.jobs.runner spec.json`.

It reports on stdout, one JSON object per line: `{"event": "stage", "stage": ...}` as the engine
moves on, `{"event": "lyrics"}` when LRCLIB had them, notes, and at the end `{"event": "done",
"result": ...}` or `{"event": "error", "code": ..., "message": ..., "transient": ...}`. Logs go
to stderr, which the server keeps in the job's log.txt. With `"fake": true` it pretends, quickly
and without a GPU, with the synthetic demo package (for tests and trying the app).
"""

import errno
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from karaoke_server.config import REPO
from karaoke_server.jobs.titles import split_artist

logger = logging.getLogger("karaoke_server.runner")

DEMO = REPO / "fixtures" / "packages" / "demo-sintetico"


def emit(**event: Any) -> None:
    print(json.dumps(event, ensure_ascii=False), flush=True)


def classify_error(exc: BaseException) -> tuple[str, bool]:
    """What went wrong, as an error code, and whether trying again could help."""
    from karaoke_engine.audio import AudioError

    message = str(exc)
    if isinstance(exc, AudioError):
        return "unreadable", False
    if type(exc).__name__ == "OutOfMemoryError" or "CUDA out of memory" in message:
        return "gpu_memory", True
    if isinstance(exc, MemoryError):
        return "out_of_memory", True
    if isinstance(exc, OSError) and exc.errno == errno.ENOSPC:
        return "disk_full", False
    if isinstance(exc, RuntimeError) and "CUDA" in message:
        return "engine_failed", True
    if isinstance(exc, ValueError) and "lyrics" in message:
        return "bad_lyrics", False
    return "engine_failed", False


def run_make(spec: dict[str, Any]) -> dict[str, Any]:
    if spec.get("fake"):
        return fake_make(spec)
    from karaoke_engine.audio import probe
    from karaoke_engine.lyrics_lookup import find_lyrics
    from karaoke_engine.make import make_package

    source, out = Path(spec["source"]), Path(spec["out"])
    lyrics: str | None = (spec.get("lyrics") or "").strip() or None
    title, artist = spec.get("title"), spec.get("artist")
    kind = "user"
    if lyrics is None and spec.get("lrclib"):
        if not artist and title:
            artist, title = split_artist(title)
        if title and artist:
            found = find_lyrics(title, artist, probe(source).duration)
            if found is None:
                emit(event="note", message="LRCLIB has no lyrics for this song; transcribing")
            else:
                lyrics, kind = found.text, "lrclib"
                emit(event="lyrics", source="lrclib")
    doc = make_package(
        source,
        out,
        spec["language"],
        lyrics,
        title=title,
        artist=artist,
        lyrics_source="lrclib" if kind == "lrclib" else "user",
        progress=lambda step: emit(event="stage", stage=step),
    )
    return {"doc_id": doc.id, "duration": doc.duration}


def run_export(spec: dict[str, Any]) -> dict[str, Any]:
    out = Path(spec["out"])
    if spec.get("fake"):
        _pause()
        background = Path(spec["package"]) / "background.mp4"
        if background.is_file():
            shutil.copy(background, out)
        else:
            out.write_bytes(b"\x00\x00\x00\x18ftypmp42")
        return {"file": str(out)}
    from karaoke_engine.subtitles.themes import load_theme
    from karaoke_engine.video.render import render

    report = render(Path(spec["package"]), out, load_theme(spec["theme"]), aspect=spec["aspect"])
    return {"file": str(out), "seconds": report.seconds, "encoder": report.encoder}


def run_prepare(spec: dict[str, Any]) -> dict[str, Any]:
    """Downloads (and converts) every model a language needs, before the first song."""
    from huggingface_hub import snapshot_download

    from karaoke_engine.align.models import DEFAULT_BY_LANGUAGE, FALLBACK_MODEL, MODELS
    from karaoke_engine.make import default_separator
    from karaoke_engine.transcribe import WhisperTranscriber

    language = spec["language"]
    emit(event="note", message="separator")
    separator = default_separator()
    load = getattr(separator, "load", None)
    if callable(load):
        load()
        separator.unload()  # type: ignore[attr-defined]
    emit(event="note", message="aligner")
    model = MODELS[DEFAULT_BY_LANGUAGE.get(language, FALLBACK_MODEL)]
    snapshot_download(model.repo, revision=getattr(model, "revision", None))
    emit(event="note", message="transcriber")
    WhisperTranscriber().prepare_for(language)
    return {"language": language}


def _pause() -> None:
    time.sleep(float(os.environ.get("KARAOKE_FAKE_STAGE_SECONDS", "0.05")))


def fake_make(spec: dict[str, Any]) -> dict[str, Any]:
    from karaoke_contracts import dump_doc, load_doc
    from karaoke_engine.demo import synthesize_package_audio

    with_lyrics = bool((spec.get("lyrics") or "").strip())
    steps = ["decode", "separate", *([] if with_lyrics else ["transcribe"]), "align", "encode"]
    for step in steps:
        emit(event="stage", stage=step)
        _pause()
    out = Path(spec["out"])
    out.mkdir(parents=True, exist_ok=True)
    doc = load_doc(DEMO / "karaoke.json")
    update = {
        "title": spec.get("title") or doc.title,
        "artist": spec.get("artist"),
        "language": spec.get("language") or doc.language,
    }
    changed = doc.model_copy(update=update)
    dump_doc(changed, out / "karaoke.json")
    synthesize_package_audio(out)
    return {"doc_id": changed.id, "duration": changed.duration}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    spec = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    try:
        kind = spec.get("kind")
        if kind == "export":
            result = run_export(spec)
        elif kind == "prepare":
            result = run_prepare(spec)
        else:
            result = run_make(spec)
    except Exception as exc:
        logger.exception("the job failed")
        code, transient = classify_error(exc)
        emit(event="error", code=code, message=str(exc)[:500], transient=transient)
        return 1
    emit(event="done", result=result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
