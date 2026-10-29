"""Baseline transcriber: faster-whisper (CTranslate2), as in the v2 system.

CTranslate2 4.8 is built for CUDA 12 while torch here ships CUDA 13, so the CUDA 12 cuBLAS
(from the nvidia-cublas-cu12 wheel) is preloaded before importing it; cuDNN 9 from torch's
wheel works for both. This only happens in the transcriber's own process.
"""

import ctypes
import importlib.util
from pathlib import Path
from typing import Any

from karaoke_bench.audio import load_mono16k
from karaoke_engine.steps import Transcript, TranscriptSegment

MODELS: dict[str, tuple[str, str]] = {
    "small": ("Systran/faster-whisper-small", "536b0662742c02347bc0e980a01041f333bce120"),
    "large-v3-turbo": (
        "dropbox-dash/faster-whisper-large-v3-turbo",
        "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf",
    ),
}


class FasterWhisperTranscriber:
    name = "faster-whisper"
    version = "1"

    def __init__(
        self,
        model: str = "large-v3-turbo",
        detect_language: bool = False,
        compute_type: str = "int8_float16",
        device: str = "cuda",
        beam_size: int = 5,
    ) -> None:
        if model not in MODELS:
            raise ValueError(f"unknown Whisper model '{model}' (use {', '.join(MODELS)})")
        self.model = model
        self.detect_language = detect_language
        self.compute_type = compute_type
        self.device = device
        self.beam_size = beam_size
        self._whisper: Any = None

    def load(self) -> None:
        if self.device == "cuda":
            _preload_cuda12()
        from faster_whisper import WhisperModel
        from huggingface_hub import snapshot_download

        repo, revision = MODELS[self.model]
        path = snapshot_download(repo, revision=revision)
        self._whisper = WhisperModel(path, device=self.device, compute_type=self.compute_type)

    def transcribe(self, vocals: Path, language: str) -> Transcript:
        if self._whisper is None:
            self.load()
        # Decoded with ffmpeg: faster-whisper 1.2.1 cannot open files with PyAV 19.
        segments, info = self._whisper.transcribe(
            load_mono16k(vocals),
            language=None if self.detect_language else language,
            beam_size=self.beam_size,
        )
        found = tuple(TranscriptSegment(s.start, s.end, s.text.strip()) for s in segments)
        return Transcript(language=info.language, segments=found)


def _preload_cuda12() -> None:
    for package, pattern in (
        ("nvidia.cublas", "libcublas*.so.12"),
        ("nvidia.cudnn", "libcudnn*.so.9"),
    ):
        spec = importlib.util.find_spec(package)
        if spec is None or not spec.submodule_search_locations:
            continue
        lib_dir = Path(next(iter(spec.submodule_search_locations))) / "lib"
        # Shortest name first: each core library before its companions.
        for lib in sorted(lib_dir.glob(pattern), key=lambda p: (len(p.name), p.name)):
            ctypes.CDLL(str(lib), mode=ctypes.RTLD_GLOBAL)
