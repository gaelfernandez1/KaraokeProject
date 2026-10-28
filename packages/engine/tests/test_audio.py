import shutil
import subprocess
from pathlib import Path

import pytest

from karaoke_engine.audio import (
    Gain,
    Loudness,
    decode,
    measure,
    package_audio,
    plan_gain,
    probe,
)
from karaoke_engine.steps import Stems

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")


def _lavfi(dest: Path, source: str, *extra: str) -> Path:
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", source, *extra, str(dest)],
        check=True,
    )
    return dest


def _noise(dest: Path, amplitude: float, seconds: float = 6.0, seed: int = 1) -> Path:
    # Pink noise is closer to music than a sine for a loudness meter.
    return _lavfi(
        dest,
        f"anoisesrc=color=pink:amplitude={amplitude}:duration={seconds}:seed={seed}",
        "-ac", "2", "-ar", "44100",
    )  # fmt: skip


def test_plan_gain_reaches_the_target() -> None:
    assert plan_gain(Loudness(-20.0, -6.0), [-8.0, -10.0]) == Gain(db=6.0, lufs=-14.0)


def test_plan_gain_stops_at_the_peak_ceiling() -> None:
    # The loudest stem peaks at -3 dBTP, so only 2 dB fit under the -1 dBTP ceiling.
    assert plan_gain(Loudness(-20.0, -2.0), [-3.0, -9.0]) == Gain(db=2.0, lufs=-18.0)


def test_plan_gain_leaves_silence_alone() -> None:
    assert plan_gain(Loudness(None, None), [None, None]) == Gain(db=0.0, lufs=None)


def test_measure_reports_loudness_and_peak(tmp_path: Path) -> None:
    quiet = measure(_noise(tmp_path / "quiet.wav", 0.05))
    loud = measure(_noise(tmp_path / "loud.wav", 0.2))

    assert quiet.integrated is not None
    assert loud.integrated is not None
    # Four times the amplitude is 12 dB louder.
    assert loud.integrated - quiet.integrated == pytest.approx(12.0, abs=0.5)
    assert quiet.true_peak is not None
    assert quiet.true_peak < 0


def test_measure_of_silence_is_none(tmp_path: Path) -> None:
    silence = _lavfi(tmp_path / "silence.wav", "anullsrc=r=44100:cl=stereo", "-t", "3")

    assert measure(silence) == Loudness(None, None)


def test_decode_takes_the_audio_of_a_video(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i",
         "testsrc=size=160x120:rate=10:duration=4", "-f", "lavfi", "-i",
         "sine=frequency=440:sample_rate=48000:duration=4", "-shortest", "-c:v", "mpeg4",
         "-c:a", "aac", str(video)],
        check=True,
    )  # fmt: skip

    wav = decode(video, tmp_path / "audio.wav")

    info = probe(wav)
    assert (info.sample_rate, info.channels) == (44100, 2)
    assert info.duration == pytest.approx(4.0, abs=0.1)


def test_package_audio_writes_normalized_m4a(tmp_path: Path) -> None:
    vocals = _noise(tmp_path / "vocals.wav", 0.02, seed=1)
    instrumental = _noise(tmp_path / "instrumental.wav", 0.03, seed=2)
    mix = tmp_path / "mix.wav"
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(vocals), "-i", str(instrumental),
         "-filter_complex", "amix=inputs=2:normalize=0", str(mix)],
        check=True,
    )  # fmt: skip

    refs = package_audio(mix, Stems(vocals=vocals, instrumental=instrumental), tmp_path / "pkg")

    assert (refs.instrumental, refs.vocals) == ("instrumental.m4a", "vocals.m4a")
    assert refs.loudness_lufs == pytest.approx(-14.0, abs=0.1)
    out = {name: tmp_path / "pkg" / name for name in ("instrumental.m4a", "vocals.m4a")}
    for path in out.values():
        info = probe(path)
        assert (info.codec, info.sample_rate, info.channels) == ("aac", 44100, 2)
        assert info.duration == pytest.approx(6.0, abs=0.05)
    # Both stems go through the same encoder settings, so they decode to the same length.
    lengths = {probe(decode(p, tmp_path / f"{p.stem}.wav")).frames for p in out.values()}
    assert len(lengths) == 1
    # Played together at full volume, the stems sound like the mix at the target loudness.
    together = tmp_path / "together.wav"
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(out["vocals.m4a"]), "-i",
         str(out["instrumental.m4a"]), "-filter_complex", "amix=inputs=2:normalize=0",
         str(together)],
        check=True,
    )  # fmt: skip
    measured = measure(together).integrated
    assert measured == pytest.approx(-14.0, abs=0.7)
