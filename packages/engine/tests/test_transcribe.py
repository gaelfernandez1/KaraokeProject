import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from karaoke_engine.steps import Transcriber
from karaoke_engine.transcribe import MODELS, WhisperTranscriber

RATE = 16000


@dataclass
class FakeSegment:
    start: float
    end: float
    text: str


@dataclass
class FakeInfo:
    language: str


class FakeWhisper:
    def __init__(self, segments: list[FakeSegment], language: str = "pt") -> None:
        self.segments = segments
        self.language = language
        self.calls: list[dict[str, object]] = []

    def transcribe(self, audio: np.ndarray, **options: object) -> tuple[object, FakeInfo]:
        self.calls.append(options)
        return iter(self.segments), FakeInfo(self.language)


def _vocals(tmp_path: Path, voiced: list[tuple[float, float]], seconds: float = 8.0) -> Path:
    samples = np.zeros(round(seconds * RATE), dtype=np.float32)
    t = np.arange(len(samples)) / RATE
    for start, end in voiced:
        inside = (t >= start) & (t < end)
        samples[inside] = 0.5 * np.sin(2 * np.pi * 220 * t[inside])
    path = tmp_path / "vocals.wav"
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((samples * 32767).astype("<i2").tobytes())
    return path


def _transcribe(tmp_path: Path, segments: list[FakeSegment], voiced: list[tuple[float, float]]):  # type: ignore[no-untyped-def]
    whisper = FakeWhisper(segments)
    transcriber = WhisperTranscriber(whisper=whisper)
    return transcriber.transcribe(_vocals(tmp_path, voiced), "gl"), whisper


@pytest.mark.usefixtures("ffmpeg")
def test_transcriber_keeps_the_requested_language(tmp_path: Path) -> None:
    transcript, whisper = _transcribe(tmp_path, [FakeSegment(0.5, 1.5, " Ola mar ")], [(0, 2)])

    assert transcript.language == "gl"
    assert [s.text for s in transcript.segments] == ["Ola mar"]
    assert whisper.calls[0]["language"] == "gl"
    assert whisper.calls[0]["condition_on_previous_text"] is False


@pytest.mark.usefixtures("ffmpeg")
def test_transcriber_drops_segments_without_voice(tmp_path: Path) -> None:
    segments = [FakeSegment(0.5, 1.5, "Ola mar"), FakeSegment(4.0, 6.0, "Grazas por ver o vídeo")]

    transcript, _ = _transcribe(tmp_path, segments, [(0, 2)])

    assert [s.text for s in transcript.segments] == ["Ola mar"]


@pytest.mark.usefixtures("ffmpeg")
def test_transcriber_drops_looping_repeats(tmp_path: Path) -> None:
    segments = [
        FakeSegment(0.0, 1.0, "vai o vento"),
        FakeSegment(1.0, 2.0, "la la la la la la la la la la la la"),
        *(FakeSegment(2.0 + i, 3.0 + i, "e ti que fas") for i in range(5)),
    ]

    transcript, _ = _transcribe(tmp_path, segments, [(0, 8)])

    assert [s.text for s in transcript.segments] == ["vai o vento", "e ti que fas", "e ti que fas"]


def test_transcriber_is_a_transcriber() -> None:
    assert isinstance(WhisperTranscriber(), Transcriber)


def test_models_are_pinned() -> None:
    assert {"large-v3-turbo", "nos-turbo-gl", "hitz-large-v3-gl", "bsc-los"} <= set(MODELS)
    assert all(len(spec.revision) == 40 for spec in MODELS.values())


def test_segmenter_cuts_on_punctuation_and_length() -> None:
    from karaoke_engine.steps import Transcript, TranscriptSegment
    from karaoke_engine.transcribe import LineSegmenter

    long = " ".join(f"p{i}" for i in range(12))
    transcript = Transcript(
        language="gl",
        segments=(
            TranscriptSegment(0.0, 3.0, "Ola, mar. Vai o vento!"),
            TranscriptSegment(3.0, 9.0, long),
        ),
    )

    lines = LineSegmenter().segment(transcript)

    assert lines == ["Ola, mar.", "Vai o vento!", " ".join(f"p{i}" for i in range(6)),
                     " ".join(f"p{i}" for i in range(6, 12))]  # fmt: skip


def test_galician_defaults_to_the_galician_model() -> None:
    assert WhisperTranscriber().model_for_language("gl").startswith("HiTZ/whisper-large-v3-gl@")
    assert (
        WhisperTranscriber()
        .model_for_language("es")
        .startswith("dropbox-dash/faster-whisper-large-v3-turbo@")
    )


def test_conversion_runs_in_its_own_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import karaoke_engine.transcribe as transcribe

    ran: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> None:
        ran.append(command)
        (Path(command[-1]) / "model.bin").parent.mkdir(parents=True, exist_ok=True)
        (Path(command[-1]) / "model.bin").write_bytes(b"x")

    monkeypatch.setattr(transcribe, "CACHE", tmp_path)
    monkeypatch.setattr(transcribe.subprocess, "run", fake_run)
    monkeypatch.setattr(transcribe, "_download", lambda spec: tmp_path / "hf")

    target = transcribe.prepare("hitz-large-v3-gl")

    assert (target / "model.bin").is_file()
    assert ran[0][1:3] == ["-m", "karaoke_engine.transcribe"]
    assert transcribe.prepare("hitz-large-v3-gl") == target
    assert len(ran) == 1
