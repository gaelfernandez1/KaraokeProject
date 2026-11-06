import json
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from karaoke_server.app import build_services, create_app
from karaoke_server.config import Settings
from karaoke_server.db import Database
from karaoke_server.network import NetworkState

from .conftest import MakeClient, write_package
from .live import live_server, read_events

FAKE_YTDLP = (sys.executable, str(Path(__file__).with_name("fake_ytdlp.py")))


@pytest.fixture
def fake_settings(settings: Settings) -> Settings:
    return Settings.from_env(
        data_dir=settings.data_dir,
        web_dir=settings.web_dir,
        fake_engine=True,
        ytdlp=FAKE_YTDLP,
        max_duration=60.0,
    )


@pytest.fixture
def app(fake_settings: Settings, db: Database):  # type: ignore[no-untyped-def]
    services = build_services(
        fake_settings, db=db, network_state=NetworkState("mirrored", "192.168.1.20", None, None)
    )
    return create_app(fake_settings, services=services)


def tone(path: Path, seconds: float = 3.0, **tags: str) -> Path:
    metadata = [arg for key, value in tags.items() for arg in ("-metadata", f"{key}={value}")]
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=d={seconds}",
            *metadata,
            str(path),
        ],
        check=True,
    )
    return path


def wait_for(http: httpx.Client, job_id: str, stage: str, timeout: float = 30) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = http.get(f"/api/jobs/{job_id}").json()
        if job["stage"] == stage:
            return job  # type: ignore[no-any-return]
        if job["stage"] in ("done", "error", "cancelled"):
            raise AssertionError(job)
        time.sleep(0.05)
    raise AssertionError(f"job still {job['stage']}")


