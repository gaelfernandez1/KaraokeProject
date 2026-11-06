import asyncio
from pathlib import Path

import anyio
import pytest

from karaoke_server.config import Settings
from karaoke_server.db import Database
from karaoke_server.jobs.queue import JobQueue
from karaoke_server.jobs.store import JobStore
from karaoke_server.jobs.types import DownloadError, Outcome, RemoteInfo
from karaoke_server.library import Library
from karaoke_server.models import ExportRequest, Job, MakeRequest

from .conftest import write_package

pytestmark = pytest.mark.anyio


class FakeSpawner:
    """Runs jobs only when the test lets them, reporting the stages the engine would."""

    def __init__(self) -> None:
        self.running: list[str] = []
        self.started: list[str] = []
        self.gates: dict[str, asyncio.Event] = {}
        self.outcomes: dict[str, list[Outcome]] = {}
        self.max_parallel = 0
        self.specs: dict[str, dict[str, object]] = {}

    leftovers_stopped = 0

    def stop_leftovers(self) -> None:
        self.leftovers_stopped += 1
        self.started_when_stopped = list(self.started)

    def gate(self, job_id: str) -> asyncio.Event:
        return self.gates.setdefault(job_id, asyncio.Event())

    async def run(self, job_id, spec, log, on_event):  # type: ignore[no-untyped-def]
        self.specs[job_id] = spec
        self.started.append(job_id)
        self.running.append(job_id)
        self.max_parallel = max(self.max_parallel, len(self.running))
        try:
            on_event({"event": "stage", "stage": "decode"})
            await self.gate(job_id).wait()
            self.gates.pop(job_id)
            outcomes = self.outcomes.get(job_id) or [Outcome(ok=True)]
            outcome = outcomes.pop(0) if len(outcomes) > 1 else outcomes[0]
            if outcome.ok and spec["kind"] == "make":
                write_package(Path(spec["out"]), title=spec.get("title") or "Made")
            if outcome.ok and spec["kind"] == "export":
                Path(spec["out"]).write_bytes(b"mp4")
            return outcome
        finally:
            self.running.remove(job_id)


class FakeDownloader:
    def __init__(self, info: RemoteInfo | None = None, fail: DownloadError | None = None) -> None:
        self.info = info or RemoteInfo(
            title="Song (Official Video)",
            artist="Band - Topic",
            track=None,
            duration=200.0,
            is_live=False,
        )
        self.fail = fail
        self.gate = asyncio.Event()
        self.gate.set()
        self.downloads = 0

    async def probe(self, url: str) -> RemoteInfo:
        if self.fail:
            raise self.fail
        return self.info

    async def download(self, url, dest, on_progress, parts=1):  # type: ignore[no-untyped-def]
        self.downloads += 1
        on_progress(0.5)
        await self.gate.wait()
        dest.mkdir(parents=True, exist_ok=True)
        path = dest / "source.mkv"
        path.write_bytes(b"video")
        return path


async def until(predicate, timeout: float = 5.0) -> None:  # type: ignore[no-untyped-def]
    with anyio.fail_after(timeout):
        while not predicate():
            await asyncio.sleep(0.01)


@pytest.fixture
def library(settings: Settings, db: Database) -> Library:
    return Library(settings, db)


def make_queue(
    settings: Settings,
    db: Database,
    library: Library,
    spawner: FakeSpawner,
    downloader: FakeDownloader | None = None,
) -> JobQueue:
    return JobQueue(settings, JobStore(db), library, spawner, downloader or FakeDownloader())


def upload(
    queue: JobQueue, settings: Settings, title: str = "Mar", lyrics: str | None = "la"
) -> Job:
    job_id = queue.new_id()
    source = settings.jobs_dir / job_id / "source.mp3"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"mp3")
    request = MakeRequest(language="gl", lyrics=lyrics, title=title)
    return queue.submit_make(job_id, request, source=source, duration=180.0)


