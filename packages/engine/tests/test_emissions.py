from pathlib import Path

import numpy as np
import pytest

from karaoke_engine.align.emissions import Vocab, compact
from karaoke_engine.align.models import DEFAULT_BY_LANGUAGE, FALLBACK_MODEL, MODELS

DEMO = Path(__file__).resolve().parents[3] / "fixtures" / "packages" / "demo-sintetico"
LETTERS = {ch: i + 2 for i, ch in enumerate("abcdeglmnorsxz")}


def _vocab(fallbacks: dict[str, str] | None = None) -> Vocab:
    mapping = {"<pad>": 0, "|": 1, **LETTERS}
    return Vocab.from_mapping(mapping, blank=0, fallbacks=fallbacks or {})


def test_vocab_uses_fallback_before_base_letter() -> None:
    ids = _vocab({"j": "x"}).encode("janela")

    assert ids[0] == LETTERS["x"]
    assert len(ids) == 6


def test_vocab_falls_back_to_the_base_letter() -> None:
    assert _vocab().encode("ç") == (LETTERS["c"],)
    assert _vocab().encode("é") == (LETTERS["e"],)


def test_vocab_drops_what_it_cannot_spell() -> None:
    assert _vocab().encode("ola!'") == (LETTERS["o"], LETTERS["l"], LETTERS["a"])
    assert _vocab().encode("q") == ()


def test_blank_and_delimiter_come_from_the_mapping() -> None:
    vocab = Vocab.from_mapping({"[PAD]": 5, " ": 0, "a": 1}, blank=5, fallbacks={})

    assert vocab.blank == 5
    assert vocab.delimiter == 0


def test_uppercase_vocabularies_are_matched() -> None:
    vocab = Vocab.from_mapping({"<pad>": 0, "|": 1, "A": 2, "B": 3}, blank=0, fallbacks={})

    assert vocab.encode("ab") == (2, 3)


def test_compact_keeps_blank_and_any_columns() -> None:
    lp = np.log(np.array([[0.6, 0.1, 0.3], [0.2, 0.7, 0.1]], dtype=np.float32))

    out = compact(lp, blank=0, ids=[2])

    assert out.shape == (2, 3)
    np.testing.assert_allclose(out[:, 0], lp[:, 0])
    np.testing.assert_allclose(out[:, 1], [np.log(0.3), np.log(0.7)], rtol=1e-6)
    np.testing.assert_allclose(out[:, 2], lp[:, 2])


def test_every_language_has_a_pinned_model() -> None:
    assert {"gl", "es", "pt", "en", "fr", "de"} <= set(DEFAULT_BY_LANGUAGE)
    assert FALLBACK_MODEL in MODELS
    for spec in MODELS.values():
        assert len(spec.revision) == 40


@pytest.mark.usefixtures("ffmpeg")
def test_emissions_cover_the_audio() -> None:
    torch = pytest.importorskip("torch")
    pytest.importorskip("transformers")
    if not torch.cuda.is_available():
        pytest.skip("needs a CUDA GPU")
    vocals = DEMO / "vocals.wav"
    if not vocals.is_file():
        pytest.skip("run `uv run karaoke demo fixtures/packages/demo-sintetico` first")
    from karaoke_engine.align.audio import load_mono16k
    from karaoke_engine.align.emissions import EmissionModel

    samples = load_mono16k(vocals)
    model = EmissionModel(MODELS["nos-xlsr-300m-gl"])
    model.load()
    ids = model.vocab.encode("ola")

    emissions = model.emissions(samples, ids)

    seconds = emissions.log_probs.shape[0] * emissions.frame_seconds
    assert seconds == pytest.approx(len(samples) / 16000, abs=0.05)
    assert emissions.log_probs.shape[1] == 2 + len(ids)


def test_compact_tensor_matches_compact() -> None:
    torch = pytest.importorskip("torch")
    from karaoke_engine.align.emissions import compact_tensor

    rng = np.random.default_rng(0)
    logits = torch.from_numpy(rng.normal(size=(50, 12)).astype(np.float32))
    log_probs = logits.log_softmax(dim=-1)

    out = compact_tensor(log_probs, blank=3, ids=[5, 0, 11])

    np.testing.assert_allclose(out, compact(log_probs.numpy(), blank=3, ids=[5, 0, 11]), rtol=1e-6)


def test_unload_drops_the_model_and_features() -> None:
    from karaoke_engine.align.emissions import EmissionModel

    model = EmissionModel(MODELS["nos-xlsr-300m-gl"])
    model._net, model._features = object(), object()

    model.unload()

    assert model._net is None
    assert model._features is None
