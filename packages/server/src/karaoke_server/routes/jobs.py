"""Making karaokes and exporting videos: the job queue over HTTP."""

import asyncio
import re
import shutil
from collections.abc import AsyncIterable
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent

from karaoke_engine.align.lyrics import parse_lyrics
from karaoke_engine.languages import TWO_LETTERS
from karaoke_engine.subtitles.themes import THEMES_DIR
from karaoke_server.access import Owner, Reader
from karaoke_server.errors import ApiError
from karaoke_server.jobs.intake import IntakeError, media_info, receive_form
from karaoke_server.jobs.queue import JobQueue
from karaoke_server.jobs.titles import clean_title, split_artist
from karaoke_server.models import ExportRequest, Job, MakeRequest

router = APIRouter(tags=["jobs"])

LANGUAGE = re.compile(r"^[a-z]{2,3}$")
# A theme is a file name in THEMES_DIR: nothing that could walk out of it.
THEME = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
LOG_LINES = 200


def _queue(request: Request) -> JobQueue:
    return request.app.state.services.jobs  # type: ignore[no-any-return]


def _make_request(fields: dict[str, str]) -> MakeRequest:
    def text(key: str) -> str | None:
        value = fields.get(key, "").strip()
        return value or None

    language = text("language")
    if not language or not LANGUAGE.match(language):
        raise IntakeError(422, "bad_language", "Choose a language, like gl")
    if language in TWO_LETTERS:
        raise IntakeError(422, "bad_language", f"Write the language as {TWO_LETTERS[language]}")
    lyrics = text("lyrics")
    if lyrics is not None and not parse_lyrics(lyrics):
        raise IntakeError(422, "bad_lyrics", "The lyrics have no sung lines")
    url = text("url")
    if url is not None:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise IntakeError(422, "bad_url", "Links must start with http:// or https://")
    return MakeRequest(
        language=language,
        lyrics=lyrics,
        lrclib=text("lrclib") == "true",
        title=text("title"),
        artist=text("artist"),
        url=url,
    )


@router.post("/api/jobs", status_code=201)
async def create_job(request: Request, who: Owner) -> Job:
    """A song file (multipart `file`) or a link (`url`), with its language and lyrics if any."""
    queue = _queue(request)
    settings = request.app.state.services.settings
    if shutil.disk_usage(settings.jobs_dir).free < settings.min_free_bytes:
        raise ApiError(507, "disk_full", "The laptop is out of disk space")
    job_id = queue.new_id()
    folder = queue.job_dir(job_id)
    try:
        form = await receive_form(
            request.headers, request.stream(), folder, settings.max_upload_bytes
        )
        make = _make_request(form.fields)
        if form.file is None:
            if make.url is None:
                raise IntakeError(422, "bad_form", "Send a song file or a link")
            return queue.submit_make(job_id, make)
        info = await media_info(form.file)
        if not info.has_audio:
            raise IntakeError(422, "no_audio", "That file has no sound we can read")
        if info.duration > settings.max_duration:
            minutes = round(settings.max_duration / 60)
            raise IntakeError(422, "too_long", f"Songs can last up to {minutes} minutes")
        # «01 - Title» is a track number, not an artist: cleaned before and after the split.
        name = clean_title(Path(form.filename or "song").stem)
        artist_from_name, title_from_name = split_artist(name)
        title = info.title or clean_title(title_from_name)
        if make.artist is None and (info.artist or artist_from_name):
            make = make.model_copy(update={"artist": info.artist or artist_from_name})
        return queue.submit_make(
            job_id, make, source=form.file, duration=info.duration, title=title
        )
    except IntakeError as exc:
        shutil.rmtree(folder, ignore_errors=True)
        raise ApiError(exc.status, exc.code, str(exc)) from exc
    except BaseException:
        # A client gone, a cancel, a broken body, ffprobe missing: never an empty job folder.
        shutil.rmtree(folder, ignore_errors=True)
        raise


@router.get("/api/jobs")
async def list_jobs(request: Request, who: Reader) -> list[Job]:
    return _queue(request).list()


@router.get("/api/jobs/{job_id}")
async def get_job(job_id: str, request: Request, who: Reader) -> Job:
    job = _queue(request).get(job_id)
    if job is None:
        raise ApiError(404, "not_found", "No such job")
    return job


@router.delete("/api/jobs/{job_id}", status_code=204)
async def cancel_job(job_id: str, request: Request, who: Owner) -> Response:
    queue = _queue(request)
    if queue.get(job_id) is None:
        raise ApiError(404, "not_found", "No such job")
    await queue.cancel(job_id)
    return Response(status_code=204)


@router.post("/api/jobs/{job_id}/retry")
async def retry_job(job_id: str, request: Request, who: Owner) -> Job:
    queue = _queue(request)
    if queue.get(job_id) is None:
        raise ApiError(404, "not_found", "No such job")
    job = queue.retry(job_id)
    if job is None:
        raise ApiError(409, "not_retryable", "This job cannot be tried again")
    return job


@router.get("/api/jobs/{job_id}/log", response_class=PlainTextResponse)
async def job_log(job_id: str, request: Request, who: Owner) -> str:
    queue = _queue(request)
    if queue.get(job_id) is None:
        raise ApiError(404, "not_found", "No such job")
    log = queue.job_dir(job_id) / "log.txt"
    if not log.is_file():
        return ""
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-LOG_LINES:])


def _existing(job_id: str, request: Request, who: Reader) -> Job:
    job = _queue(request).get(job_id)
    if job is None:
        raise ApiError(404, "not_found", "No such job")
    return job


@router.get("/api/jobs/{job_id}/events", response_class=EventSourceResponse)
async def job_events(
    job: Annotated[Job, Depends(_existing)], request: Request
) -> AsyncIterable[ServerSentEvent]:
    """The job now and after every change."""
    queue = _queue(request)
    updates: asyncio.Queue[Job] = asyncio.Queue()
    unsubscribe = queue.subscribe(job.id, updates.put_nowait)
    try:
        # Read again once subscribed: a short job may have ended since the 404 check.
        now = queue.get(job.id) or job
        yield ServerSentEvent(event="job", data=now.model_dump(mode="json"))
        while True:
            update = await updates.get()
            yield ServerSentEvent(event="job", data=update.model_dump(mode="json"))
    finally:
        unsubscribe()


@router.post("/api/songs/{song_id}/exports", status_code=201)
async def export_video(song_id: str, body: ExportRequest, request: Request, who: Owner) -> Job:
    if not THEME.match(body.theme) or not (THEMES_DIR / f"{body.theme}.json").is_file():
        raise ApiError(422, "bad_theme", f"There is no lyrics style called {body.theme}")
    job = _queue(request).submit_export(song_id, body)
    if job is None:
        raise ApiError(404, "not_found", "No such song")
    return job