async def test_jobs_run_one_at_a_time_in_order(
    settings: Settings, db: Database, library: Library
) -> None:
    spawner = FakeSpawner()
    queue = make_queue(settings, db, library, spawner)
    await queue.start()
    try:
        first, second = upload(queue, settings, "Un"), upload(queue, settings, "Dous")
        await until(lambda: spawner.started == [first.id])
        assert queue.get(second.id).stage == "queued"  # type: ignore[union-attr]
        assert queue.get(first.id).stage == "separate"  # type: ignore[union-attr]
        spawner.gate(first.id).set()
        await until(lambda: spawner.started == [first.id, second.id])
        spawner.gate(second.id).set()
        await until(lambda: queue.get(second.id).stage == "done")  # type: ignore[union-attr]
        assert spawner.max_parallel == 1
        done = queue.get(first.id)
        assert done is not None
        assert done.song_id == "un"
        assert done.overall == 1.0
        assert library.summary("un") is not None
        assert not (settings.jobs_dir / first.id / "source.mp3").exists()
    finally:
        await queue.stop()


async def test_download_overlaps_the_gpu(
    settings: Settings, db: Database, library: Library
) -> None:
    spawner = FakeSpawner()
    downloader = FakeDownloader()
    queue = make_queue(settings, db, library, spawner, downloader)
    await queue.start()
    try:
        busy = upload(queue, settings, "Busy")
        await until(lambda: spawner.started == [busy.id])
        link = queue.submit_make(queue.new_id(), MakeRequest(language="gl", url="https://x/v"))
        await until(lambda: queue.get(link.id).stage == "queued" and downloader.downloads == 1)  # type: ignore[union-attr]
        job = queue.get(link.id)
        assert job is not None
        assert job.title == "Song"
        spawner.gate(busy.id).set()
        await until(lambda: link.id in spawner.started)
        spawner.gate(link.id).set()
        await until(lambda: queue.get(link.id).stage == "done")  # type: ignore[union-attr]
    finally:
        await queue.stop()


async def test_events_tell_subscribers(settings: Settings, db: Database, library: Library) -> None:
    spawner = FakeSpawner()
    queue = make_queue(settings, db, library, spawner)
    await queue.start()
    try:
        seen: list[str] = []
        job = upload(queue, settings)
        queue.subscribe(job.id, lambda j: seen.append(j.stage))
        spawner.gate(job.id).set()
        await until(lambda: "done" in seen)
        assert seen[-1] == "done"
    finally:
        await queue.stop()


async def test_cancel_queued_and_running(
    settings: Settings, db: Database, library: Library
) -> None:
    spawner = FakeSpawner()
    queue = make_queue(settings, db, library, spawner)
    await queue.start()
    try:
        running, waiting = upload(queue, settings, "A"), upload(queue, settings, "B")
        await until(lambda: spawner.started == [running.id])
        assert await queue.cancel(waiting.id) is True
        assert queue.get(waiting.id).stage == "cancelled"  # type: ignore[union-attr]
        assert await queue.cancel(running.id) is True
        await until(lambda: queue.get(running.id).stage == "cancelled")  # type: ignore[union-attr]
        assert spawner.running == []
        assert await queue.cancel(running.id) is False
        cancelled = queue.get(running.id)
        assert cancelled is not None
        assert cancelled.can_retry is True
        assert cancelled.overall is None
    finally:
        await queue.stop()


async def test_transient_failure_is_retried_once(
    settings: Settings, db: Database, library: Library
) -> None:
    spawner = FakeSpawner()
    queue = make_queue(settings, db, library, spawner)
    await queue.start()
    try:
        job = upload(queue, settings)
        oom = Outcome(ok=False, code="gpu_memory", message="CUDA out of memory", transient=True)
        spawner.outcomes[job.id] = [oom, oom]
        spawner.gate(job.id).set()
        await until(lambda: spawner.started.count(job.id) == 2)
        assert queue.get(job.id).attempt == 2  # type: ignore[union-attr]
        spawner.gate(job.id).set()
        await until(lambda: queue.get(job.id).stage == "error")  # type: ignore[union-attr]
        failed = queue.get(job.id)
        assert failed is not None
        assert failed.error_code == "gpu_memory"
        assert failed.can_retry is True
    finally:
        await queue.stop()


