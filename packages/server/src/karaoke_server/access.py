"""Who is asking: the network zone a request comes from, and the devices paired with the server.

- local: the laptop itself (the TV). It owns the server.
- home: a private address on the home network. It may browse, sing and join parties.
- remote: anything else, and everything through a tunnel (Tailscale Serve connects to the
  tunnel port), or carrying a proxy header. Only paired devices get in.

A paired device has a random token in an HttpOnly cookie; the server keeps only its hash.
"""

import hashlib
import ipaddress
import re
import secrets
import subprocess
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import Depends, Request

from karaoke_server.config import Settings
from karaoke_server.db import Database
from karaoke_server.errors import ApiError
from karaoke_server.library import iso
from karaoke_server.models import Device

Zone = Literal["local", "home", "remote"]

# A request that went through a proxy may not be what it seems: it counts as remote.
PROXY_HEADERS = (
    "x-forwarded-for",
    "forwarded",
    "x-real-ip",
    "cf-connecting-ip",
    "tailscale-user-login",
    "tailscale-funnel-request",
)
# Private and link-local ranges, IPv4 and IPv6.
_HOME = "10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 169.254.0.0/16 fc00::/7 fe80::/10"
_HOME_NETWORKS = [ipaddress.ip_network(n) for n in _HOME.split()]

# No vowels, so a code never spells a word (the party codes use the same letters).
CODE_LETTERS = "BCDFGHJKLMNPQRSTVWXZ"
PAIRING_SECONDS = 600
MAX_FAILURES = 10
# From all clients together: a code has about 35 bits, so this still makes guessing hopeless.
MAX_FAILURES_ALL = 100
COOKIE = "karaoke_device"


def classify(
    client_host: str | None,
    server_port: int,
    headers: Mapping[str, str],
    settings: Settings,
    gateways: frozenset[str],
) -> Zone:
    if server_port == settings.tunnel_port:
        return "remote"
    if any(name in headers for name in PROXY_HEADERS):
        return "remote"
    try:
        address = ipaddress.ip_address(client_host or "")
    except ValueError:
        return "remote"
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    if address.is_loopback:
        # The laptop's browser calls it localhost. Another name that reaches loopback is a page
        # whose domain was pointed here (DNS rebinding): not the owner.
        return "local" if _loopback_name(headers.get("host")) else "remote"
    # Under WSL's NAT, whatever Windows forwards (portproxy, a proxy app) arrives from the
    # gateway: it could be anyone.
    if str(address) in gateways:
        return "remote"
    if any(address in network for network in _HOME_NETWORKS):
        return "home"
    return "remote"


def _loopback_name(host: str | None) -> bool:
    """Whether a Host header names this machine's loopback (none at all: not a browser)."""
    if host is None:
        return True
    name = urlsplit(f"//{host}").hostname or ""
    if name == "localhost" or name.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


