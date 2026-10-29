"""Vocal separation with RoFormer models through audio-separator.

One model, one pass: a vocals model gives the vocals and everything else; a karaoke model gives
the lead vocals and leaves the backing vocals in the instrumental, which is what a karaoke track
wants. Which one is best is decided with the bench, not here.
"""

from pathlib import Path
from typing import Any

from karaoke_engine.audio import decode
from karaoke_engine.steps import Stems

DEFAULT_MODEL_DIR = Path.home() / ".cache" / "karaoke" / "models" / "audio-separator"
_LIBSNDFILE_FORMATS = {".wav", ".flac"}


def stem_roles(primary: str, secondary: str, vocals_stem: str) -> dict[str, str]:
    """Maps a model's two stem names to "vocals" and "instrumental"."""
    if primary.lower() == vocals_stem.lower():
        return {primary: "vocals", secondary: "instrumental"}
    if secondary.lower() == vocals_stem.lower():
        return {secondary: "vocals", primary: "instrumental"}
    raise ValueError(f"model stems are {primary}, {secondary}; none is {vocals_stem!r}")


class RoformerSeparator:
    name = "roformer"
    # Bumped when a default changes too: defaults are not part of the bench cache key.
    version = "2"

    def __init__(
        self,
        model: str,
        vocals_stem: str = "Vocals",
        model_dir: str | None = None,
        # STFT frames per chunk; None keeps the model's own (8 s for most RoFormers). Shorter
        # chunks need less VRAM.
        segment_size: int | None = None,
        # Overlapping passes per chunk. With 8, audio-separator's default, a 4 min song took over
        # 3 min on the laptop GPU; 2 is the usual trade-off (the models ship with 1 to 8).
        overlap: int = 2,
        batch_size: int = 1,
        autocast: bool = True,
    ) -> None:
        self.model = model
        self.vocals_stem = vocals_stem
        self.model_dir = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
        self.segment_size = segment_size
        self.overlap = overlap
        self.batch_size = batch_size
        self.autocast = autocast
        self._separator: Any = None

    def load(self) -> None:
        import logging

        from audio_separator.separator import Separator

        self.model_dir.mkdir(parents=True, exist_ok=True)
        separator = Separator(
            log_level=logging.WARNING,
            model_file_dir=str(self.model_dir),
            output_format="WAV",
            # Only scale a stem down if it would clip: both stems must keep the mix's balance.
            normalization_threshold=1.0,
            use_autocast=self.autocast,
            mdxc_params={
                "segment_size": self.segment_size or 256,
                "override_model_segment_size": self.segment_size is not None,
                "batch_size": self.batch_size,
                "overlap": self.overlap,
                "pitch_shift": 0,
            },
        )
        separator.load_model(model_filename=self.model)
        self._separator = separator

    def separate(self, audio: Path, work_dir: Path) -> Stems:
        if self._separator is None:
            self.load()
        separator = self._separator
        instance = separator.model_instance
        roles = stem_roles(instance.primary_stem_name, instance.secondary_stem_name,
                           self.vocals_stem)  # fmt: skip
        work_dir.mkdir(parents=True, exist_ok=True)
        # audio-separator reads through libsndfile, which cannot open AAC (YouTube's .m4a).
        if audio.suffix.lower() not in _LIBSNDFILE_FORMATS:
            audio = decode(audio, work_dir / "input.wav")
        separator.output_dir = instance.output_dir = str(work_dir)
        separator.separate(str(audio), custom_output_names=roles)
        stems = Stems(vocals=work_dir / "vocals.wav", instrumental=work_dir / "instrumental.wav")
        for path in (stems.vocals, stems.instrumental):
            if not path.is_file():
                raise RuntimeError(f"{self.model} did not write {path.name}")
        return stems
