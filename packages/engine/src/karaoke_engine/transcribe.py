"""Transcription when there are no lyrics: Whisper models (Galician ones for Galician) on the voice.

faster-whisper (CTranslate2) runs them in 8 bits, so even a large-v3 fits the 4 GB card. Galician
fine-tunes are published for transformers; the first use converts them once into the model cache.
The language is always the one asked for, never a guess. Whisper invents text in silences and
loops on repeats, so segments where the separated voice is silent and runaway repeats are dropped.
"""

import ctypes
import importlib.util
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from karaoke_engine.align.activity import vocal_activity
from karaoke_engine.align.audio import SAMPLE_RATE, load_mono16k
from karaoke_engine.steps import Transcript, TranscriptSegment

CACHE = Path.home() / ".cache" / "karaoke" / "models" / "ct2"
_NOTE_BRACKETS = re.compile(r"\[[^\]]*\]|[♪♫]")
_NOTE_WORD = re.compile(r"\(\s*[^()\s]+\s*\)")
_REPEAT_MARK = re.compile(r"^[x\u00d7]\d+$", re.IGNORECASE)
_HOP = 0.02
# A segment needs at least this share of voiced time; Whisper fills silences with stock phrases.
MIN_VOICE_SHARE = 0.3
# Repeats and loops only count as made up where the voice sounds less than this: a chorus sung
# over and over is real.
_SURE_VOICE_SHARE = 0.6
# Converting a large-v3 holds two copies of it at once (6.7 GB at peak).
CONVERSION_MEMORY_GB = 6.0
# The same text this many times in a row is a loop; and a long run of one or two words is too.
_MAX_SAME_IN_A_ROW = 2
_LOOP_WORDS = 10
_CHANT_WORDS = 8


@dataclass(frozen=True)
class WhisperSpec:
    repo: str
    revision: str
    licence: str
    converted: bool  # already in CTranslate2 format


MODELS: dict[str, WhisperSpec] = {
    "large-v3-turbo": WhisperSpec(
        "dropbox-dash/faster-whisper-large-v3-turbo",
        "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf",
        "MIT",
        True,
    ),
    "nos-turbo-gl": WhisperSpec(
        "proxectonos/whisper-large-v3-turbo-gl-v1.0",
        "9395c7fcc24760ffdf10d665fff3b2a119d0758a",
        "Apache-2.0",
        False,
    ),
    "hitz-large-v3-gl": WhisperSpec(
        "HiTZ/whisper-large-v3-gl", "323307be9018a24572e3fdb06219234038b0e490", "Apache-2.0", False
    ),
    "bsc-los": WhisperSpec(
        "BSC-LT/whisper-large-v3-LoS",
        "88111779fbb59e28fea2627c146201d3a4f7748f",
        "Apache-2.0",
        False,
    ),
}
# Chosen with the bench (decision 005); everything else uses large-v3-turbo.
DEFAULT_BY_LANGUAGE: dict[str, str] = {"gl": "hitz-large-v3-gl"}


