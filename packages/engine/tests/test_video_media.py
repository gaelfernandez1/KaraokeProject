import json
import shutil
import subprocess
from itertools import pairwise
from pathlib import Path

import pytest

from karaoke_contracts import dump_doc, load_doc
from karaoke_engine.video.media import (
    add_background,
    extract_background,
    extract_cover,
    mean_luma,
    probe_video,
)

pytestmark = pytest.mark.usefixtures("ffmpeg")

DEMO = Path(__file__).resolve().parents[3] / "fixtures/packages/demo-sintetico"


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def _clip(path: Path, size: str = "640x360", rate: int = 25, seconds: float = 3) -> Path:
    _ffmpeg(
        "-f", "lavfi", "-i", f"testsrc2=s={size}:r={rate}:d={seconds}",
        "-f", "lavfi", "-i", f"sine=d={seconds}", "-shortest", str(path),
    )  # fmt: skip
    return path


def _song_with_art(tmp_path: Path) -> Path:
    art = tmp_path / "art.png"
    _ffmpeg("-f", "lavfi", "-i", "color=red:s=300x300", "-frames:v", "1", str(art))
    song = tmp_path / "song.mp3"
    _ffmpeg(
        "-f", "lavfi", "-i", "sine=d=2", "-i", str(art), "-map", "0:a", "-map", "1:v",
        "-c:v", "png", "-disposition:v", "attached_pic", str(song),
    )  # fmt: skip
    return song


def _streams(path: Path) -> list[dict[str, object]]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    streams: list[dict[str, object]] = json.loads(out)["streams"]
    return streams


def test_probe_finds_video(tmp_path: Path) -> None:
    info = probe_video(_clip(tmp_path / "a.mp4"))

    assert info is not None
    assert (info.width, info.height) == (640, 360)
    assert info.fps == pytest.approx(25)
    assert info.duration == pytest.approx(3, abs=0.1)


def test_probe_ignores_attached_picture(tmp_path: Path) -> None:
    assert probe_video(_song_with_art(tmp_path)) is None


def test_audio_only_source_has_no_background(tmp_path: Path) -> None:
    song = tmp_path / "song.wav"
    _ffmpeg("-f", "lavfi", "-i", "sine=d=1", str(song))

    assert probe_video(song) is None


def test_background_is_web_friendly(tmp_path: Path) -> None:
    out = extract_background(_clip(tmp_path / "a.mp4", size="2560x1440"), tmp_path / "bg.mp4")

    (video,) = _streams(out)
    assert video["codec_name"] == "h264"
    assert video["pix_fmt"] == "yuv420p"
    assert (video["width"], video["height"]) == (1280, 720)
    data = out.read_bytes()
    assert data.index(b"moov") < data.index(b"mdat")
    keys = subprocess.run(
        ["ffprobe", "-v", "error", "-skip_frame", "nokey", "-select_streams", "v:0",
         "-show_entries", "frame=pts_time", "-of", "csv=p=0", str(out)],
        capture_output=True, text=True, check=True,
    ).stdout.split()  # fmt: skip
    times = [float(t) for t in keys]
    assert max(b - a for a, b in pairwise(times)) <= 1.05


def test_background_caps_fps_at_30(tmp_path: Path) -> None:
    out = extract_background(_clip(tmp_path / "a.mp4", rate=50), tmp_path / "bg.mp4")

    info = probe_video(out)
    assert info is not None
    assert info.fps == pytest.approx(30)


def test_cover_from_attached_picture(tmp_path: Path) -> None:
    cover = extract_cover(_song_with_art(tmp_path), tmp_path / "cover.jpg")

    assert cover is not None
    (image,) = _streams(cover)
    assert (image["width"], image["height"]) == (300, 300)
    assert mean_luma(cover) == pytest.approx(0.30, abs=0.05)  # pure red has a luma of 0.3


def test_cover_from_a_frame(tmp_path: Path) -> None:
    cover = extract_cover(_clip(tmp_path / "a.mp4", size="1920x1080"), tmp_path / "cover.jpg")

    assert cover is not None
    (image,) = _streams(cover)
    assert (image["width"], image["height"]) == (1280, 720)


def test_no_cover_from_plain_audio(tmp_path: Path) -> None:
    song = tmp_path / "song.wav"
    _ffmpeg("-f", "lavfi", "-i", "sine=d=1", str(song))

    assert extract_cover(song, tmp_path / "cover.jpg") is None


def test_mean_luma_of_white_and_black(tmp_path: Path) -> None:
    white, black = tmp_path / "w.mp4", tmp_path / "b.mp4"
    _ffmpeg("-f", "lavfi", "-i", "color=white:s=64x64:d=2", "-pix_fmt", "yuv420p", str(white))
    _ffmpeg("-f", "lavfi", "-i", "color=black:s=64x64:d=2", "-pix_fmt", "yuv420p", str(black))

    assert mean_luma(white) > 0.9
    assert mean_luma(black) < 0.1


def test_probe_reports_the_shape_after_rotation(tmp_path: Path) -> None:
    rotated = tmp_path / "phone.mp4"
    _ffmpeg(
        "-display_rotation", "90", "-i", str(_clip(tmp_path / "a.mp4")), "-c", "copy", str(rotated)
    )

    info = probe_video(rotated)

    assert info is not None
    assert (info.width, info.height) == (360, 640)


def _package_with_cover(tmp_path: Path) -> Path:
    package = tmp_path / "pkg"
    shutil.copytree(DEMO, package)
    _ffmpeg("-f", "lavfi", "-i", "color=blue:s=64x64", "-frames:v", "1", str(package / "cover.jpg"))
    doc = load_doc(package / "karaoke.json").model_copy(update={"cover": "cover.jpg"})
    dump_doc(doc, package / "karaoke.json")
    return package


def test_a_song_with_art_replaces_the_cover(tmp_path: Path) -> None:
    package = _package_with_cover(tmp_path)

    add_background(package, _song_with_art(tmp_path))

    assert mean_luma(package / "cover.jpg") == pytest.approx(0.30, abs=0.05)  # red, not blue


def test_a_failed_background_leaves_the_old_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _package_with_cover(tmp_path)
    (package / "background.mp4").write_bytes(b"old")

    def broken(source: Path, out: Path) -> Path:
        out.write_bytes(b"half")
        raise RuntimeError("ffmpeg failed")

    monkeypatch.setattr("karaoke_engine.video.media.extract_background", broken)
    before = (package / "karaoke.json").read_bytes()

    with pytest.raises(RuntimeError):
        add_background(package, _clip(tmp_path / "a.mp4"))

    assert (package / "background.mp4").read_bytes() == b"old"
    assert (package / "karaoke.json").read_bytes() == before