async def test_input_error_is_not_retried(
    settings: Settings, db: Database, library: Library
) -> None:
    spawner = FakeSpawner()
    queue = make_queue(settings, db, library, spawner)
    await queue.start()
    try:
        job = upload(queue, settings)
        spawner.outcomes[job.id] = [Outcome(ok=False, code="bad_lyrics", message="no lines")]
        spawner.gate(job.id).set()
        await until(lambda: queue.get(job.id).stage == "error")  # type: ignore[union-attr]
        assert spawner.started.count(job.id) == 1
        assert queue.get(job.id).error == "no lines"  # type: ignore[union-attr]
    finally:
        await queue.stop()


async def test_retry_runs_a_failed_job_again(
    settings: Settings, db: Database, library: Library
) -> None:
    spawner = FakeSpawner()
    queue = make_queue(settings, db, library, spawner)
    await queue.start()
    try:
        job = upload(queue, settings)
        spawner.outcomes[job.id] = [
            Outcome(ok=False, code="engine_failed", message="x"),
            Outcome(ok=True),
        ]
        spawner.gate(job.id).set()
        await until(lambda: queue.get(job.id).stage == "error")  # type: ignore[union-attr]
        assert queue.retry("nope") is None
        again = queue.retry(job.id)
        assert again is not None
        assert again.stage == "queued"
        assert again.error is None
        spawner.gate(job.id).set()
        await until(lambda: queue.get(job.id).stage == "done")  # type: ignore[union-attr]
        assert queue.retry(job.id) is None
    finally:
        await queue.stop()


async def test_download_errors(settings: Settings, db: Database, library: Library) -> None:
    downloader = FakeDownloader(fail=DownloadError("too_long", "The video is longer than 20 min"))
    queue = make_queue(settings, db, library, FakeSpawner(), downloader)
    await queue.start()
    try:
        job = queue.submit_make(queue.new_id(), MakeRequest(language="gl", url="https://x/v"))
        await until(lambda: queue.get(job.id).stage == "error")  # type: ignore[union-attr]
        assert queue.get(job.id).error_code == "too_long"  # type: ignore[union-attr]
    finally:
        await queue.stop()


async def test_recover_requeues_running_jobs(
    settings: Settings, db: Database, library: Library
) -> None:
    store = JobStore(db)
    first = make_queue(settings, db, library, FakeSpawner())
    job = upload(first, settings)
    store.update(job.id, stage="align", stage_started=1.0)
    spawner = FakeSpawner()
    queue = make_queue(settings, db, library, spawner)
    await queue.start()
    try:
        await until(lambda: spawner.started == [job.id])
        assert queue.get(job.id).attempt == 2  # type: ignore[union-attr]
    finally:
        await queue.stop()


async def test_engines_left_by_a_server_that_died_are_stopped_before_resuming(
    settings: Settings, db: Database, library: Library
) -> None:
    store = JobStore(db)
    job = upload(make_queue(settings, db, library, FakeSpawner()), settings)
    store.update(job.id, stage="separate", stage_started=1.0)
    spawner = FakeSpawner()
    queue = make_queue(settings, db, library, spawner)
    await queue.start()
    try:
        await until(lambda: spawner.started == [job.id])
        assert spawner.leftovers_stopped == 1
        assert spawner.started_when_stopped == []  # before the job ran again
    finally:
        await queue.stop()


async def test_recover_marks_jobs_without_input_interrupted(
    settings: Settings, db: Database, library: Library
) -> None:
    store = JobStore(db)
    first = make_queue(settings, db, library, FakeSpawner())
    job = upload(first, settings)
    store.update(job.id, stage="separate", stage_started=1.0)
    (settings.jobs_dir / job.id / "source.mp3").unlink()
    queue = make_queue(settings, db, library, FakeSpawner())
    await queue.start()
    try:
        recovered = queue.get(job.id)
        assert recovered is not None
        assert recovered.stage == "error"
        assert recovered.error_code == "interrupted"
        assert recovered.can_retry is False
    finally:
        await queue.stop()


