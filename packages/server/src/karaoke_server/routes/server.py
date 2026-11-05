"""About the server itself: where phones can reach it, and whether it is up."""

from importlib import metadata

from fastapi import APIRouter, Request
from pydantic import BaseModel

from karaoke_server.access import Reader
from karaoke_server.network import ServerInfo

router = APIRouter(tags=["server"])


class Health(BaseModel):
    ok: bool
    version: str


@router.get("/api/server")
async def server_info(request: Request, who: Reader) -> ServerInfo:
    return request.app.state.services.network.info()  # type: ignore[no-any-return]


@router.get("/api/health")
async def health() -> Health:
    return Health(ok=True, version=metadata.version("karaoke-server"))
