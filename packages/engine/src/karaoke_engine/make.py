"""`karaoke make`: a song and its lyrics in, a karaoke package out.

The steps run one after another in this process, each freeing the GPU before the next loads its
model (a 4 GB card holds one at a time): decode the song, separate the voice, align the lyrics,
level and encode the stems, and only then write karaoke.json, so an interrupted run never leaves
a package that looks complete.
"""

import logging
import re
import subprocess
import tempfile
import unicodedata
from collections.abc import Callable
from importlib import metadata
from pathlib import Path
from typing import Any, Literal

from karaoke_contracts import (
    KaraokeDoc,
    LanguageFallback,
    Line,
    Provenance,
    Singer,
    VideoRefs,
    dump_doc,
    validate_doc,
    validate_package,
)
from karaoke_engine.align.aligner import LyricsAligner
from karaoke_engine.align.clitics import join_clitics
from karaoke_engine.align.lyrics import parse_lyrics, singer_id
from karaoke_engine.align.models import DEFAULT_BY_LANGUAGE, FALLBACK_MODEL
from karaoke_engine.audio import decode, package_audio, probe
from karaoke_engine.separation import RoformerSeparator
from karaoke_engine.steps import Separator, TextAligner, Transcriber
from karaoke_engine.transcribe import LineSegmenter, WhisperTranscriber, transcribe_in_child
from karaoke_engine.video.media import extract_background, extract_cover, probe_video

_LANGUAGE = re.compile(r"^[a-z]{2,3}$")


logger = logging.getLogger(__name__)


def default_separator() -> Separator:
    """The separator chosen with the bench (decision 004): Kim's Mel-Band RoFormer, 8 s chunks."""
    return RoformerSeparator(model="vocals_mel_band_roformer.ckpt", segment_size=801)


def default_aligner(**options: Any) -> TextAligner:
    return LyricsAligner(**options)


def make_package(
    source: Path,
    out_dir: Path,
    language: str,
    lyrics: str | None,
    *,
    separator: Separator | None = None,
    aligner: TextAligner | None = None,
    transcriber: Transcriber | None = None,
    lyrics_source: Literal["user", "lrclib"] = "user",
    overlap_backing: bool = False,
    title: str | None = None,
    artist: str | None = None,
    progress: Callable[[str], None] | None = None,
) -> KaraokeDoc:
    """Without lyrics it transcribes: with the given transcriber, or else in a child process."""
    # Everything that can fail cheaply fails before the long steps start.
    if not _LANGUAGE.match(language):
        raise ValueError(f"language must be a two or three letter code like gl, not {language!r}")
    probe(source)  # files without audio
    if lyrics is not None and not parse_lyrics(lyrics):
        raise ValueError("the lyrics have no sung lines (only labels or symbols)")
    if lyrics is None and transcriber is None:
        # A model converted on first use needs the memory before anything else is loaded.
        WhisperTranscriber().prepare_for(language)
    step = progress or (lambda name: None)
    separator = separator or default_separator()
    if aligner is None:
        aligner = default_aligner(overlap_backing=True) if overlap_backing else default_aligner()
    out_dir.mkdir(parents=True, exist_ok=True)
    # An old document next to new audio would look like a finished package.
    (out_dir / "karaoke.json").unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(dir=out_dir, prefix=".make-") as tmp:
        work = Path(tmp)
        step("decode")
        mix = decode(source, work / "mix.wav")
        step("separate")
        stems = separator.separate(mix, work / "stems")
        _unload(separator)
        asr_model = None
        source_kind: Literal["user", "asr", "lrclib"] = lyrics_source
        if lyrics is None:
            step("transcribe")
            if transcriber is None:
                transcript, asr_model = transcribe_in_child(stems.vocals, language)
            else:
                transcript = transcriber.transcribe(stems.vocals, language)
                asr_model = _model_name(transcriber, language)
                _unload(transcriber)
            lyrics = "\n".join(LineSegmenter().segment(transcript))
            source_kind = "asr"
        step("align")
        lines = aligner.align_text(stems.vocals, lyrics, language)
        _unload(aligner)
        if language == "gl":
            lines = join_clitics(lines)
        step("encode")
        refs = package_audio(mix, stems, out_dir)
        duration = probe(mix).duration
        video, cover = _keep_pictures(source, out_dir)
    name = title or source.stem
    doc = KaraokeDoc(
        id=slug(name) or "karaoke",
        title=name,
        artist=artist,
        language=language,
        duration=duration,
        audio=refs,
        video=video,
        cover=cover,
        singers=_singers(lyrics),
        lines=_numbered(lines),
        provenance=Provenance(
            lyrics_source=source_kind,
            separation_model=str(getattr(separator, "model", separator.name)),
            asr_model=asr_model,
            align_model=_model_name(aligner, language),
            engine_version=f"karaoke-engine {metadata.version('karaoke-engine')}",
            language_fallbacks=_fallbacks(language),
        ),
    )
    issues = validate_doc(doc)
    if issues:
        raise ValueError("; ".join(f"{i.path}: {i.message}" for i in issues[:5]))
    staged = out_dir / ".karaoke.json.tmp"
    dump_doc(doc, staged)
    staged.replace(out_dir / "karaoke.json")
    issues = validate_package(out_dir)
    if issues:
        raise ValueError("; ".join(f"{i.path}: {i.message}" for i in issues[:5]))
    return doc


