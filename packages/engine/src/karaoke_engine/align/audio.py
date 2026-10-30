"""The vocals as the alignment models want them: mono float32 at 16 kHz."""

import subprocess
from pathlib import Path

import numpy as np
import numpy.typing as npt

from karaoke_engine.audio import AudioError

SAMPLE_RATE = 16_000


def load_mono16k(path: Path) -> npt.NDArray[np.float32]:
    """Decodes any format ffmpeg reads into mono float32 samples at 16 kHz."""
    if not path.is_file():
        raise AudioError(path, "file not found")
    result = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar",
         str(SAMPLE_RATE), "pipe:1"],
        capture_output=True,
        check=False,
    )  # fmt: skip
    if result.returncode != 0:
        raise AudioError(path, result.stderr.decode(errors="replace"))
    return np.frombuffer(result.stdout, dtype=np.float32).copy()
