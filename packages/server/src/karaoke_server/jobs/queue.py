"""The job queue: one job on the GPU at a time, and downloads alongside it.

Two lanes read the jobs table: the download lane fetches links (one at a time) and puts the
song back in the queue; the GPU lane runs the engine for the oldest ready job in a process of
its own. A job that fails for a passing reason (out of memory, a crash) is tried once more.
After a restart, what was running goes back to the queue.
"""

import asyncio
import contextlib
import logging
import secrets
import shutil
import time
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from karaoke_server.config import Settings
from karaoke_server.jobs.progress import ENGINE_STAGE, TIME_BASED, Estimator
from karaoke_server.jobs.store import TERMINAL, JobRecord, JobStore
from karaoke_server.jobs.titles import clean_artist, clean_title
from karaoke_server.jobs.types import Downloader, DownloadError, Event, Outcome, Spawner
from karaoke_server.library import Library
from karaoke_server.models import ExportRequest, Job, MakeRequest

logger = logging.getLogger(__name__)

# One automatic retry; a job that keeps taking the server down stops after this many starts.
MAX_ATTEMPTS = 2
MAX_STARTS = 3
KEEP_DAYS = 7
# After an unexpected error, a lane waits this long before picking the next job.
LANE_RETRY_SECONDS = 1.0
TICK_SECONDS = 2.0

Listener = Callable[[Job], None]


