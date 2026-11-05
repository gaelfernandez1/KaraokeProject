"""The FastAPI app: the API, the package files and the web app, on one port per zone."""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from importlib import metadata

from fastapi import Depends, FastAPI, Request, Response

from karaoke_server.access import Devices, same_origin, wsl_gateways
from karaoke_server.backup import backup_daily
from karaoke_server.config import Settings
from karaoke_server.db import Database
from karaoke_server.errors import ApiError, api_error_handler
from karaoke_server.jobs.child import ProcessSpawner
from karaoke_server.jobs.download import YtDlp
from karaoke_server.jobs.queue import JobQueue
from karaoke_server.jobs.store import JobStore
from karaoke_server.library import Library
from karaoke_server.network import Network, NetworkState
from karaoke_server.parties import Parties
from karaoke_server.routes import devices, jobs, media, parties, server, songs, web
from karaoke_server.services import Services

logger = logging.getLogger(__name__)


def build_services(
    settings: Settings,
    *,
    db: Database | None = None,
    network_state: NetworkState | None = None,
    gateways: frozenset[str] | None = None,
) -> Services:
    settings.ensure_dirs()
    if db is None:
        db = Database(settings.db_path)
        db.migrate()
    library = Library(settings, db)
    rooms = Parties(db, library)
    rooms.load()
    return Services(
        settings=settings,
        db=db,
        library=library,
        devices=Devices(db),
        network=Network(settings, network_state),
        gateways=wsl_gateways() if gateways is None else gateways,
        parties=rooms,
        jobs=JobQueue(
            settings, JobStore(db), library, ProcessSpawner(settings), YtDlp(settings.ytdlp)
        ),
    )


async def _tidy_daily(services: Services) -> None:
    """The server may run for weeks: old trash and old job inputs go once a day."""
    while True:
        try:
            purged = await asyncio.to_thread(services.library.purge_trash)
            if purged:
                logger.info("emptied %s songs deleted over 30 days ago", purged)
            # On the loop: it uses the database, whose connection lives here.
            services.jobs.purge_old_inputs()
        except Exception:
            logger.exception("could not tidy the trash and the old jobs")
        await asyncio.sleep(86400)


def create_app(settings: Settings, *, services: Services | None = None) -> FastAPI:
    services = services or build_services(settings)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        tasks = [
            asyncio.create_task(services.network.refresh_forever()),
            asyncio.create_task(backup_daily(services.settings, services.db)),
            asyncio.create_task(_tidy_daily(services)),
        ]
        await services.jobs.start()
        try:
            yield
        finally:
            await services.jobs.stop()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(
        title="Karaoke server",
        version=metadata.version("karaoke-server"),
        lifespan=lifespan,
        dependencies=[Depends(same_origin)],
        # One schema per model, the same for requests and answers: simpler generated TS types.
        separate_input_output_schemas=False,
    )
    app.state.services = services
    app.add_exception_handler(ApiError, api_error_handler)

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    for module in (songs, media, devices, server, parties, jobs):
        app.include_router(module.router)
    # Last: it answers every other GET with the web app.
    app.include_router(web.router)
    return app
