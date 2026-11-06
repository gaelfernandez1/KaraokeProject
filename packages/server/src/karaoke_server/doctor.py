"""`karaoke-server doctor`: is everything in place, and if not, what to do about it."""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from karaoke_server import autostart
from karaoke_server.config import Settings
from karaoke_server.jobs.child import scope_available
from karaoke_server.network import NetworkState, probe_network

GUIDE = "docs/servidor.md"


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    fix: str = ""
    # Optional checks show «·» instead of «✗» when they are not set up.
    optional: bool = False


def _run(*command: str) -> str:
    try:
        return subprocess.run(
            command, capture_output=True, text=True, timeout=20, check=False
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def tool_checks(settings: Settings) -> list[Check]:
    checks = []
    ffmpeg = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
    checks.append(
        Check(
            "ffmpeg",
            ffmpeg,
            "ffmpeg and ffprobe" if ffmpeg else "not found",
            "sudo apt install ffmpeg",
        )
    )
    if ffmpeg:
        nvenc = "h264_nvenc" in _run("ffmpeg", "-hide_banner", "-encoders")
        checks.append(
            Check(
                "video encoder",
                nvenc,
                "NVENC" if nvenc else "CPU only (slower)",
                "update the NVIDIA driver on Windows",
                optional=True,
            )
        )
    gpu = _run("nvidia-smi", "-L").strip().split(" (UUID")[0]
    checks.append(
        Check(
            "GPU",
            bool(gpu),
            gpu.splitlines()[0] if gpu else "not seen",
            "install the NVIDIA driver for WSL on Windows",
        )
    )
    ytdlp = shutil.which(settings.ytdlp[0]) is not None and shutil.which("node") is not None
    checks.append(
        Check(
            "links (yt-dlp)",
            ytdlp,
            "uvx and node" if ytdlp else "uvx or node missing",
            "install uv and Node 22 (docs/desarrollo.md)",
        )
    )
    separator = Path.home() / ".cache/karaoke/models/audio-separator/vocals_mel_band_roformer.ckpt"
    checks.append(
        Check(
            "models",
            separator.exists(),
            "downloaded" if separator.exists() else "not downloaded yet",
            "karaoke-server prepare --lang gl (or wait: the first song downloads them)",
            optional=True,
        )
    )
    checks.append(
        Check(
            "memory guard",
            scope_available(),
            "each job in a systemd scope" if scope_available() else "no systemd scopes",
            "enable systemd in /etc/wsl.conf ([boot] systemd=true)",
        )
    )
    free = shutil.disk_usage(settings.data_dir if settings.data_dir.exists() else Path.home()).free
    checks.append(
        Check(
            "disk",
            free >= settings.min_free_bytes,
            f"{free / 1024**3:.0f} GB free",
            "free some space on the WSL disk",
        )
    )
    built = settings.web_dir is not None and (settings.web_dir / "index.html").is_file()
    checks.append(
        Check("web app", built, "built" if built else "not built", "pnpm --dir web build")
    )
    return checks


def network_checks(settings: Settings, state: NetworkState) -> list[Check]:
    checks = []
    if state.wsl_mode == "nat":
        checks.append(
            Check(
                "home network",
                False,
                f"WSL is in NAT mode: phones cannot reach {state.home_ip}",
                f"set networkingMode=mirrored in .wslconfig and open port {settings.home_port} "
                f"in the firewall ({GUIDE})",
            )
        )
    elif state.home_ip:
        checks.append(
            Check(
                "home network",
                True,
                f"http://{state.home_ip}:{settings.home_port} (check from a phone)",
                f"if a phone cannot open it, open port {settings.home_port} ({GUIDE})",
            )
        )
    else:
        checks.append(
            Check("home network", False, "no home address found", "connect the laptop to the Wi-Fi")
        )
    if state.tailscale_host is None:
        checks.append(
            Check(
                "outside home",
                False,
                "Tailscale is not running",
                f"optional: install Tailscale and run tailscale serve --bg "
                f"{settings.tunnel_port} ({GUIDE})",
                optional=True,
            )
        )
    elif state.serve_port == settings.tunnel_port:
        checks.append(Check("outside home", True, f"https://{state.tailscale_host}"))
    elif state.serve_port == settings.home_port:
        checks.append(
            Check(
                "outside home",
                False,
                f"Tailscale Serve points at the home port {settings.home_port}: "
                "everyone on the tailnet would count as being at home",
                f"tailscale serve --bg {settings.tunnel_port}",
            )
        )
    else:
        checks.append(
            Check(
                "outside home",
                False,
                "Tailscale Serve is not set up",
                f"tailscale serve --bg {settings.tunnel_port}",
                optional=True,
            )
        )
    return checks


def startup_checks() -> list[Check]:
    shortcut = autostart.status()
    return [
        Check(
            "start with Windows",
            shortcut is not None,
            "installed" if shortcut else "not installed",
            "karaoke-server autostart install",
            optional=True,
        )
    ]


def run_checks(settings: Settings) -> list[Check]:
    return [*tool_checks(settings), *network_checks(settings, probe_network()), *startup_checks()]


def render(checks: list[Check]) -> str:
    lines = []
    for check in checks:
        mark = "✓" if check.ok else ("·" if check.optional else "✗")
        lines.append(f"{mark} {check.name}: {check.detail}")
        if not check.ok and check.fix:
            lines.append(f"    → {check.fix}")
    return "\n".join(lines)