class WhisperTranscriber:
    name = "whisper"
    # Bumped when a default changes too: defaults are not part of the bench cache key.
    version = "5"

    def __init__(
        self,
        model: str = "auto",
        vad: bool = True,
        seed: int = 0,
        beam_size: int = 1,
        compute_type: str = "int8_float16",
        device: str = "cuda",
        whisper: Any = None,
    ) -> None:
        if model != "auto" and model not in MODELS:
            raise ValueError(f"unknown Whisper model '{model}' (use auto, {', '.join(MODELS)})")
        self.model = model
        self.vad = vad
        self.seed = seed
        self.beam_size = beam_size
        self.compute_type = compute_type
        self.device = device
        self._injected = whisper
        self._loaded: tuple[str, Any] | None = None

    def load(self) -> None:
        if self._injected is None and self.model != "auto":
            self._whisper_for(self.model)

    def prepare_for(self, language: str) -> None:
        """Downloads (and converts once) the model a language will use, before anything loads."""
        if self._injected is None:
            prepare(self._name_for(language))

    def model_for_language(self, language: str) -> str:
        name = (
            self.model
            if self.model != "auto"
            else DEFAULT_BY_LANGUAGE.get(language, "large-v3-turbo")
        )
        spec = MODELS[name]
        return f"{spec.repo}@{spec.revision[:12]}"

    def transcribe(self, vocals: Path, language: str) -> Transcript:
        samples = load_mono16k(vocals)
        whisper = self._injected or self._whisper_for(self._name_for(language))
        if self._injected is None:
            import ctranslate2

            ctranslate2.set_random_seed(self.seed)
        segments, _ = whisper.transcribe(
            samples,
            language=language,
            beam_size=self.beam_size,
            vad_filter=self.vad,
            condition_on_previous_text=False,
            compression_ratio_threshold=2.4,
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0,
        )
        active = vocal_activity(samples, SAMPLE_RATE, _HOP)
        kept: list[TranscriptSegment] = []
        for segment in segments:
            text = " ".join(segment.text.split())
            share = _voice_share(active, segment.start, segment.end)
            if not text or share < MIN_VOICE_SHARE:
                continue
            looping = _is_loop(text) or _repeats(kept, text) >= _MAX_SAME_IN_A_ROW
            if looping and share < _SURE_VOICE_SHARE:
                continue
            if _is_loop(text):
                # A chant may be real, but Whisper runs on with it: keep one line of it.
                text = " ".join(text.split()[:_CHANT_WORDS])
            kept.append(TranscriptSegment(segment.start, segment.end, text))
        return Transcript(language=language, segments=tuple(kept))

    def unload(self) -> None:
        import gc

        self._loaded = None
        gc.collect()

    def _name_for(self, language: str) -> str:
        if self.model != "auto":
            return self.model
        return DEFAULT_BY_LANGUAGE.get(language, "large-v3-turbo")

    def _whisper_for(self, name: str) -> Any:
        if self._loaded is not None and self._loaded[0] == name:
            return self._loaded[1]
        self.unload()
        if self.device == "cuda":
            _preload_cuda12()
        from faster_whisper import WhisperModel

        model = WhisperModel(
            str(_ct2_dir(name)), device=self.device, compute_type=self.compute_type
        )
        self._loaded = (name, model)
        return model