@pytest.mark.usefixtures("ffmpeg")
def test_upload_makes_a_karaoke(app, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    song = tone(tmp_path / "Banda - Mar de Vigo.mp3")
    with live_server(app) as base, httpx.Client(base_url=base, timeout=30) as http:
        with song.open("rb") as f:
            created = http.post(
                "/api/jobs",
                data={"language": "gl", "lyrics": "Ola mar"},
                files={"file": (song.name, f, "audio/mpeg")},
            )
        assert created.status_code == 201, created.text
        job = created.json()
        assert job["title"] == "Mar de Vigo"
        assert job["with_lyrics"] is True
        done = wait_for(http, job["id"], "done")
        assert done["song_id"] == "mar-de-vigo"
        songs = http.get("/api/songs").json()
        assert [s["id"] for s in songs] == ["mar-de-vigo"]
        assert songs[0]["artist"] == "Banda"
        assert http.get(f"/api/jobs/{job['id']}/log").status_code == 200


@pytest.mark.usefixtures("ffmpeg")
def test_upload_uses_file_tags_for_title(app, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    song = tone(tmp_path / "track01.mp3", title="Pandeireta", artist="Fillas")
    with live_server(app) as base, httpx.Client(base_url=base, timeout=30) as http:
        with song.open("rb") as f:
            job = http.post(
                "/api/jobs", data={"language": "gl"}, files={"file": (song.name, f)}
            ).json()
        assert job["title"] == "Pandeireta"
        assert job["with_lyrics"] is False


@pytest.mark.usefixtures("ffmpeg")
def test_upload_without_tags_takes_a_clean_title_from_the_file_name(app, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    song = tone(tmp_path / "plain.mp3")
    with live_server(app) as base, httpx.Client(base_url=base, timeout=30) as http:
        titles = []
        for name in ("01 - un aire.mp3", "2_laverca.mp3", "Cibrán - 06. O mundo do motor.mp3"):
            with song.open("rb") as f:
                job = http.post(
                    "/api/jobs", data={"language": "gl"}, files={"file": (name, f)}
                ).json()
            titles.append(job["title"])
        assert titles == ["un aire", "laverca", "O mundo do motor"]


@pytest.mark.usefixtures("ffmpeg")
def test_upload_checks(app, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    picture = tmp_path / "x.png"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=16x16",
            "-frames:v",
            "1",
            str(picture),
        ],
        check=True,
    )
    long_song = tone(tmp_path / "long.mp3", seconds=61)
    with live_server(app) as base, httpx.Client(base_url=base, timeout=30) as http:

        def post(path: Path, **data: str) -> httpx.Response:
            with path.open("rb") as f:
                return http.post(
                    "/api/jobs", data={"language": "gl", **data}, files={"file": (path.name, f)}
                )

        assert post(picture).json()["code"] == "no_audio"
        assert post(long_song).json()["code"] == "too_long"
        assert post(long_song, language="Galego").json()["code"] == "bad_language"
        # The three-letter code would lose every Galician model: refused at once, not after
        # waiting for the GPU.
        assert post(long_song, language="glg").json()["code"] == "bad_language"
        assert post(long_song, lyrics="[Estribillo]").json()["code"] == "bad_lyrics"
        assert http.post("/api/jobs", data={"language": "gl"}).json()["code"] == "bad_form"
        assert (
            http.post("/api/jobs", data={"language": "gl", "url": "ftp://x"}).json()["code"]
            == "bad_url"
        )
        settings = app.state.services.settings
        assert list(settings.jobs_dir.iterdir()) == []


def test_upload_goes_to_disk_not_tmp(app, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    import tempfile

    before = set(Path(tempfile.gettempdir()).iterdir())
    with live_server(app) as base, httpx.Client(base_url=base, timeout=30) as http:
        http.post("/api/jobs", data={"language": "gl"}, files={"file": ("x.mp3", b"x" * 3_000_000)})
    after = set(Path(tempfile.gettempdir()).iterdir())
    assert not [p for p in after - before if p.stat().st_size > 1_000_000]


def test_url_job_downloads_then_queues(app, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("FAKE_YTDLP", json.dumps({"pause": 0.05}))
    with live_server(app) as base, httpx.Client(base_url=base, timeout=30) as http:
        created = http.post("/api/jobs", data={"language": "gl", "url": "https://example.com/v"})
        assert created.status_code == 201
        done = wait_for(http, created.json()["id"], "done")
        assert done["title"] == "Pandeireta"
        song = http.get("/api/songs").json()[0]
        assert song["artist"] == "Banda"


def test_live_or_long_url_is_refused(app, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("FAKE_YTDLP", json.dumps({"info": {"duration": 3600}}))
    with live_server(app) as base, httpx.Client(base_url=base, timeout=30) as http:
        job = http.post("/api/jobs", data={"language": "gl", "url": "https://example.com/v"}).json()
        failed = wait_for(http, job["id"], "error")
        assert failed["error_code"] == "too_long"
        monkeypatch.setenv("FAKE_YTDLP", json.dumps({"info": {"is_live": True}}))
        job = http.post("/api/jobs", data={"language": "gl", "url": "https://example.com/v"}).json()
        assert wait_for(http, job["id"], "error")["error_code"] == "bad_url"


def test_jobs_routes_need_owner(app) -> None:  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    with TestClient(app, client=("192.168.1.20", 1)) as home:
        assert (
            home.post("/api/jobs", data={"language": "gl", "url": "https://x"}).status_code == 403
        )
        assert home.get("/api/jobs").status_code == 200
        assert home.delete("/api/jobs/job-x").status_code == 403
        assert home.post("/api/jobs/job-x/retry").status_code == 403
        assert (
            home.post(
                "/api/songs/x/exports", json={"aspect": "16:9", "theme": "clasico"}
            ).status_code
            == 403
        )
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 1)) as local:
        assert local.get("/api/jobs/job-x").status_code == 404
        assert local.post("/api/jobs/job-x/retry").status_code == 404


def test_job_events_stream_until_done(app, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("KARAOKE_FAKE_STAGE_SECONDS", "0.2")
    with live_server(app) as base, httpx.Client(base_url=base, timeout=30) as http:
        job = http.post("/api/jobs", data={"language": "gl", "url": "https://example.com/v"}).json()
        stages = []
        with http.stream("GET", f"/api/jobs/{job['id']}/events") as stream:
            lines = stream.iter_lines()
            while not stages or stages[-1] not in ("done", "error", "cancelled"):
                event, data = read_events(lines, 1)[0]
                assert event == "job"
                stages.append(json.loads(data)["stage"])
        assert "download" in stages
        assert "separate" in stages
        assert stages[-1] == "done"


def test_export_job_puts_the_mp4_in_exports(app, fake_settings: Settings) -> None:  # type: ignore[no-untyped-def]
    write_package(fake_settings.library_dir / "song")
    with live_server(app) as base, httpx.Client(base_url=base, timeout=30) as http:
        bad = http.post("/api/songs/song/exports", json={"aspect": "16:9", "theme": "neon"})
        assert bad.json()["code"] == "bad_theme"
        assert (
            http.post(
                "/api/songs/missing/exports", json={"aspect": "16:9", "theme": "clasico"}
            ).status_code
            == 404
        )
        job = http.post("/api/songs/song/exports", json={"aspect": "9:16", "theme": "moderno"})
        assert job.status_code == 201
        done = wait_for(http, job.json()["id"], "done")
        assert done["file"] == "exports/song-9x16-moderno.mp4"
        video = http.get(f"/media/song/{done['file']}?download=1")
        assert video.status_code == 200
        assert "attachment" in video.headers["content-disposition"]


def test_cancel_and_retry_through_the_api(app, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("KARAOKE_FAKE_STAGE_SECONDS", "2")
    with live_server(app) as base, httpx.Client(base_url=base, timeout=30) as http:
        job = http.post("/api/jobs", data={"language": "gl", "url": "https://example.com/v"}).json()
        wait_for(http, job["id"], "separate")
        assert http.delete(f"/api/jobs/{job['id']}").status_code == 204
        cancelled = wait_for(http, job["id"], "cancelled")
        assert cancelled["can_retry"] is True
        monkeypatch.setenv("KARAOKE_FAKE_STAGE_SECONDS", "0.01")
        again = http.post(f"/api/jobs/{job['id']}/retry")
        assert again.status_code == 200
        wait_for(http, job["id"], "done")
        assert http.post(f"/api/jobs/{job['id']}/retry").status_code == 409


@pytest.mark.anyio
async def test_job_events_start_from_the_job_as_it_is_once_subscribed() -> None:
    """A short job may end between the 404 check and the stream: its end must not be lost."""
    from types import SimpleNamespace

    from karaoke_server.models import Job
    from karaoke_server.routes.jobs import job_events

    def job(stage: str) -> Job:
        return Job(
            id="job-1", kind="export", title="x", stage=stage, progress=0.0, song_id=None,
            file=None, error=None, error_code=None, with_lyrics=False, created_at="2026",
            overall=None, eta=None, can_retry=False, attempt=1,
        )  # fmt: skip

    class Queue:
        def get(self, job_id: str) -> Job:
            return job("done")

        def subscribe(self, job_id: str, listener: object):  # type: ignore[no-untyped-def]
            return lambda: None

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        services=SimpleNamespace(jobs=Queue()))))  # fmt: skip
    stream = job_events(job("video"), request)  # type: ignore[arg-type]
    first = await anext(stream)  # type: ignore[call-overload]
    assert first.data["stage"] == "done"
    await stream.aclose()  # type: ignore[attr-defined]


def test_export_theme_must_be_a_plain_name(make_client: MakeClient, settings: Settings) -> None:
    write_package(settings.library_dir / "song")
    local = make_client("local")
    for theme in ("../themes/clasico", "clasico/../clasico", "/etc/passwd", ".hidden", "clasico\n"):
        answer = local.post("/api/songs/song/exports", json={"aspect": "16:9", "theme": theme})
        assert answer.status_code == 422, theme
        assert answer.json()["code"] == "bad_theme"


def test_every_error_has_a_code_the_app_can_translate(
    settings: Settings, make_client: MakeClient
) -> None:
    write_package(settings.library_dir / "song")
    owner = make_client("local")
    invalid = owner.put("/api/songs/song/doc", json={"duration": -1})
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "invalid_request"
    assert isinstance(invalid.json()["detail"], str)
    unknown = owner.post("/api/nothing-here")
    assert unknown.status_code in (404, 405)
    assert unknown.json()["code"] in ("not_found", "method_not_allowed")


def test_a_broken_upload_is_a_clear_error_and_leaves_nothing(
    app,  # type: ignore[no-untyped-def]
) -> None:
    with live_server(app) as base, httpx.Client(base_url=base, timeout=30) as http:
        broken = http.post(
            "/api/jobs",
            content=b"--xyz\r\nContent-Disposition: form-data\r\n\r\nnot closed",
            headers={"Content-Type": "multipart/form-data; boundary=xyz"},
        )
        assert broken.status_code == 400
        assert broken.json()["code"] == "bad_form"
    assert list(app.state.services.settings.jobs_dir.iterdir()) == []
