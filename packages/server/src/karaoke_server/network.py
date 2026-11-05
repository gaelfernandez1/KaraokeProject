"""Where phones can reach the server: the home address for the party QR and the Tailscale URL.

Under WSL the answers live on the Windows side, so they are looked up now and then in the
background (calls to .exe files take a moment) and never while a request waits.
"""

import asyncio
import contextlib
import ipaddress
import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel

from karaoke_server.access import wsl_networking_mode
from karaoke_server.config import Settings

logger = logging.getLogger(__name__)

TAILSCALE_EXE = Path("/mnt/c/Program Files/Tailscale/tailscale.exe")
REFRESH_SECONDS = 60


class ServerInfo(BaseModel):
    """Addresses of the server; `url` is the one for the party QR (the home network's)."""

    url: str
    home_url: str | None
    remote_url: str | None
    # False when phones cannot get in through the home address (WSL in NAT mode).
    home_reachable: bool


@dataclass(frozen=True)
class NetworkState:
    wsl_mode: str | None
    home_ip: str | None
    tailscale_host: str | None
    # The local port Tailscale Serve sends its HTTPS traffic to, if it is set up.
    serve_port: int | None


def pick_home_ip(ip_addr_output: str) -> str | None:
    """The best home-network IPv4 in `ip -4 -o addr` output: 192.168 or 10 first, then 172.16."""
    found: list[ipaddress.IPv4Address] = []
    for line in ip_addr_output.splitlines():
        fields = line.split()
        if "inet" not in fields:
            continue
        address = ipaddress.IPv4Interface(fields[fields.index("inet") + 1]).ip
        if address.is_private and not (address.is_loopback or address.is_link_local):
            found.append(address)
    rank = {True: 0, False: 1}
    found.sort(key=lambda a: rank[a not in ipaddress.IPv4Network("172.16.0.0/12")])
    return str(found[0]) if found else None


def tailscale_host(status_json: str) -> str | None:
    try:
        status = json.loads(status_json)
    except ValueError:
        return None
    if status.get("BackendState") != "Running":
        return None
    name = str((status.get("Self") or {}).get("DNSName") or "").rstrip(".")
    return name or None


def serve_target_port(serve_json: str) -> int | None:
    """The local port the HTTPS root of `tailscale serve` proxies to."""
    try:
        config = json.loads(serve_json or "{}")
    except ValueError:
        return None
    for site in (config.get("Web") or {}).values():
        proxy = ((site.get("Handlers") or {}).get("/") or {}).get("Proxy")
        if proxy:
            target = proxy if "://" in proxy else f"http://{proxy}"
            port = urlsplit(target).port
            if port:
                return port
    return None


def _run(command: list[str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout if result.returncode == 0 else ""


def tailscale_command() -> list[str] | None:
    found = shutil.which("tailscale")
    if found:
        return [found]
    return [str(TAILSCALE_EXE)] if TAILSCALE_EXE.exists() else None


def windows_home_ip() -> str | None:
    """Windows' own address on the home network (the adapter with a default gateway)."""
    script = (
        "Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null -and "
        "$_.NetAdapter.Status -eq 'Up' } | ForEach-Object { $_.IPv4Address.IPAddress }"
    )
    output = _run(["powershell.exe", "-NoProfile", "-Command", script])
    for line in output.split():
        with contextlib.suppress(ValueError):
            if ipaddress.IPv4Address(line.strip()).is_private:
                return line.strip()
    return None


def probe_network() -> NetworkState:
    mode = wsl_networking_mode()
    home = windows_home_ip() if mode == "nat" else pick_home_ip(_run(["ip", "-4", "-o", "addr"]))
    host = port = None
    tailscale = tailscale_command()
    if tailscale:
        host = tailscale_host(_run([*tailscale, "status", "--json"]))
        if host:
            port = serve_target_port(_run([*tailscale, "serve", "status", "--json"]))
    return NetworkState(mode, home, host, port)


class Network:
    def __init__(self, settings: Settings, state: NetworkState | None = None) -> None:
        self.settings = settings
        self.state = state or NetworkState(None, None, None, None)
        # A given state is fixed (tests); otherwise it is looked up in the background.
        self._probe = state is None

    def info(self) -> ServerInfo:
        port = self.settings.home_port
        home = f"http://{self.state.home_ip}:{port}" if self.state.home_ip else None
        remote = None
        if self.state.tailscale_host and self.state.serve_port == self.settings.tunnel_port:
            remote = f"https://{self.state.tailscale_host}"
        return ServerInfo(
            url=home or f"http://localhost:{port}",
            home_url=home,
            remote_url=remote,
            home_reachable=home is not None and self.state.wsl_mode != "nat",
        )

    async def refresh_forever(self) -> None:
        if not self._probe:
            return
        while True:
            try:
                self.state = await asyncio.to_thread(probe_network)
            except Exception:
                logger.exception("could not look up the network addresses")
            await asyncio.sleep(REFRESH_SECONDS)