class LineSegmenter:
    """Lyric lines from a transcript: a line per sentence, and no line longer than MAX_WORDS."""

    name = "lines"
    version = "2"
    MAX_WORDS = 9

    def segment(self, transcript: Transcript) -> list[str]:
        lines: list[str] = []
        for segment in transcript.segments:
            for sentence in _sentences(_without_notes(segment.text)):
                words = sentence.split()
                chunks = -(-len(words) // self.MAX_WORDS)
                size = -(-len(words) // chunks)
                lines += [" ".join(words[i : i + size]) for i in range(0, len(words), size)]
        return lines


def _without_notes(text: str) -> str:
    """Drops what transcribers add that is not sung ([Música], (risas), ♪) and anything the lyrics
    parser would read as a label, a repeat mark or a backing part."""
    text = _NOTE_BRACKETS.sub(" ", text)
    text = _NOTE_WORD.sub(" ", text)
    text = text.replace("(", " ").replace(")", " ")
    words = [w for w in text.split() if not _REPEAT_MARK.match(w) and any(c.isalnum() for c in w)]
    return " ".join(words)


def _sentences(text: str) -> list[str]:
    out, current = [], []
    for word in text.split():
        current.append(word)
        if word[-1] in ".!?;…":
            out.append(" ".join(current))
            current = []
    if current:
        out.append(" ".join(current))
    return out


def transcribe_in_child(vocals: Path, language: str) -> tuple[Transcript, str]:
    """Transcribes in a fresh process, and says with which model.

    CTranslate2 and torch keep their memory in the process that used them: alongside the
    separator and the aligner, a large-v3 pushed `karaoke make` to 5.7 GB of RAM. In a child, its
    memory goes back to the system as soon as the text is out.
    """
    import multiprocessing

    with multiprocessing.get_context("spawn").Pool(1) as pool:
        found, segments, model = pool.apply(_transcribe_here, (str(vocals), language))
    return Transcript(found, tuple(TranscriptSegment(*s) for s in segments)), model


def _transcribe_here(vocals: str, language: str) -> tuple[str, list[tuple[float, float, str]], str]:
    transcriber = WhisperTranscriber()
    transcript = transcriber.transcribe(Path(vocals), language)
    segments = [(s.start, s.end, s.text) for s in transcript.segments]
    return transcript.language, segments, transcriber.model_for_language(language)


def _ct2_dir(name: str) -> Path:
    """The model in CTranslate2 format: downloaded as is, or converted once from transformers."""
    spec = MODELS[name]
    if spec.converted:
        return _download(spec)
    return prepare(name)


def prepare(name: str) -> Path:
    """Converts a transformers model to CTranslate2 once, in a process of its own.

    The converter holds the PyTorch model and its converted copy at once (6.7 GB for a large-v3):
    run alone, all of it goes back to the system when it ends. It writes into a side folder that
    only takes the final name once the conversion has finished, so an interrupted one is redone.
    `karaoke make` prepares the model before loading anything else.
    """
    spec = MODELS[name]
    if spec.converted:
        return _download(spec)
    target = CACHE / f"{name}-{spec.revision[:12]}"
    if (target / "model.bin").is_file():
        return target
    free = _available_memory_gb()
    if free < CONVERSION_MEMORY_GB:
        raise ModelError(
            f"converting {spec.repo} the first time needs about {CONVERSION_MEMORY_GB:.0f} GB of "
            f"free memory and {free:.1f} GB are free: close other programs and try again"
        )
    print(f"First use of {spec.repo}: downloading and converting it once.", file=sys.stderr)
    source = _download(spec)
    side = target.with_name(target.name + ".partial")
    shutil.rmtree(side, ignore_errors=True)
    try:
        subprocess.run(
            [sys.executable, "-m", "karaoke_engine.transcribe", str(source), str(side)],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(side, ignore_errors=True)
        raise ModelError(f"could not convert {spec.repo} (exit code {exc.returncode})") from exc
    side.replace(target)
    return target


class ModelError(RuntimeError):
    pass


def _available_memory_gb() -> float:
    try:
        for row in Path("/proc/meminfo").read_text().splitlines():
            if row.startswith("MemAvailable:"):
                return int(row.split()[1]) / 2**20
    except OSError:
        pass
    return float("inf")


def _download(spec: WhisperSpec) -> Path:
    from huggingface_hub import snapshot_download

    if spec.converted:
        return Path(snapshot_download(spec.repo, revision=spec.revision))
    # Weights and tokenizer only: some repos also carry multi-gigabyte optimizer states.
    patterns = ["*.json", "model*.safetensors", "pytorch_model*.bin", "*.txt"]
    return Path(snapshot_download(spec.repo, revision=spec.revision, allow_patterns=patterns))


def _convert(source: Path, target: Path) -> None:
    from ctranslate2.converters import TransformersConverter

    copy = [f for f in ("tokenizer.json", "preprocessor_config.json") if (source / f).is_file()]
    converter = TransformersConverter(
        str(source), copy_files=copy, load_as_float16=True, low_cpu_mem_usage=True
    )
    converter.convert(str(target), quantization="int8_float16", force=True)


def _voice_share(active: npt.NDArray[np.bool_], start: float, end: float) -> float:
    first, last = round(start / _HOP), max(round(end / _HOP), round(start / _HOP) + 1)
    span = active[first:last]
    return float(span.mean()) if len(span) else 0.0


def _is_loop(text: str) -> bool:
    words = text.lower().split()
    return len(words) >= _LOOP_WORDS and len(set(words)) <= 2


def _repeats(kept: list[TranscriptSegment], text: str) -> int:
    count = 0
    for segment in reversed(kept):
        if segment.text.lower() != text.lower():
            break
        count += 1
    return count


def _preload_cuda12() -> None:
    """CTranslate2 4.8 is built for CUDA 12 and torch ships CUDA 13: load cuBLAS 12 first."""
    for package, pattern in (
        ("nvidia.cublas", "libcublas*.so.12"),
        ("nvidia.cudnn", "libcudnn*.so.9"),
    ):
        spec = importlib.util.find_spec(package)
        if spec is None or not spec.submodule_search_locations:
            continue
        lib_dir = Path(next(iter(spec.submodule_search_locations))) / "lib"
        for lib in sorted(lib_dir.glob(pattern), key=lambda p: (len(p.name), p.name)):
            ctypes.CDLL(str(lib), mode=ctypes.RTLD_GLOBAL)


if __name__ == "__main__":
    _convert(Path(sys.argv[1]), Path(sys.argv[2]))
