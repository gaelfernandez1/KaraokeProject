import wave
from pathlib import Path

from karaoke_contracts import load_doc, validate_package
from karaoke_engine.demo import SAMPLE_RATE, synthesize_package_audio


def peak_at(path: Path, seconds: float, window: float = 0.02) -> int:
    with wave.open(str(path)) as wav:
        wav.setpos(int(seconds * wav.getframerate()))
        frames = wav.readframes(int(window * wav.getframerate()))
    samples = memoryview(frames).cast("h")
    return max(abs(s) for s in samples)


def test_synthesized_package_validates(bare_package: Path) -> None:
    synthesize_package_audio(bare_package)

    assert validate_package(bare_package) == []


def test_audio_matches_document_duration(bare_package: Path) -> None:
    synthesize_package_audio(bare_package)
    doc = load_doc(bare_package / "karaoke.json")

    for name in ("instrumental.wav", "vocals.wav"):
        with wave.open(str(bare_package / name)) as wav:
            assert wav.getframerate() == SAMPLE_RATE
            assert wav.getnchannels() == 1
            assert abs(wav.getnframes() / SAMPLE_RATE - doc.duration) <= 0.05


def test_vocals_sound_only_inside_sung_parts(bare_package: Path) -> None:
    synthesize_package_audio(bare_package)
    vocals = bare_package / "vocals.wav"

    assert peak_at(vocals, 4.10) > 3000  # middle of "O" in "Ola,"
    assert peak_at(vocals, 19.0) == 0  # instrumental gap before the last line
    assert peak_at(bare_package / "instrumental.wav", 19.0) > 0
