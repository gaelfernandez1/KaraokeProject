"""Baseline separator: Demucs htdemucs, the model the v2 system used."""

import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from karaoke_bench.audio import AudioError, write_wav
from karaoke_engine.steps import Stems


class DemucsSeparator:
    name = "demucs"
    version = "1"

    def __init__(
        self,
        model: str = "htdemucs",
        device: str = "cuda",
        segment: float | None = None,
        overlap: float = 0.25,
    ) -> None:
        self.model = model
        self.device = device
        self.segment = segment
        self.overlap = overlap
        self._net: Any = None

    def load(self) -> None:
        from demucs.pretrained import get_model

        self._net = get_model(self.model).eval().to(self.device)

    def separate(self, audio: Path, work_dir: Path) -> Stems:
        import torch
        from demucs.apply import apply_model

        if self._net is None:
            self.load()
        rate = int(self._net.samplerate)
        mix = torch.from_numpy(_decode_stereo(audio, rate))
        reference = mix.mean(0)
        mean, std = reference.mean(), reference.std() + 1e-8
        with torch.inference_mode():
            separated = apply_model(
                self._net,
                ((mix - mean) / std)[None].to(self.device),
                device=self.device,
                segment=self.segment,
                overlap=self.overlap,
                split=True,
                progress=False,
            )[0]
        sources = (separated * std + mean).cpu().numpy()
        vocals_index = list(self._net.sources).index("vocals")
        vocals = sources[vocals_index]
        others = np.delete(sources, vocals_index, axis=0).sum(axis=0)
        return Stems(
            vocals=write_wav(work_dir / "vocals.wav", vocals, rate),
            instrumental=write_wav(work_dir / "instrumental.wav", others, rate),
        )


def _decode_stereo(path: Path, rate: int) -> np.ndarray:
    command = ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2",
               "-ar", str(rate), "pipe:1"]  # fmt: skip
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        raise AudioError(path, result.stderr.decode(errors="replace"))
    return np.frombuffer(result.stdout, dtype=np.float32).reshape(-1, 2).T.copy()
