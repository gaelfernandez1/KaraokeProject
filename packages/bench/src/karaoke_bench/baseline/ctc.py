"""Baseline aligner: CTC forced alignment of whole songs with per-language wav2vec2 models.

The default models are the ones WhisperX picks per language (WhisperX itself pins torch 2.8,
which does not fit this workspace). Emissions are computed in overlapping windows so a 4-minute
song fits in 4 GB, then one Viterbi pass places every character of the lyrics.
"""

import gc
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from karaoke_bench.audio import SAMPLE_RATE, Samples, load_mono16k
from karaoke_bench.baseline.ctc_core import (
    LogProbs,
    Vocab,
    encode_words,
    forced_align,
    vocab_from_json,
    word_spans,
)
from karaoke_contracts import Line, Word

DEFAULT_MODELS: dict[str, tuple[str, str]] = {
    "en": ("facebook/wav2vec2-base-960h", "22aad52d435eb6dbaf354bdad9b0da84ce7d6156"),
    "es": (
        "jonatasgrosman/wav2vec2-large-xlsr-53-spanish",
        "96d7e9b4e4a78af515a3c6d3cee7c0826045d276",
    ),
    "fr": (
        "jonatasgrosman/wav2vec2-large-xlsr-53-french",
        "7c79e105a6525d38e1e69f640b974b4a679723cc",
    ),
    "de": (
        "jonatasgrosman/wav2vec2-large-xlsr-53-german",
        "4b8a02957378d0f2da2ef74091156b032c485a89",
    ),
    "pt": (
        "jonatasgrosman/wav2vec2-large-xlsr-53-portuguese",
        "634ac655299bcdc46c83bc01da9bab52d2987e4f",
    ),
    "gl": ("ifrz/wav2vec2-large-xlsr-galician", "70b3bfad73c9cec3b2c638c655bc6dc7ceef2c9e"),
}
_BLANKS = ("<pad>", "[PAD]")
_DELIMITERS = ("|", " ")


class CtcAligner:
    name = "ctc-wav2vec2"
    version = "1"

    def __init__(
        self,
        model: str | None = None,
        revision: str | None = None,
        window_seconds: float = 30.0,
        context_seconds: float = 2.0,
        device: str = "cuda",
        dtype: str = "float16",
    ) -> None:
        self.model = model
        self.revision = revision
        self.window_seconds = window_seconds
        self.context_seconds = context_seconds
        self.device = device
        self.dtype = dtype
        self._loaded: tuple[str, str | None] | None = None
        self._net: Any = None
        self._features: Any = None
        self._vocab: Vocab | None = None

    def align(self, vocals: Path, lyrics_lines: Sequence[str], language: str) -> list[Line]:
        repo, revision = self._model_for(language)
        self._load(repo, revision)
        assert self._vocab is not None
        audio = load_mono16k(vocals)
        log_probs = self._emissions(audio)
        frame_seconds = len(audio) / SAMPLE_RATE / log_probs.shape[0]

        line_words = [line.split() for line in lyrics_lines]
        flat = [word for words in line_words for word in words]
        tokens, owner = encode_words(flat, self._vocab)
        spans = forced_align(log_probs, tokens, self._vocab.blank)
        per_word = word_spans(spans, owner, len(flat))
        confidence = _confidences(log_probs, tokens, spans, owner, len(flat))
        times = _word_times(per_word, frame_seconds)

        lines, index = [], 0
        for i, words in enumerate(line_words):
            built = [
                Word(
                    text=text,
                    start=times[index + k][0],
                    end=times[index + k][1],
                    confidence=confidence[index + k],
                )
                for k, text in enumerate(words)
            ]
            index += len(words)
            lines.append(Line(id=f"l{i + 1}", start=built[0].start, end=built[-1].end, words=built))
        return lines

    def _model_for(self, language: str) -> tuple[str, str | None]:
        if self.model:
            return self.model, self.revision
        if language not in DEFAULT_MODELS:
            raise ValueError(f"no default alignment model for language '{language}'")
        return DEFAULT_MODELS[language]

    def _load(self, repo: str, revision: str | None) -> None:
        if self._loaded == (repo, revision):
            return
        import torch
        from huggingface_hub import hf_hub_download
        from transformers import AutoFeatureExtractor, AutoModelForCTC

        self._net = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        dtype = getattr(torch, self.dtype) if self.device != "cpu" else torch.float32
        self._features = AutoFeatureExtractor.from_pretrained(repo, revision=revision)  # type: ignore[no-untyped-call]
        net = AutoModelForCTC.from_pretrained(repo, revision=revision, dtype=dtype)
        self._net = net.to(self.device).eval()
        vocab_path = hf_hub_download(repo, "vocab.json", revision=revision)
        mapping: dict[str, int] = json.loads(Path(vocab_path).read_text(encoding="utf-8"))
        blank = next(token for token in _BLANKS if token in mapping)
        delimiter = next((token for token in _DELIMITERS if token in mapping), None)
        self._vocab = vocab_from_json(mapping, blank, delimiter)
        self._loaded = (repo, revision)

    def _emissions(self, audio: Samples) -> LogProbs:
        """Log-probabilities per frame, computed window by window with some context."""
        import torch

        window = round(self.window_seconds * SAMPLE_RATE)
        context = round(self.context_seconds * SAMPLE_RATE)
        parts = []
        for start in range(0, len(audio), window):
            stop = min(start + window, len(audio))
            left, right = max(0, start - context), min(len(audio), stop + context)
            inputs = self._features(
                audio[left:right], sampling_rate=SAMPLE_RATE, return_tensors="pt"
            ).input_values.to(self.device, dtype=self._net.dtype)
            with torch.inference_mode():
                logits = self._net(inputs).logits[0].float()
            per_sample = logits.shape[0] / (right - left)
            first = round((start - left) * per_sample)
            last = round((stop - left) * per_sample)
            parts.append(logits[first:last].log_softmax(dim=-1).cpu().numpy())
        return np.concatenate(parts)


def _word_times(
    spans: Sequence[tuple[int, int] | None], frame_seconds: float
) -> list[tuple[float, float]]:
    """Seconds per word; words without tokens get zero length next to their neighbour."""
    times: list[tuple[float, float] | None] = [
        None if span is None else (span[0] * frame_seconds, (span[1] + 1) * frame_seconds)
        for span in spans
    ]
    resolved: list[tuple[float, float]] = []
    for i, time in enumerate(times):
        if time is not None:
            resolved.append(time)
            continue
        if resolved:
            point = resolved[-1][1]
        else:
            point = next((t[0] for t in times[i + 1 :] if t is not None), 0.0)
        resolved.append((point, point))
    return resolved


def _confidences(
    log_probs: LogProbs,
    tokens: Sequence[int],
    spans: Sequence[tuple[int, int]],
    owner: Sequence[int],
    n_words: int,
) -> list[float | None]:
    totals = [0.0] * n_words
    counts = [0] * n_words
    for token, (first, last), word in zip(tokens, spans, owner, strict=True):
        if word < 0:
            continue
        totals[word] += float(log_probs[first : last + 1, token].sum())
        counts[word] += last - first + 1
    return [
        round(float(np.exp(total / count)), 3) if count else None
        for total, count in zip(totals, counts, strict=True)
    ]
