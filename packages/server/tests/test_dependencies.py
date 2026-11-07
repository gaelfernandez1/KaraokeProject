import inspect
from collections.abc import Iterator

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from starlette.routing import BaseRoute

from karaoke_server.config import Settings
from karaoke_server.db import Database


def _api_routes(routes: list[BaseRoute]) -> Iterator[APIRoute]:
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        included = getattr(route, "original_router", None)  # an include_router()
        if included is not None:
            yield from _api_routes(included.routes)


def _calls(dependant: Dependant) -> Iterator[object]:
    for dependency in dependant.dependencies:
        yield dependency.call
        yield from _calls(dependency)


def test_every_dependency_runs_on_the_event_loop(settings: Settings, db: Database) -> None:
    # FastAPI runs a plain `def` dependency in a thread pool, and the database connection belongs
    # to the event loop's thread: six players asking for their jobs at once broke it (500s).
    from karaoke_server.app import build_services, create_app

    app = create_app(settings, services=build_services(settings, db=db))
    blocking = {
        f"{route.path}: {getattr(call, '__name__', call)}"
        for route in _api_routes(app.routes)
        for call in _calls(route.dependant)
        if not inspect.iscoroutinefunction(call)
    }
    assert any("/api/jobs/{job_id}/events" in r.path for r in _api_routes(app.routes))
    assert blocking == set()
