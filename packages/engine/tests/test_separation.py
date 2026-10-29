import shutil
from pathlib import Path

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
