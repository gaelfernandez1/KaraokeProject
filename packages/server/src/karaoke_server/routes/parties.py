"""Party mode over HTTP: the same routes and answers as the web's development stand-in."""

import asyncio
from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel

from karaoke_server.access import Reader
from karaoke_server.errors import ApiError
from karaoke_server.models import (
    Joined,
    PartyCommand,
    PartyCreated,
    PartySettings,
    PartyState,
    Playback,
    QueueItem,
    QueueItemState,
)
from karaoke_server.parties import Parties

router = APIRouter(tags=["parties"])


class JoinRequest(BaseModel):
    name: str


class QueueRequest(BaseModel):
    song_id: str


class AdvanceRequest(BaseModel):
    item_id: str
    state: QueueItemState


def _parties(request: Request) -> Parties:
    return request.app.state.services.parties  # type: ignore[no-any-return]


def _who(request: Request) -> str:
    """The host or guest token: a Bearer header, or `?token=` (EventSource sends no headers)."""
    header = request.headers.get("authorization", "")
    token = header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else ""
    return token or request.query_params.get("token", "")


async def _party(code: str, request: Request, who: Reader) -> PartyState:
    state = _parties(request).get(code)
    if state is None:
        raise ApiError(404, "not_found", "No such party")
    return state


Party = Annotated[PartyState, Depends(_party)]


def _done(ok: bool) -> Response:
    if not ok:
        raise ApiError(403, "not_allowed", "Not allowed")
    return Response(status_code=204)


@router.post("/api/parties", status_code=201)
async def create_party(request: Request, who: Reader) -> PartyCreated:
    return _parties(request).create()


@router.get("/api/parties/{code}")
async def get_party(party: Party) -> PartyState:
    return party


@router.delete("/api/parties/{code}", status_code=204)
async def end_party(party: Party, request: Request) -> Response:
    """Only the TV (the host token) ends its party; the phones are told and their streams end."""
    return _done(_parties(request).end(party.code, _who(request)))


@router.get("/api/parties/{code}/events", response_class=EventSourceResponse)
async def party_events(party: Party, request: Request) -> AsyncIterable[ServerSentEvent]:
    """The full state at once and after every change; commands go to the TV only; `ended`
    when the TV ends the party (or it expires), and then the stream closes."""
    queue: asyncio.Queue[ServerSentEvent | None] = asyncio.Queue()

    def listener(event: str, data: BaseModel) -> None:
        queue.put_nowait(ServerSentEvent(event=event, data=data.model_dump(mode="json")))
        if event == "ended":
            queue.put_nowait(None)  # and the stream ends: there is nothing more to follow

    unsubscribe = _parties(request).subscribe(party.code, _who(request) or None, listener)
    try:
        while (event := await queue.get()) is not None:
            yield event
    finally:
        if unsubscribe:
            unsubscribe()


@router.post("/api/parties/{code}/guests", status_code=201)
async def join(party: Party, body: JoinRequest, request: Request) -> Joined:
    joined = _parties(request).join(party.code, body.name)
    if joined is None:
        raise ApiError(422, "bad_name", "A name is needed (or the party is full)")
    return joined


@router.post("/api/parties/{code}/queue", status_code=201)
async def enqueue(party: Party, body: QueueRequest, request: Request) -> QueueItem:
    item = _parties(request).enqueue(party.code, _who(request), body.song_id)
    if item is None:
        raise ApiError(403, "not_allowed", "Not allowed")
    return item


@router.delete("/api/parties/{code}/queue/{item_id}", status_code=204)
async def remove(party: Party, item_id: str, request: Request) -> Response:
    return _done(_parties(request).remove(party.code, _who(request), item_id))


@router.post("/api/parties/{code}/promote/{item_id}", status_code=204)
async def promote(party: Party, item_id: str, request: Request) -> Response:
    return _done(_parties(request).promote(party.code, _who(request), item_id))


@router.put("/api/parties/{code}/advance", status_code=204)
async def advance(party: Party, body: AdvanceRequest, request: Request) -> Response:
    return _done(_parties(request).advance(party.code, _who(request), body.item_id, body.state))


@router.post("/api/parties/{code}/commands", status_code=204)
async def command(party: Party, body: PartyCommand, request: Request) -> Response:
    return _done(_parties(request).command(party.code, _who(request), body))


@router.put("/api/parties/{code}/playback", status_code=204)
async def playback(party: Party, body: Playback, request: Request) -> Response:
    return _done(_parties(request).publish_playback(party.code, _who(request), body))


@router.put("/api/parties/{code}/settings", status_code=204)
async def settings(party: Party, body: PartySettings, request: Request) -> Response:
    return _done(_parties(request).update_settings(party.code, _who(request), body))