async def test_export_puts_the_mp4_in_exports(
    settings: Settings, db: Database, library: Library
) -> None:
    write_package(settings.library_dir / "song")
    spawner = FakeSpawner()
    queue = make_queue(settings, db, library, spawner)
    await queue.start()
    try:
        job = queue.submit_export("song", ExportRequest(aspect="9:16", theme="moderno"))
        assert job is not None
        assert job.kind == "export"
        spawner.gate(job.id).set()
        await until(lambda: queue.get(job.id).stage == "done")  # type: ignore[union-attr]
        done = queue.get(job.id)
        assert done is not None
        assert done.file == "exports/song-9x16-moderno.mp4"
        assert (settings.library_dir / "song" / done.file).is_file()
        assert queue.submit_export("missing", ExportRequest()) is None
    finally:
        await queue.stop()


async def test_export_of_a_deleted_song_fails_song_missing(
    settings: Settings, db: Database, library: Library
) -> None:
    write_package(settings.library_dir / "song")
    spawner = FakeSpawner()
    queue = make_queue(settings, db, library, spawner)
    await queue.start()
    try:
        busy = upload(queue, settings, "Busy")
        await until(lambda: spawner.started == [busy.id])
        job = queue.submit_export("song", ExportRequest())
        assert job is not None
        library.delete("song")
        spawner.gate(busy.id).set()
        await until(lambda: queue.get(job.id).stage == "error")  # type: ignore[union-attr]
        assert queue.get(job.id).error_code == "song_missing"  # type: ignore[union-attr]
    finally:
        await queue.stop()


@pytest.mark.parametrize("ending", ["cancel", "fail"])
async def test_an_export_that_does_not_finish_leaves_no_partial_video(
    settings: Settings, db: Database, library: Library, ending: str
) -> None:
    folder = write_package(settings.library_dir / "song")
    spawner = FakeSpawner()
    queue = make_queue(settings, db, library, spawner)
    await queue.start()
    try:
        job = queue.submit_export("song", ExportRequest())
        assert job is not None
        await until(lambda: job.id in spawner.started)
        partial = Path(str(spawner.specs[job.id]["out"]))
        partial.write_bytes(b"half a video")  # what ffmpeg had written so far
        partial.with_suffix(".jpg").write_bytes(b"thumb")
        # And the encoder's own scratch file, left when the runner is killed mid-encode.
        partial.with_name(f".{partial.stem}.part{partial.suffix}").write_bytes(b"half")
        if ending == "cancel":
            await queue.cancel(job.id)
        else:
            spawner.outcomes[job.id] = [Outcome(ok=False, code="engine_failed", message="x")]
            spawner.gate(job.id).set()
            await until(lambda: queue.get(job.id).stage == "error")  # type: ignore[union-attr]
        assert list((folder / "exports").iterdir()) == []
    finally:
        await queue.stop()


async def test_a_retried_job_does_not_count_its_stages_twice(
    settings: Settings, db: Database, library: Library
) -> None:
    spawner = FakeSpawner()
    queue = make_queue(settings, db, library, spawner)
    store = JobStore(db)
    await queue.start()
    try:
        job = upload(queue, settings)
        await until(lambda: job.id in spawner.started)
        store.update(job.id, stage_seconds={"download": 5.0, "separate": 100.0})
        oom = Outcome(ok=False, code="gpu_memory", message="CUDA out of memory", transient=True)
        spawner.outcomes[job.id] = [oom, Outcome(ok=True)]
        spawner.gate(job.id).set()
        await until(lambda: spawner.started.count(job.id) == 2)
        # The second attempt starts its stages from zero; a download is not done again.
        assert store.get(job.id).stage_seconds.get("separate", 0.0) < 100.0  # type: ignore[union-attr]
        assert store.get(job.id).stage_seconds["download"] == 5.0  # type: ignore[union-attr]
    finally:
        await queue.stop()


