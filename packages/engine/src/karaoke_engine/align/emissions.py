"""CTC emissions of the vocals: per-frame log-probabilities of the letters the lyrics use.

Only the columns the lyrics need leave the GPU (plus the blank and the best other letter), so a
model with ten thousand symbols costs no more memory than one with forty.
"""

import contextlib
import json
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from karaoke_engine.align.audio import SAMPLE_RATE
from karaoke_engine.align.ctc import ANY, BLANK
from karaoke_engine.align.models import CtcModelSpec

_DELIMITERS = ("|", " ")


@dataclass(frozen=True)
class Vocab:
    ids: dict[str, int]
    blank: int
    delimiter: int | None
    upper: bool
    fallbacks: dict[str, str]

    @classmethod
    def from_mapping(
        cls, mapping: dict[str, int], blank: int, fallbacks: dict[str, str]
    ) -> "Vocab":
        letters = [token for token in mapping if len(token) == 1 and token.isalpha()]
        delimiter = next((mapping[d] for d in _DELIMITERS if d in mapping), None)
        upper = bool(letters) and not any(token.islower() for token in letters)
        return cls(dict(mapping), blank, delimiter, upper, dict(fallbacks))

    def encode(self, word: str) -> tuple[int, ...]:
        """Ids of a word's letters: the letter, its fallback, its base letter, or nothing."""
        ids = []
        for ch in word:
            token = self._token(ch)
            if token is not None:
                ids.append(token)
        return tuple(ids)

    def _token(self, ch: str) -> int | None:
        for candidate in (ch, self.fallbacks.get(ch.lower(), ""), _base(ch)):
            if not candidate:
                continue
            cased = candidate.upper() if self.upper else candidate.lower()
            if cased in self.ids and self.ids[cased] not in (self.blank, self.delimiter):
                return self.ids[cased]
        return None


@dataclass(frozen=True)
class Emissions:
    log_probs: npt.NDArray[np.float32]  # (frames, 2 + ids): blank, best other, then the ids
    frame_seconds: float


def compact(
    log_probs: npt.NDArray[np.floating], blank: int, ids: Sequence[int]
) -> npt.NDArray[np.float32]:
    """Blank, best non-blank and the requested columns, in the layout align_segments reads."""
    others = log_probs.copy()
    others[:, blank] = -np.inf
    out = np.empty((log_probs.shape[0], 2 + len(ids)), dtype=np.float32)
    out[:, BLANK] = log_probs[:, blank]
    out[:, ANY] = others.max(axis=1)
    out[:, 2:] = log_probs[:, list(ids)]
    return out


def compact_tensor(log_probs: Any, blank: int, ids: Sequence[int]) -> npt.NDArray[np.float32]:
    """compact() on a torch tensor, so only the needed columns leave the GPU."""
    import torch

    others = log_probs.clone()
    others[:, blank] = -torch.inf
    columns = [log_probs[:, blank : blank + 1], others.max(dim=1, keepdim=True).values]
    if ids:
        columns.append(log_probs[:, list(ids)])
    out: npt.NDArray[np.float32] = torch.cat(columns, dim=1).float().cpu().numpy()
    return out


class EmissionModel:
    def __init__(
        self,
        spec: CtcModelSpec,
        device: str = "cuda",
        dtype: str = "float16",
        window_seconds: float = 30.0,
        context_seconds: float = 2.0,
    ) -> None:
        self.spec = spec
        self.device = device
        self.dtype = dtype
        self.window_seconds = window_seconds
        self.context_seconds = context_seconds
        self._net: Any = None
        self._features: Any = None
        self._vocab: Vocab | None = None

    @property
    def vocab(self) -> Vocab:
        if self._vocab is None:
            raise RuntimeError("load() the model first")
        return self._vocab

    def load(self) -> None:
        import torch
        from huggingface_hub import hf_hub_download
        from transformers import AutoFeatureExtractor, AutoModelForCTC

        repo, revision = self.spec.repo, self.spec.revision
        dtype = torch.float16 if self.device != "cpu" and self.dtype == "float16" else torch.float32
        self._features = AutoFeatureExtractor.from_pretrained(repo, revision=revision)  # type: ignore[no-untyped-call]
        net = AutoModelForCTC.from_pretrained(repo, revision=revision, dtype=dtype)
        self._net = net.to(self.device).eval()
        mapping = json.loads(
            Path(hf_hub_download(repo, "vocab.json", revision=revision)).read_text(encoding="utf-8")
        )
        self._vocab = Vocab.from_mapping(mapping, net.config.pad_token_id, self.spec.fallbacks)

    def emissions(self, samples: npt.NDArray[np.float32], ids: Sequence[int]) -> Emissions:
        """Compact emissions computed window by window, with context on both sides."""
        import torch

        if self._net is None:
            self.load()
        blank = self.vocab.blank
        window = round(self.window_seconds * SAMPLE_RATE)
        context = round(self.context_seconds * SAMPLE_RATE)
        parts = []
        for start in range(0, len(samples), window):
            stop = min(start + window, len(samples))
            left, right = max(0, start - context), min(len(samples), stop + context)
            inputs = self._features(
                samples[left:right], sampling_rate=SAMPLE_RATE, return_tensors="pt"
            )
            inputs = {
                key: value.to(self.device, dtype=self._net.dtype)
                if value.is_floating_point()
                else value.to(self.device)
                for key, value in inputs.items()
            }
            with torch.inference_mode():
                logits = self._net(**inputs).logits[0].float()
            per_sample = logits.shape[0] / (right - left)
            first = round((start - left) * per_sample)
            last = round((stop - left) * per_sample)
            parts.append(compact_tensor(logits[first:last].log_softmax(dim=-1), blank, ids))
        log_probs = np.concatenate(parts) if parts else np.zeros((0, 2 + len(ids)), np.float32)
        frame_seconds = len(samples) / SAMPLE_RATE / max(log_probs.shape[0], 1)
        return Emissions(log_probs, frame_seconds)

    def unload(self) -> None:
        """Frees the model, on the GPU and in RAM, before another one loads."""
        import gc

        self._net = None
        self._features = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        _give_memory_back()


def _give_memory_back() -> None:
    """Returns freed heap to the system (glibc keeps it otherwise), so models do not pile up."""
    import ctypes
    import ctypes.util

    name = ctypes.util.find_library("c")
    if name:
        with contextlib.suppress(OSError, AttributeError):
            ctypes.CDLL(name).malloc_trim(0)


def _base(ch: str) -> str:
    base = "".join(c for c in unicodedata.normalize("NFD", ch) if not unicodedata.combining(c))
    return base if len(base) == 1 else ""
