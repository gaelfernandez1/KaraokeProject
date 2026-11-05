"""Pairing: a device becomes the owner's with a short code shown on one already paired."""

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from karaoke_server.access import (
    COOKIE,
    Caller,
    Owner,
    PairingLockedError,
    Zone,
    caller,
    device_name,
    is_https,
)
from karaoke_server.errors import ApiError
from karaoke_server.library import iso
from karaoke_server.models import Device

router = APIRouter(tags=["devices"])

COOKIE_SECONDS = 365 * 86400


class Me(BaseModel):
    owner: bool
    zone: Zone
    device: Device | None


class PairingUrls(BaseModel):
    home: str | None
    remote: str | None


class PairingOut(BaseModel):
    code: str
    expires_at: str
    urls: PairingUrls


class PairRequest(BaseModel):
    code: str
    name: str | None = None


@router.get("/api/me")
async def me(request: Request) -> Me:
    who: Caller = caller(request)
    return Me(owner=who.owner, zone=who.zone, device=who.device)


@router.post("/api/devices/pairing")
async def start_pairing(request: Request, who: Owner) -> PairingOut:
    services = request.app.state.services
    pairing = services.devices.start_pairing()
    info = services.network.info()

    def link(base: str | None) -> str | None:
        return f"{base}/vincular?code={pairing.code}" if base else None

    return PairingOut(
        code=pairing.code,
        expires_at=iso(pairing.expires_at),
        # A home link phones cannot reach (WSL in NAT mode) would only be a QR that fails.
        urls=PairingUrls(
            home=link(info.home_url) if info.home_reachable else None,
            remote=link(info.remote_url),
        ),
    )


@router.post("/api/devices/pair")
async def pair(body: PairRequest, request: Request, response: Response) -> Device:
    devices = request.app.state.services.devices
    name = body.name or device_name(request.headers.get("user-agent", ""))
    try:
        paired = devices.pair(body.code, name)
    except PairingLockedError as exc:
        raise ApiError(429, "locked", str(exc)) from exc
    if paired is None:
        raise ApiError(422, "bad_code", "That code is wrong or has expired")
    device, token = paired
    response.set_cookie(
        COOKIE,
        token,
        max_age=COOKIE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=is_https(request),
        path="/",
    )
    return device  # type: ignore[no-any-return]


@router.get("/api/devices")
async def list_devices(request: Request, who: Owner) -> list[Device]:
    return request.app.state.services.devices.list()  # type: ignore[no-any-return]


@router.delete("/api/devices/{device_id}", status_code=204)
async def revoke(device_id: str, request: Request, who: Owner) -> Response:
    if not request.app.state.services.devices.revoke(device_id):
        raise ApiError(404, "not_found", "No such device")
    return Response(status_code=204)
