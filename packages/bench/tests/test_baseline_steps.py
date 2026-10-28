from pathlib import Path

import pytest

from karaoke_bench.audio import duration
from karaoke_bench.baseline.separation import DemucsSeparator
from karaoke_bench.baseline.whisper import FasterWhisperTranscriber

REPO = Path(__file__).resolve().parents[3]
DEMO = REPO / "fixtures" / "packages" / "demo-sintetico"


def _needs_gpu() -> None:
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("needs a CUDA GPU")


def test_unknown_whisper_model_rejected() -> None:
    with pytest.raises(ValueError, match="tiny-x"):
        FasterWhisperTranscriber(model="tiny-x")


@pytest.mark.usefixtures("ffmpeg")
def test_demucs_separator_writes_two_stems(tmp_path: Path) -> None:
    _needs_gpu()
    pytest.importorskip("demucs")
    mix = DEMO / "instrumental.wav"
    if not mix.is_file():
        pytest.skip("run `uv run karaoke demo fixtures/packages/demo-sintetico` first")
    separator = DemucsSeparator()
    separator.load()

    stems = separator.separate(mix, tmp_path)

    assert stems.vocals == tmp_path / "vocals.wav"
    assert stems.instrumental == tmp_path / "instrumental.wav"
    assert duration(stems.vocals) == pytest.approx(duration(mix), abs=0.05)
    assert duration(stems.instrumental) == pytest.approx(duration(mix), abs=0.05)


@pytest.mark.usefixtures("ffmpeg")
def test_whisper_reports_language(tmp_path: Path) -> None:
    _needs_gpu()
    pytest.importorskip("faster_whisper")
    song = REPO / "bench" / "data" / "jamendo" / "Baila_-_Alfonso_Lugo" / "audio.mp3"
    if not song.is_file():
        pytest.skip("run `uv run karaoke-bench fetch --set jamendo` first")
    from karaoke_bench.audio import cut

    clip = cut(song, 30.0, 45.0, tmp_path / "clip.wav")
    transcriber = FasterWhisperTranscriber(model="small", detect_language=True)
    transcriber.load()

    transcript = transcriber.transcribe(clip, "gl")

    assert transcript.language == "es"
    assert transcript.segments