def wsl_networking_mode() -> str | None:
    try:
        result = subprocess.run(
            ["wslinfo", "--networking-mode"], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None if result.returncode == 0 else None


def wsl_gateways(
    mode: Callable[[], str | None] = wsl_networking_mode, route: Path = Path("/proc/net/route")
) -> frozenset[str]:
    """The Windows side of WSL's NAT network, from which forwarded connections arrive."""
    if mode() != "nat":
        return frozenset()
    gateways = set()
    try:
        rows = route.read_text().splitlines()[1:]
    except OSError:
        return frozenset()
    for row in rows:
        fields = row.split()
        if len(fields) > 2 and fields[1] == "00000000" and fields[2] != "00000000":
            gateways.add(str(ipaddress.IPv4Address(bytes.fromhex(fields[2])[::-1])))
    return frozenset(gateways)


class PairingLockedError(RuntimeError):
    """Too many wrong codes lately: pairing waits a few minutes."""


@dataclass(frozen=True)
class Pairing:
    code: str
    expires_at: float


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Devices:
    def __init__(self, db: Database, now: Callable[[], float] = time.time) -> None:
        self.db = db
        self.now = now
        # Wrong codes per client: one phone guessing locks itself out, not the owner.
        self._failures: dict[str, list[float]] = {}

    def start_pairing(self) -> Pairing:
        """A code for one device to pair with (stored, so `karaoke-server pair` works too)."""
        code = "".join(secrets.choice(CODE_LETTERS) for _ in range(8))
        expires = self.now() + PAIRING_SECONDS
        self.db.execute("DELETE FROM pairings WHERE expires_at <= ?", (self.now(),))
        self.db.execute("INSERT INTO pairings (code, expires_at) VALUES (?, ?)", (code, expires))
        return Pairing(code, expires)

    def pair(self, code: str, name: str, client: str = "") -> tuple[Device, str] | None:
        """Exchanges a pairing code for a device and its token (the only time it is seen).

        `client` says who is asking (zone and address): too many wrong codes lock that client
        out for a while, and the whole server only after many more (MAX_FAILURES_ALL).
        """
        now = self.now()
        recent = now - PAIRING_SECONDS
        self._failures = {
            who: kept
            for who, times in self._failures.items()
            if (kept := [t for t in times if t > recent])
        }
        mine = self._failures.get(client, [])
        everyone = sum(len(times) for times in self._failures.values())
        if len(mine) >= MAX_FAILURES or everyone >= MAX_FAILURES_ALL:
            raise PairingLockedError("too many wrong codes; try again in a few minutes")
        clean = re.sub(r"[\s-]", "", code).upper()
        # Taken in one statement, so a code is never used twice.
        if not self.db.execute(
            "DELETE FROM pairings WHERE code = ? AND expires_at > ?", (clean, now)
        ):
            self._failures.setdefault(client, []).append(now)
            return None
        token = secrets.token_urlsafe(32)
        device = Device(
            id=secrets.token_hex(6),
            name=(name.strip() or "Device")[:60],
            created_at=iso(now),
            last_seen=iso(now),
        )
        self.db.execute(
            "INSERT INTO devices (id, name, token_hash, created_at, last_seen) "
            "VALUES (?, ?, ?, ?, ?)",
            (device.id, device.name, _hash(token), device.created_at, device.last_seen),
        )
        return device, token

    def verify(self, token: str) -> Device | None:
        if not token:
            return None
        rows = self.db.query("SELECT * FROM devices WHERE token_hash = ?", (_hash(token),))
        if not rows:
            return None
        device = Device(**{k: rows[0][k] for k in ("id", "name", "created_at", "last_seen")})
        seen = iso(self.now())
        # Once a minute is plenty for "last used".
        if seen[:16] != device.last_seen[:16]:
            self.db.execute("UPDATE devices SET last_seen = ? WHERE id = ?", (seen, device.id))
        return device

    def list(self) -> list[Device]:
        rows = self.db.query(
            "SELECT id, name, created_at, last_seen FROM devices ORDER BY created_at"
        )
        return [Device(**dict(row)) for row in rows]

    def revoke(self, device_id: str) -> bool:
        return self.db.execute("DELETE FROM devices WHERE id = ?", (device_id,)) > 0


_SYSTEMS = (
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Android", "Android"),
    ("CrOS", "Chromebook"),
    ("Windows", "Windows"),
    ("Macintosh", "Mac"),
    ("Linux", "Linux"),
)
_BROWSERS = (
    ("Edg/", "Edge"),
    ("SamsungBrowser", "Samsung Internet"),
    ("Firefox/", "Firefox"),
    ("FxiOS", "Firefox"),
    ("CriOS", "Chrome"),
    ("Chrome/", "Chrome"),
    ("Safari/", "Safari"),
)


def device_name(user_agent: str) -> str:
    """A name a person recognises in the list of paired devices, e.g. «iPhone · Safari»."""
    system = next((name for key, name in _SYSTEMS if key in user_agent), None)
    browser = next((name for key, name in _BROWSERS if key in user_agent), None)
    parts = [p for p in (system, browser) if p]
    return " · ".join(parts) if parts else "Device"


# What request handlers depend on.


@dataclass(frozen=True)
class Caller:
    zone: Zone
    device: Device | None
    owner: bool


def caller(request: Request) -> Caller:
    services = request.app.state.services
    server = request.scope.get("server") or ("", 0)
    zone = classify(
        request.client.host if request.client else None,
        int(server[1] or 0),
        request.headers,
        services.settings,
        services.gateways,
    )
    device = services.devices.verify(request.cookies.get(COOKIE, ""))
    owner = (
        zone == "local" or device is not None or (zone == "home" and services.settings.open_home)
    )
    return Caller(zone, device, owner)


def require_reader(who: Annotated[Caller, Depends(caller)]) -> Caller:
    """The library is open to the home network and to paired devices."""
    if not (who.owner or who.zone == "home"):
        raise ApiError(403, "not_paired", "This device is not paired with the server")
    return who


def require_owner(who: Annotated[Caller, Depends(caller)]) -> Caller:
    if not who.owner:
        raise ApiError(403, "not_owner", "Only a paired device can do this")
    return who


def is_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"


def same_origin(request: Request) -> None:
    """Another site cannot make a browser change anything here (with SameSite cookies, too)."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    origin = request.headers.get("origin")
    if origin is None:
        return
    hosts = {request.headers.get("host"), request.headers.get("x-forwarded-host")}
    if urlsplit(origin).netloc not in hosts - {None}:
        raise ApiError(403, "bad_origin", "Requests must come from the karaoke app itself")


Reader = Annotated[Caller, Depends(require_reader)]
Owner = Annotated[Caller, Depends(require_owner)]
