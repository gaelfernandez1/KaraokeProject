"""Server settings: where the data lives, the two ports and the limits for new karaokes."""

import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

GIB = 1024**3

# yt-dlp changes every week to keep up with the sites, so it runs at its latest release, apart
# from the project's own environment. Node is the JavaScript runtime YouTube now requires.
YTDLP = ("uvx", "--from", "yt-dlp[default]@latest", "yt-dlp", "--js-runtimes", "node")

REPO = Path(__file__).resolve().parents[4]


def _flag(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _default_data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "karaoke"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    home_host: str = "0.0.0.0"  # noqa: S104 - the home socket must reach phones
    home_port: int = 8765
    # Tunnels (Tailscale Serve) connect here; everything on this port counts as remote.
    tunnel_port: int = 8766
    web_dir: Path | None = field(default_factory=lambda: REPO / "web" / "build")
    max_upload_bytes: int = 2 * GIB
    max_duration: float = 20 * 60.0
    min_free_bytes: int = 2 * GIB
    # Lets anyone on the home network create, edit and delete, without pairing.
    open_home: bool = False
    fake_engine: bool = False
    # Memory cap for each job's process; None works it out from the machine's RAM.
    memory_max: int | None = None
    # Swap the job may use beyond that; None leaves it to the system (WSL's swap file).
    memory_swap_max: int | None = None
    ytdlp: tuple[str, ...] = YTDLP
    backup_dir: Path | None = None

    @classmethod
    def from_env(cls, **overrides: Any) -> "Settings":
        env = os.environ
        port = int(env.get("KARAOKE_PORT") or 8765)
        backup = env.get("KARAOKE_BACKUP_DIR")
        values: dict[str, Any] = {
            "data_dir": Path(env["KARAOKE_DATA"]) if env.get("KARAOKE_DATA") else None,
            "home_port": port,
            "tunnel_port": port + 1,
            "open_home": _flag(env.get("KARAOKE_OPEN_HOME")),
            "fake_engine": _flag(env.get("KARAOKE_FAKE_ENGINE")),
            "backup_dir": Path(backup) if backup else None,
        }
        values.update({k: v for k, v in overrides.items() if v is not None})
        if values["data_dir"] is None:
            values["data_dir"] = _default_data_dir()
        if "home_port" in overrides and "tunnel_port" not in overrides:
            values["tunnel_port"] = values["home_port"] + 1
        known = {f.name for f in fields(cls)}
        unknown = set(values) - known
        if unknown:
            raise TypeError(f"unknown settings: {', '.join(sorted(unknown))}")
        return cls(**values)

    @property
    def library_dir(self) -> Path:
        return self.data_dir / "library"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def trash_dir(self) -> Path:
        return self.data_dir / "trash"

    @property
    def tmp_dir(self) -> Path:
        """Scratch space on disk: /tmp is in RAM on this machine."""
        return self.data_dir / "tmp"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "karaoke.db"

    def ensure_dirs(self) -> None:
        for path in (self.library_dir, self.jobs_dir, self.trash_dir, self.tmp_dir, self.logs_dir):
            path.mkdir(parents=True, exist_ok=True)