def _keep_pictures(source: Path, out_dir: Path) -> tuple[VideoRefs | None, str | None]:
    """The song's video as the package background and its cover art (or a frame) as cover."""
    for old in ("background.mp4", "cover.jpg"):
        (out_dir / old).unlink(missing_ok=True)
    # Both are extras: a file whose pictures ffmpeg cannot handle still makes its karaoke.
    video = None
    try:
        if probe_video(source) is not None:
            extract_background(source, out_dir / "background.mp4")
            video = VideoRefs(background="background.mp4")
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        logger.warning("could not keep the video of %s: %s", source.name, exc)
        (out_dir / "background.mp4").unlink(missing_ok=True)
    cover = None
    try:
        if extract_cover(source, out_dir / "cover.jpg") is not None:
            cover = "cover.jpg"
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        logger.warning("could not keep the cover of %s: %s", source.name, exc)
        (out_dir / "cover.jpg").unlink(missing_ok=True)
    return video, cover


def slug(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")


def _numbered(lines: list[Line]) -> list[Line]:
    ordered = sorted(lines, key=lambda line: line.start)
    return [
        line.model_copy(update={"id": f"l{i + 1}", "singer": line.singer or "s1"})
        for i, line in enumerate(ordered)
    ]


def _singers(lyrics: str) -> list[Singer]:
    """s1 for lines nobody is credited with, then one singer per name in the section labels."""
    singers = [Singer(id="s1")]
    seen = {"s1"}
    for line in parse_lyrics(lyrics):
        if line.singer and singer_id(line.singer) not in seen:
            seen.add(singer_id(line.singer))
            singers.append(Singer(id=singer_id(line.singer), name=line.singer))
    return singers


def _model_name(step: Any, language: str) -> str:
    describe = getattr(step, "model_for_language", None)
    if callable(describe):
        return str(describe(language))
    return str(getattr(step, "model_name", step.name))


def _fallbacks(language: str) -> list[LanguageFallback]:
    if language in DEFAULT_BY_LANGUAGE:
        return []
    return [
        LanguageFallback(
            step="align",
            requested=language,
            used=FALLBACK_MODEL,
            reason="no alignment model for this language; a multilingual one aligns it",
        )
    ]


def _unload(step: Any) -> None:
    unload = getattr(step, "unload", None)
    if callable(unload):
        unload()
