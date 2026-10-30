import json
import shutil
import subprocess
from pathlib import Path

import pytest

from karaoke_contracts import load_doc
from karaoke_engine.cli import main
from karaoke_engine.demo import synthesize_package_audio
from karaoke_engine.subtitles.layout import build_layout
from karaoke_engine.subtitles.themes import load_theme, theme_metrics
from karaoke_engine.video.render import credits_text, render, title_events

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures/packages"


def _layout(package: str, width: int = 1920, height: int = 1080):  # type: ignore[no-untyped-def]
    theme = load_theme("clasico")
    doc = load_doc(FIXTURES / package / "karaoke.json")
    return doc, theme, build_layout(doc, theme, width, height, theme_metrics(theme))


def _stamps(events: list[str]) -> list[tuple[str, str, str]]:
    return [(e.split(",")[1], e.split(",")[2], e.rsplit("}", 1)[-1]) for e in events]


def test_title_when_singing_starts_late() -> None:
    doc, theme, layout = _layout("nandomalo-esencia")

    events = title_events(doc, theme, layout, 1920, 1080, None)

    # The first line shows at 16.47 s: the title is on from 0.5 s until 0.5 s before it.
    assert ("0:00:00.50", "0:00:15.92", "Esencia") in _stamps(events)
    assert ("0:00:00.50", "0:00:15.92", "NANDOMALO") in _stamps(events)


def test_no_title_when_singing_starts_early() -> None:
    doc, theme, layout = _layout("demo-sintetico")

    titles = [e for e in title_events(doc, theme, layout, 1920, 1080, None) if "00:00:00" in e]
    assert titles == []


def test_credits_at_the_end() -> None:
    doc, theme, layout = _layout("nandomalo-esencia")

    events = title_events(doc, theme, layout, 1920, 1080, "Licence: CC BY-SA")

    texts = [t for start, _, t in _stamps(events) if start > "0:04:00"]
    assert texts == ["Esencia · NANDOMALO", "Licence: CC BY-SA"]


def test_credits_text_from_the_licence() -> None:
    assert credits_text(FIXTURES / "nandomalo-esencia") == (
        "Song: Esencia by NANDOMALO · Licence: CC BY-SA · "
        "Source: https://www.jamendo.com/track/1348566/esencia/lyrics"
    )
    assert credits_text(FIXTURES / "demo-sintetico") is None


def _probe(path: Path) -> dict[str, object]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    data: dict[str, object] = json.loads(out)
    return data


@pytest.fixture
def demo(tmp_path: Path) -> Path:
    package = tmp_path / "demo"
    shutil.copytree(FIXTURES / "demo-sintetico", package)
    synthesize_package_audio(package)
    return package


@pytest.mark.usefixtures("ffmpeg")
@pytest.mark.parametrize(("aspect", "size"), [("16:9", (320, 180)), ("9:16", (180, 320))])
def test_render_writes_a_video(
    demo: Path, tmp_path: Path, aspect: str, size: tuple[int, int]
) -> None:
    out = tmp_path / "out.mp4"

    report = render(demo, out, load_theme("clasico"), aspect=aspect, size=size)

    data = _probe(out)
    streams = data["streams"]
    assert isinstance(streams, list)
    video = next(s for s in streams if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == size
    assert any(s["codec_type"] == "audio" for s in streams)
    assert float(data["format"]["duration"]) == pytest.approx(32, abs=0.2)  # type: ignore[index]
    assert report.thumbnail is not None
    assert report.thumbnail.is_file()


@pytest.mark.usefixtures("ffmpeg")
def test_render_mixes_guide_vocals_only_when_asked(demo: Path, tmp_path: Path) -> None:
    quiet, loud = tmp_path / "quiet.mp4", tmp_path / "loud.mp4"

    render(demo, quiet, load_theme("clasico"), size=(160, 90))
    render(demo, loud, load_theme("clasico"), size=(160, 90), vocals=1.0)

    def level(path: Path) -> float:
        out = subprocess.run(
            ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, check=True,
        ).stderr  # fmt: skip
        return float(out.split("mean_volume:")[1].split("dB")[0])

    assert level(loud) > level(quiet) + 1


@pytest.mark.usefixtures("ffmpeg")
def test_cli_render(demo: Path, tmp_path: Path) -> None:
    out = tmp_path / "cli.mp4"

    assert main(["render", str(demo), "--size", "160x90", "-o", str(out)]) == 0
    assert out.is_file()


@pytest.mark.usefixtures("ffmpeg")
def test_cli_background_adds_a_video_and_a_cover(demo: Path, tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=320x240:d=2", str(clip)],
        check=True,
    )

    assert main(["background", str(demo), str(clip)]) == 0

    doc = load_doc(demo / "karaoke.json")
    assert doc.video is not None
    assert doc.video.background == "background.mp4"
    assert doc.cover == "cover.jpg"
    assert (demo / "background.mp4").is_file()
    assert (demo / "cover.jpg").is_file()
    assert main(["validate", str(demo)]) == 0


@pytest.mark.usefixtures("ffmpeg")
def test_render_accepts_a_relative_package_path(
    demo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clip = tmp_path / "clip.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=320x240:d=2", str(clip)],
        check=True,
    )
    assert main(["background", str(demo), str(clip)]) == 0
    monkeypatch.chdir(tmp_path)

    assert main(["render", "demo", "--size", "160x90", "-o", "rel.mp4"]) == 0
    assert (tmp_path / "rel.mp4").is_file()


@pytest.mark.usefixtures("ffmpeg")
def test_thumbnail_shows_the_title_at_full_strength(demo: Path, tmp_path: Path) -> None:
    out = tmp_path / "thumb.mp4"
    report = render(demo, out, load_theme("clasico"), size=(640, 360), background="gradient")
    assert report.thumbnail is not None

    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(report.thumbnail), "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True,
    ).stdout  # fmt: skip
    # The title is drawn in the sung colour (#FFC531): some pixels must be that bright yellow.
    yellow = sum(
        1
        for i in range(0, len(raw), 3)
        if raw[i] > 220 and 170 < raw[i + 1] < 220 and raw[i + 2] < 90
    )
    assert yellow > 200