class JobQueue:
    def __init__(
        self,
        settings: Settings,
        store: JobStore,
        library: Library,
        spawner: Spawner,
        downloader: Downloader,
        estimator: Estimator | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.settings = settings
        self.store = store
        self.library = library
        self.spawner = spawner
        self.downloader = downloader
        self.estimator = estimator or Estimator(store.stage_history)
        self.now = now
        self._listeners: dict[str, list[Listener]] = {}
        # Made in start(), on the loop that runs the lanes.
        self._gpu_wake: asyncio.Event | None = None
        self._download_wake: asyncio.Event | None = None
        self._loops: list[asyncio.Task[None]] = []
        self._running: dict[str, asyncio.Task[None]] = {}
        self._cancelled: set[str] = set()

    # Lifecycle

    async def start(self) -> None:
        await asyncio.to_thread(self.spawner.stop_leftovers)
        self.recover()
        self._gpu_wake, self._download_wake = asyncio.Event(), asyncio.Event()
        self._loops = [
            asyncio.create_task(self._lane(self.store.next_for_gpu, self._run_gpu, self._gpu_wake)),
            asyncio.create_task(
                self._lane(self.store.next_for_download, self._run_download, self._download_wake)
            ),
            asyncio.create_task(self._tick()),
        ]

    async def stop(self) -> None:
        for task in self._loops:
            task.cancel()
        await asyncio.gather(*self._loops, return_exceptions=True)
        self._loops = []

    # Asking for work

    def new_id(self) -> str:
        return f"job-{secrets.token_hex(4)}"

    def job_dir(self, job_id: str) -> Path:
        return self.settings.jobs_dir / job_id

    def submit_make(
        self,
        job_id: str,
        request: MakeRequest,
        source: Path | None = None,
        duration: float | None = None,
        title: str | None = None,
    ) -> Job:
        """A song (already in the job's folder, or a link to fetch) to turn into a karaoke."""
        name = request.title or title or "Canción nova"
        record = JobRecord.new(job_id, "make", name, request.model_dump(), self.now())
        record.source = str(source) if source else None
        record.duration = duration
        self.store.add(record)
        self._wake()
        return self._emit(record)

    def submit_export(self, song_id: str, request: ExportRequest) -> Job | None:
        doc = self.library.doc(song_id)
        if doc is None:
            return None
        data = {"song_id": song_id, **request.model_dump()}
        record = JobRecord.new(self.new_id(), "export", doc.title, data, self.now())
        record.duration = doc.duration
        self.store.add(record)
        self._wake()
        return self._emit(record)

    async def cancel(self, job_id: str) -> bool:
        record = self.store.get(job_id)
        if record is None or record.stage in TERMINAL:
            return False
        task = self._running.get(job_id)
        if task is not None:
            self._cancelled.add(job_id)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            return True
        self._finish(job_id, stage="cancelled")
        return True

    def retry(self, job_id: str) -> Job | None:
        record = self.store.get(job_id)
        if record is None or not self._can_retry(record):
            return None
        updated = self.store.update(
            job_id,
            stage="queued",
            progress=0.0,
            error=None,
            error_code=None,
            attempt=record.attempt + 1,
            stage_started=None,
            stage_seconds=_kept_seconds(record),
        )
        assert updated is not None
        self._wake()
        return self._emit(updated)

    # Reading

    def get(self, job_id: str) -> Job | None:
        record = self.store.get(job_id)
        return self.to_job(record) if record else None

    def list(self, limit: int = 50) -> list[Job]:
        return [self.to_job(record) for record in self.store.recent(limit)]

    def subscribe(self, job_id: str, listener: Listener) -> Callable[[], None]:
        listeners = self._listeners.setdefault(job_id, [])
        listeners.append(listener)

        def unsubscribe() -> None:
            if listener in listeners:
                listeners.remove(listener)
            if not listeners and self._listeners.get(job_id) is listeners:
                del self._listeners[job_id]

        return unsubscribe

    def to_job(self, record: JobRecord) -> Job:
        now = self.now()
        if record.stage == "done":
            progress = 1.0
        elif record.stage == "download":
            progress = record.progress
        elif record.stage in TIME_BASED:
            elapsed = now - (record.stage_started or now)
            progress = self.estimator.stage_progress(record.stage, elapsed, record.duration)
        else:
            progress = 0.0
        overall = self.estimator.overall(record, now)
        eta = self.estimator.eta(record, now)
        # From the database's plain strings to the API's checked values.
        return Job.model_validate(
            {
                "id": record.id,
                "kind": record.kind,
                "title": record.title,
                "stage": record.stage,
                "progress": round(progress, 3),
                "song_id": record.song_id,
                "file": record.file,
                "error": record.error,
                "error_code": record.error_code,
                "with_lyrics": record.with_lyrics,
                "created_at": record.created_at,
                "overall": round(overall, 3) if overall is not None else None,
                "eta": round(eta) if eta is not None else None,
                "can_retry": self._can_retry(record),
                "attempt": record.attempt,
            }
        )

    # After a restart

    def recover(self) -> None:
        """Jobs left running by a server that stopped go back to the queue (or fail clearly)."""
        for record in self.store.unfinished():
            if record.stage == "queued":
                continue
            has_input = bool(record.source and Path(record.source).is_file())
            if record.kind == "export":
                has_input = self.library.folder(str(record.request.get("song_id"))) is not None
            elif not has_input and record.request.get("url"):
                record.source, has_input = None, True
            if not has_input or record.attempt >= MAX_STARTS:
                self.store.update(
                    record.id,
                    stage="error",
                    error_code="interrupted",
                    error="The server stopped while this job was running",
                )
                continue
            self.store.update(
                record.id,
                stage="queued",
                progress=0.0,
                stage_seconds=_kept_seconds(record),
                attempt=record.attempt + 1,
                source=record.source,
                stage_started=None,
            )
        self.purge_old_inputs()

    def purge_old_inputs(self) -> None:
        """Inputs kept for «try again» go after KEEP_DAYS (at start and every day after)."""
        limit = (datetime.now(UTC) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for record in self.store.finished_before(limit):
            folder = self.job_dir(record.id)
            if folder.exists():
                shutil.rmtree(folder, ignore_errors=True)
            if record.source:
                self.store.update(record.id, source=None)

    # The lanes

    async def _lane(
        self,
        pick: Callable[[], JobRecord | None],
        run: Callable[[JobRecord], Coroutine[Any, Any, None]],
        wake: asyncio.Event,
    ) -> None:
        # A lane must outlive any error (a full disk making SQLite fail, say): if it died, every
        # later song would wait in the queue until a restart.
        while True:
            try:
                await self._lane_step(pick, run, wake)
            except Exception:
                logger.exception("the job lane hit an error; it goes on in a moment")
                await asyncio.sleep(LANE_RETRY_SECONDS)

    async def _lane_step(
        self,
        pick: Callable[[], JobRecord | None],
        run: Callable[[JobRecord], Coroutine[Any, Any, None]],
        wake: asyncio.Event,
    ) -> None:
        wake.clear()
        record = pick()
        if record is None:
            await wake.wait()
            return
        task = asyncio.create_task(run(record))
        self._running[record.id] = task
        try:
            await task
        except asyncio.CancelledError:
            current = asyncio.current_task()
            if current is not None and current.cancelling():
                raise
            # Only that job was cancelled: on to the next one. Cancelled before its first
            # step, it could not mark itself, and it would be picked again.
            latest = self.store.get(record.id)
            if record.id in self._cancelled and latest is not None and latest.stage not in TERMINAL:
                self._finish(record.id, stage="cancelled")
        except Exception:
            logger.exception("job %s failed inside the queue", record.id)
            self._finish(
                record.id,
                stage="error",
                error_code="engine_failed",
                error="Something went wrong on the server",
            )
        finally:
            # A link job moves from the download lane to the GPU lane: by now the entry may
            # already be the GPU's, which must stay.
            if self._running.get(record.id) is task:
                del self._running[record.id]
                self._cancelled.discard(record.id)

    async def _run_download(self, record: JobRecord) -> None:
        url = str(record.request["url"])
        self._set_stage(record.id, "download")
        last = [0.0]

        def on_progress(fraction: float) -> None:
            if fraction - last[0] >= 0.02 or fraction >= 1:
                last[0] = fraction
                updated = self.store.update(record.id, progress=round(fraction, 3))
                if updated:
                    self._emit(updated)

        try:
            try:
                info = await self.downloader.probe(url)
                if info.is_live:
                    raise DownloadError("bad_url", "Live streams cannot be made into karaokes")
                if info.duration and info.duration > self.settings.max_duration:
                    limit = round(self.settings.max_duration / 60)
                    raise DownloadError("too_long", f"Songs can last up to {limit} minutes")
                changes: dict[str, Any] = {"duration": info.duration}
                if not record.request.get("title") and (info.track or info.title):
                    changes["title"] = clean_title(str(info.track or info.title))
                if not record.request.get("artist") and info.artist:
                    request = {**record.request, "artist": clean_artist(info.artist)}
                    changes["request"] = request
                updated = self.store.update(record.id, **changes)
                if updated:
                    self._emit(updated)
                path = await self.downloader.download(
                    url, self.job_dir(record.id), on_progress, parts=info.parts
                )
            except asyncio.CancelledError:
                if record.id in self._cancelled:
                    self._finish(record.id, stage="cancelled")
                    return
                raise
        except DownloadError as exc:
            self._failed(
                record.id,
                Outcome(
                    ok=False,
                    code=exc.code,
                    message=str(exc),
                    transient=exc.code == "download_failed",
                ),
            )
            return
        current = self.store.get(record.id)
        assert current is not None
        seconds = dict(current.stage_seconds)
        seconds["download"] = self.now() - (current.stage_started or self.now())
        updated = self.store.update(
            record.id,
            stage="queued",
            progress=0.0,
            source=str(path),
            stage_seconds=seconds,
            stage_started=None,
        )
        assert updated is not None
        self._emit(updated)
        self._wake()

    async def _run_gpu(self, record: JobRecord) -> None:
        folder = self.job_dir(record.id)
        folder.mkdir(parents=True, exist_ok=True)
        if record.kind == "export":
            prepared = self._export_spec(record)
            if prepared is None:
                return
            spec, final = prepared
            self._set_stage(record.id, "video")
        else:
            if not (record.source and Path(record.source).is_file()):  # noqa: ASYNC240 - metadata only
                self._finish(
                    record.id,
                    stage="error",
                    error_code="interrupted",
                    error="The song's file is gone",
                )
                return
            out = folder / "out"
            shutil.rmtree(out, ignore_errors=True)
            options = {k: record.request.get(k) for k in ("language", "lyrics", "lrclib", "artist")}
            spec = {
                "kind": "make",
                "source": record.source,
                "out": str(out),
                "title": record.title,
                **options,
                "fake": self.settings.fake_engine,
            }
            final = None
            self._set_stage(record.id, "separate")
        try:
            outcome = await self.spawner.run(
                record.id, spec, folder / "log.txt", lambda event: self._on_event(record.id, event)
            )
        except asyncio.CancelledError:
            if record.id in self._cancelled:
                self._finish(record.id, stage="cancelled")
                if record.kind == "make":
                    shutil.rmtree(folder / "out", ignore_errors=True)
                else:
                    _drop_partial(Path(str(spec["out"])))
                return
            raise
        if not outcome.ok:
            if record.kind == "export":
                _drop_partial(Path(str(spec["out"])))
            self._failed(record.id, outcome)
            return
        if record.kind == "export":
            assert final is not None
            self._finish_export(record.id, Path(str(spec["out"])), final)
        else:
            self._finish_make(record.id, folder / "out")

    def _export_spec(self, record: JobRecord) -> tuple[dict[str, Any], Path] | None:
        song_id = str(record.request.get("song_id"))
        package = self.library.folder(song_id)
        if package is None:
            self._finish(
                record.id, stage="error", error_code="song_missing", error="The song was deleted"
            )
            return None
        aspect = str(record.request.get("aspect", "16:9"))
        theme = str(record.request.get("theme", "clasico"))
        final = package / "exports" / f"{song_id}-{aspect.replace(':', 'x')}-{theme}.mp4"
        final.parent.mkdir(exist_ok=True)
        # Hidden while it is written, so nobody downloads half a video.
        partial = final.with_name(f".partial-{final.name}")
        spec = {
            "kind": "export",
            "package": str(package),
            "out": str(partial),
            "aspect": aspect,
            "theme": theme,
            "fake": self.settings.fake_engine,
        }
        return spec, final

    def _finish_make(self, job_id: str, out: Path) -> None:
        record = self.store.get(job_id)
        assert record is not None
        song_id = self.library.adopt(out, record.title, job_id=job_id)
        doc = self.library.doc(song_id)
        if record.source:
            Path(record.source).unlink(missing_ok=True)
        self._finish(
            job_id,
            stage="done",
            song_id=song_id,
            source=None,
            duration=doc.duration if doc else record.duration,
        )

    def _finish_export(self, job_id: str, partial: Path, final: Path) -> None:
        if not partial.is_file():  # the song was deleted while it rendered
            _drop_partial(partial)
            self._finish(
                job_id, stage="error", error_code="song_missing", error="The song was deleted"
            )
            return
        partial.replace(final)
        thumb = partial.with_suffix(".jpg")
        if thumb.exists():
            thumb.replace(final.with_suffix(".jpg"))
        self._finish(job_id, stage="done", file=f"exports/{final.name}")

    def _failed(self, job_id: str, outcome: Outcome) -> None:
        record = self.store.get(job_id)
        assert record is not None
        if outcome.transient and record.attempt < MAX_ATTEMPTS:
            logger.warning("job %s failed (%s); trying once more", job_id, outcome.code)
            updated = self.store.update(
                job_id,
                stage="queued",
                progress=0.0,
                stage_started=None,
                attempt=record.attempt + 1,
                stage_seconds=_kept_seconds(record),
            )
            assert updated is not None
            self._emit(updated)
            self._wake()
            return
        self._finish(
            job_id,
            stage="error",
            error_code=outcome.code or "engine_failed",
            error=outcome.message or "The engine failed",
        )

    # Bookkeeping

    def _on_event(self, job_id: str, event: Event) -> None:
        kind = event.get("event")
        if kind == "stage":
            stage = ENGINE_STAGE.get(str(event.get("stage")))
            if stage:
                self._set_stage(job_id, stage)
        elif kind == "lyrics":
            updated = self.store.update(job_id, with_lyrics=True)
            if updated:
                self._emit(updated)
        elif kind == "note":
            logger.info("job %s: %s", job_id, event.get("message"))

    def _set_stage(self, job_id: str, stage: str) -> None:
        record = self.store.get(job_id)
        if record is None or record.stage == stage:
            return
        now = self.now()
        seconds = dict(record.stage_seconds)
        if record.stage_started is not None and record.stage not in ("queued", *TERMINAL):
            seconds[record.stage] = seconds.get(record.stage, 0.0) + now - record.stage_started
        updated = self.store.update(
            job_id, stage=stage, progress=0.0, stage_started=now, stage_seconds=seconds
        )
        assert updated is not None
        self._emit(updated)

    def _finish(self, job_id: str, stage: str, **changes: Any) -> None:
        record = self.store.get(job_id)
        if record is None:
            return
        seconds = dict(record.stage_seconds)
        if record.stage_started is not None and record.stage not in ("queued", *TERMINAL):
            seconds[record.stage] = (
                seconds.get(record.stage, 0.0) + self.now() - record.stage_started
            )
        updated = self.store.update(
            job_id,
            stage=stage,
            stage_seconds=seconds,
            stage_started=None,
            progress=1.0 if stage == "done" else 0.0,
            **changes,
        )
        assert updated is not None
        self._emit(updated)

    def _can_retry(self, record: JobRecord) -> bool:
        if record.stage not in ("error", "cancelled"):
            return False
        if record.kind == "export":
            return self.library.folder(str(record.request.get("song_id"))) is not None
        has_source = bool(record.source and Path(record.source).is_file())
        return has_source or bool(record.request.get("url"))

    def _emit(self, record: JobRecord) -> Job:
        job = self.to_job(record)
        for listener in list(self._listeners.get(record.id, [])):
            listener(job)
        return job

    def _wake(self) -> None:
        for wake in (self._gpu_wake, self._download_wake):
            if wake is not None:
                wake.set()

    async def _tick(self) -> None:
        """Running stages move on with time: tell the listeners every few seconds."""
        while True:
            await asyncio.sleep(TICK_SECONDS)
            try:
                for job_id in list(self._running):
                    record = self.store.get(job_id)
                    if record and record.stage in TIME_BASED and self._listeners.get(job_id):
                        self._emit(record)
            except Exception:
                logger.exception("could not tell the listeners how the jobs go")


def _drop_partial(partial: Path) -> None:
    """The hidden file of an export that did not finish, its thumbnail, and the encoder's own
    scratch file (left when the job is killed mid-encode, see video.encode.run_encoder)."""
    partial.unlink(missing_ok=True)
    partial.with_suffix(".jpg").unlink(missing_ok=True)
    partial.with_name(f".{partial.stem}.part{partial.suffix}").unlink(missing_ok=True)


def _kept_seconds(record: JobRecord) -> dict[str, float]:
    """What a job starting again keeps of its stage times: only a download it will not redo.

    Kept whole, the next run's times would add to them and the progress estimates, which learn
    from finished jobs, would count those stages twice.
    """
    kept = (
        {"download": record.stage_seconds["download"]} if "download" in record.stage_seconds else {}
    )
    return kept
