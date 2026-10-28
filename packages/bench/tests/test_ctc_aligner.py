from pathlib import Path

import pytest

from karaoke_bench.baseline.ctc import DEFAULT_MODELS, CtcAligner
from karaoke_contracts import load_doc

DEMO = Path(__file__).resolve().parents[3] / "fixtures" / "packages" / "demo-sintetico"


def test_unknown_language_raises() -> None:
    with pytest.raises(ValueError, match="xx"):
        CtcAligner().align(Path("missing.wav"), ["ola"], "xx")


def test_default_models_are_pinned() -> None:
    assert set(DEFAULT_MODELS) == {"en", "es", "fr", "de", "pt", "gl"}
    assert all(len(revision) == 40 for _, revision in DEFAULT_MODELS.values())


@pytest.mark.usefixtures("ffmpeg")
def test_ctc_aligner_returns_one_line_per_lyric_line() -> None:
    torch = pytest.importorskip("torch")
    pytest.importorskip("transformers")
    if not torch.cuda.is_available():
        pytest.skip("needs a CUDA GPU")
    vocals = DEMO / "vocals.wav"
    if not vocals.is_file():
        pytest.skip("run `uv run karaoke demo fixtures/packages/demo-sintetico` first")
    doc = load_doc(DEMO / "karaoke.json")
    lyrics = [" ".join(word.text for word in line.words) for line in doc.lines]

    lines = CtcAligner().align(vocals, lyrics, "gl")

    assert len(lines) == len(lyrics)
    assert [len(line.words) for line in lines] == [len(text.split()) for text in lyrics]
    starts = [word.start for line in lines for word in line.words]
    assert starts == sorted(starts)
    assert lines[-1].end <= doc.duration + 0.1
