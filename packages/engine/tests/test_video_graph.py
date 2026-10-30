import shutil
import subprocess
from pathlib import Path

import pytest

from karaoke_contracts import VideoRefs, load_doc
from karaoke_engine.subtitles.themes import load_theme
from karaoke_engine.video.graph import (
    Background,
    background_graph,
    choose_background,
    dim_factor,
    gradient_colors,
)
from karaoke_engine.video.media import VideoInfo

DEMO = Path(__file__).resolve().parents[3] / "fixtures/packages/demo-sintetico"


def test_same_aspect_covers_without_fill() -> None:
    graph = background_graph(Background("video", None, 1280, 720), 1920, 1080, 30, 1.0, 10)

    assert "scale=1920:1080:force_original_aspect_ratio=increase" in graph
    assert "crop=1920:1080" in graph
    assert "split" not in graph
    assert graph.endswith("[bg]")


def test_graph_contains_fit_with_blurred_fill() -> None:
    graph = background_graph(Background("video", None, 1080, 1080), 1920, 1080, 30, 1.0, 10)

    assert "split" in graph
    assert "boxblur" in graph
    assert "force_original_aspect_ratio=decrease" in graph
    assert "overlay=(W-w)/2:(H-h)/2" in graph


def test_portrait_puts_video_high() -> None:
    graph = background_graph(Background("video", None, 1920, 1080), 1080, 1920, 30, 1.0, 10)

    assert "overlay=(W-w)/2:max(0\\,H*0.36-h/2)" in graph


def test_dimming_darkens_the_picture_and_more_the_fill() -> None:
    graph = background_graph(Background("video", None, 1080, 1080), 1920, 1080, 30, 0.6, 10)

    assert "lutyuv=y=val*0.6" in graph
    assert "lutyuv=y=val*0.45" in graph


def test_fast_video_is_brought_down_to_30_fps() -> None:
    graph = background_graph(Background("video", None, 1920, 1080, 50), 1920, 1080, 30, 1.0, 10)

    assert graph.startswith("[0:v]fps=30,")


def test_image_moves_slowly() -> None:
    graph = background_graph(Background("image", None, 1000, 1000), 1920, 1080, 30, 1.0, 10)

    assert "zoompan" in graph


def test_gradient_uses_theme_colours() -> None:
    colors = gradient_colors(load_theme("clasico"))
    graph = background_graph(Background("gradient"), 1920, 1080, 30, 1.0, 12.5, colors)

    assert graph.startswith("gradients=s=160x90:r=30:d=12.500")
    assert all(f"={c}" in graph for c in colors)
    assert "scale=1920:1080" in graph


def test_gradient_colours_are_dark_versions_of_the_theme() -> None:
    assert gradient_colors(load_theme("clasico")) == ["0x141428", "0x4C3B0F", "0x183F4C"]


@pytest.mark.parametrize(("mean", "factor"), [(0.0, 1.0), (0.3, 1.0), (0.625, 0.8), (0.95, 0.6)])
def test_dim_factor(mean: float, factor: float) -> None:
    assert dim_factor(mean) == pytest.approx(factor)


def _package(tmp_path: Path) -> Path:
    package = tmp_path / "pkg"
    shutil.copytree(DEMO, package)
    return package


def test_auto_background_falls_back_to_gradient(tmp_path: Path) -> None:
    package = _package(tmp_path)

    assert choose_background(package, load_doc(package / "karaoke.json")).kind == "gradient"


@pytest.mark.usefixtures("ffmpeg")
def test_auto_prefers_video(tmp_path: Path) -> None:
    package = _package(tmp_path)
    for name, source, frames in (
        ("background.mp4", "testsrc2=s=320x240:d=1", "25"),
        ("cover.jpg", "color=red:s=64x64", "1"),
    ):
        subprocess.run(
            ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", source, "-frames:v", frames,
             str(package / name)],
            check=True,
        )  # fmt: skip
    doc = load_doc(package / "karaoke.json").model_copy(
        update={"video": VideoRefs(background="background.mp4"), "cover": "cover.jpg"}
    )

    auto = choose_background(package, doc)
    assert (auto.kind, auto.width, auto.height) == ("video", 320, 240)
    assert choose_background(package, doc, "cover").kind == "image"
    assert choose_background(package, doc, str(package / "cover.jpg")).kind == "image"


def test_asking_for_a_missing_background_fails(tmp_path: Path) -> None:
    package = _package(tmp_path)

    with pytest.raises(ValueError, match="no cover"):
        choose_background(package, load_doc(package / "karaoke.json"), "cover")


def test_an_explicit_background_path_is_made_absolute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _package(tmp_path)
    (tmp_path / "fondo.jpg").write_bytes((package / "karaoke.json").read_bytes())
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "karaoke_engine.video.graph.probe_video", lambda path: VideoInfo(64, 64, 0, 0)
    )

    background = choose_background(package, load_doc(package / "karaoke.json"), "fondo.jpg")

    assert background.path == tmp_path / "fondo.jpg"
