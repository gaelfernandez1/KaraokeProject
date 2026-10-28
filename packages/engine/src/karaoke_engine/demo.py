"""Synthetic audio for a karaoke package, generated from its own timings.

The "vocals" track beeps exactly while each part (or word) is sung and stays silent elsewhere,
so anyone can hear whether a player or an export keeps the lyrics in sync. Stdlib only.
"""

import math
import wave
from array import array
from pathlib import Path

from karaoke_contracts import KaraokeDoc, load_doc, resolve_media

SAMPLE_RATE = 22_050
_FADE_SECONDS = 0.01
# A major pentatonic, so consecutive beeps sound like a tune rather than one long note.
_SCALE_HZ = (440.0, 493.88, 554.37, 659.25, 739.99)
_PAD_HZ = (220.0, 277.18, 329.63)


def synthesize_package_audio(package_dir: Path) -> None:
    doc = load_doc(package_dir / "karaoke.json")
    # Resolve every target before writing anything, so a bad reference leaves no half-done package.
    instrumental = _media_path(package_dir, doc.audio.instrumental)
    vocals = _media_path(package_dir, doc.audio.vocals) if doc.audio.vocals else None
    total = round(doc.duration * SAMPLE_RATE)
    _write_wav(instrumental, _pad(total))
    if vocals is not None:
        _write_wav(vocals, _beeps(doc, total))


def _media_path(package_dir: Path, ref: str) -> Path:
    target = resolve_media(package_dir, ref)
    if target.suffix != ".wav":
        raise ValueError(f"demo audio must be .wav files, got {ref!r}")
    return target


def _pad(total: int) -> array[int]:
    samples = array("h", bytes(2 * total))
    for i in range(total):
        t = i / SAMPLE_RATE
        swell = 0.75 + 0.25 * math.sin(2 * math.pi * 0.25 * t)
        value = sum(math.sin(2 * math.pi * hz * t) for hz in _PAD_HZ) / len(_PAD_HZ)
        samples[i] = int(6000 * swell * value)
    return samples


def _beeps(doc: KaraokeDoc, total: int) -> array[int]:
    samples = array("h", bytes(2 * total))
    spans: list[tuple[float, float]] = []
    for line in doc.lines:
        for word in line.words:
            if word.parts:
                spans.extend((part.start, part.end) for part in word.parts)
            else:
                spans.append((word.start, word.end))
    for n, (start, end) in enumerate(spans):
        hz = _SCALE_HZ[n % len(_SCALE_HZ)]
        first, last = round(start * SAMPLE_RATE), min(round(end * SAMPLE_RATE), total)
        length = last - first
        fade = max(1, min(round(_FADE_SECONDS * SAMPLE_RATE), length // 2))
        for k in range(length):
            envelope = min(1.0, k / fade, (length - 1 - k) / fade)
            samples[first + k] = int(
                12000 * envelope * math.sin(2 * math.pi * hz * k / SAMPLE_RATE)
            )
    return samples


def _write_wav(path: Path, samples: array[int]) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(samples.tobytes())