async def test_list_newest_first(settings: Settings, db: Database, library: Library) -> None:
    queue = make_queue(settings, db, library, FakeSpawner())
    first = upload(queue, settings, "A")
    second = upload(queue, settings, "B")
    assert [j.id for j in queue.list()] == [second.id, first.id]


async def test_cancel_stops_a_link_job_that_moved_on_to_the_gpu(
    settings: Settings, db: Database, library: Library
) -> None:
    spawner = FakeSpawner()
    queue = make_queue(settings, db, library, spawner)
    await queue.start()
    try:
        job = queue.submit_make(queue.new_id(), MakeRequest(language="gl", url="https://x/v"))
        await until(lambda: job.id in spawner.running)
        await asyncio.sleep(0.05)
        assert await queue.cancel(job.id) is True
        await until(lambda: queue.get(job.id).stage == "cancelled")  # type: ignore[union-attr]
        await until(lambda: spawner.running == [])
    finally:
        await queue.stop()


async def test_inputs_of_failed_jobs_go_after_seven_days(
    settings: Settings, db: Database, library: Library
) -> None:
    queue = make_queue(settings, db, library, FakeSpawner())
    old, recent = upload(queue, settings), upload(queue, settings)
    store = JobStore(db)
    for job in (old, recent):
        store.update(job.id, stage="error", error_code="engine_failed")
    db.execute("UPDATE jobs SET updated_at = '2026-01-01T00:00:00Z' WHERE id = ?", (old.id,))
    queue.purge_old_inputs()
    assert not (settings.jobs_dir / old.id).exists()
    assert queue.get(old.id).can_retry is False  # type: ignore[union-attr]
    assert (settings.jobs_dir / recent.id).exists()
    assert queue.get(recent.id).can_retry is True  # type: ignore[union-attr]


async def test_a_job_cancelled_before_it_could_start_stays_cancelled(
    settings: Settings, db: Database, library: Library, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DELETE can land between the lane creating the job's task and the task's first step."""
    spawner = FakeSpawner()
    queue = make_queue(settings, db, library, spawner)
    create_task = asyncio.create_task
    victims: list[str] = []

    def create_and_cancel(coro, **kwargs):  # type: ignore[no-untyped-def]
        task = create_task(coro, **kwargs)
        if getattr(coro, "__name__", "") == "_run_gpu" and not victims:
            job_id = coro.cr_frame.f_locals["record"].id
            victims.append(job_id)
            queue._cancelled.add(job_id)  # what cancel() does before task.cancel()
            task.cancel()
        return task

    monkeypatch.setattr(asyncio, "create_task", create_and_cancel)
    job = upload(queue, settings)
    await queue.start()
    try:
        await until(lambda: victims == [job.id])
        await asyncio.sleep(0.2)
        assert queue.get(job.id).stage == "cancelled"  # type: ignore[union-attr]
        assert spawner.started == []
    finally:
        await queue.stop()


def test_following_a_job_leaves_nothing_behind(
    settings: Settings, db: Database, library: Library
) -> None:
    queue = make_queue(settings, db, library, FakeSpawner())
    stop = queue.subscribe("job-1", lambda job: None)
    stop()
    stop()
    assert "job-1" not in queue._listeners


@pytest.mark.anyio
async def test_the_gpu_lane_survives_a_database_error(
    settings: Settings, db: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sqlite3

    from karaoke_server.jobs.store import JobStore

    spawner = FakeSpawner()
    queue = make_queue(settings, db, Library(settings, db), spawner)
    await queue.start()
    try:
        first = upload(queue, settings, "Un")
        await until(lambda: first.id in spawner.started)
        real_update = JobStore.update

        def full_disk(self: JobStore, job_id: str, **changes: object) -> object:
            raise sqlite3.OperationalError("database or disk is full")

        monkeypatch.setattr(JobStore, "update", full_disk)
        spawner.gate(first.id).set()
        await asyncio.sleep(0.2)
        monkeypatch.setattr(JobStore, "update", real_update)  # space freed
        second = upload(queue, settings, "Dous")
        await until(lambda: second.id in spawner.started)
    finally:
        await queue.stop()
