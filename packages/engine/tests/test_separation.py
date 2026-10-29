import shutil
from pathlib import Path
from typing import ClassVar

import pytest

from karaoke_engine.separation import DEFAULT_MODEL_DIR, RoformerSeparator, stem_roles
from karaoke_engine.steps import Separator

DEMO = Path(__file__).resolve().parents[3] / "fixtures" / "packages" / "demo-sintetico"


def test_vocals_stem_becomes_vocals_whichever_comes_first() -> None:
    expected = {"Vocals": "vocals", "Instrumental": "instrumental"}

    assert stem_roles("Vocals", "Instrumental", "Vocals") == expected
    assert stem_roles("Instrumental", "Vocals", "Vocals") == expected


def test_stem_names_compare_without_case() -> None:
    assert stem_roles("vocals", "other", "Vocals") == {"vocals": "vocals", "other": "instrumental"}


def test_karaoke_models_can_name_their_lead_stem() -> None:
    roles = stem_roles("Karaoke", "Instrumental", "karaoke")

    assert roles == {"Karaoke": "vocals", "Instrumental": "instrumental"}


def test_unknown_vocals_stem_is_rejected() -> None:
    with pytest.raises(ValueError, match="Drums, Bass"):
        stem_roles("Drums", "Bass", "Vocals")


def test_roformer_separator_is_a_separator() -> None:
    separator = RoformerSeparator(model="vocals_mel_band_roformer.ckpt")

    assert isinstance(separator, Separator)
    assert separator.version


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_roformer_separator_writes_two_stems(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("needs a CUDA GPU")
    model = "vocals_mel_band_roformer.ckpt"
    if not (DEFAULT_MODEL_DIR / model).is_file():
        pytest.skip(f"download {model} first (any bench run with a sep-* pipeline does it)")
    mix = DEMO / "vocals.wav"
    if not mix.is_file():
        pytest.skip("run `uv run karaoke demo fixtures/packages/demo-sintetico` first")
    separator = RoformerSeparator(model=model)
    separator.load()

    stems = separator.separate(mix, tmp_path)

    assert stems.vocals == tmp_path / "vocals.wav"
    assert stems.instrumental == tmp_path / "instrumental.wav"
    assert stems.vocals.stat().st_size > 1000
    assert stems.instrumental.stat().st_size > 1000


class _FakeSeparator:
    """Stands in for audio_separator's Separator and keeps the arguments it got."""

    calls: ClassVar[list[dict[str, object]]] = []

    def __init__(self, **kwargs: object) -> None:
        _FakeSeparator.calls.append(kwargs)

    def load_model(self, model_filename: str) -> None:
        pass


def _loaded_params(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, **params: object) -> object:
    import sys
    import types

    module = types.ModuleType("audio_separator.separator")
    module.Separator = _FakeSeparator  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "audio_separator", types.ModuleType("audio_separator"))
    monkeypatch.setitem(sys.modules, "audio_separator.separator", module)
    _FakeSeparator.calls = []
    RoformerSeparator(model="m.ckpt", model_dir=str(tmp_path), **params).load()  # type: ignore[arg-type]
    return _FakeSeparator.calls[-1]["mdxc_params"]


def test_model_chunk_length_is_kept_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    params = _loaded_params(monkeypatch, tmp_path)

    assert params["override_model_segment_size"] is False  # type: ignore[index]


def test_a_segment_size_overrides_the_model_chunk_length(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    params = _loaded_params(monkeypatch, tmp_path, segment_size=551)

    assert params["override_model_segment_size"] is True  # type: ignore[index]
    assert params["segment_size"] == 551  # type: ignore[index]
