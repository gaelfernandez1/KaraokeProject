"""Starting with Windows: a hidden shortcut in the user's Startup folder that runs the server.

WSL stops its virtual machine soon after the last Windows program using it goes, even with
systemd services running (microsoft/WSL#13416), so the server is started from Windows and its
own process keeps WSL up. `conhost --headless` runs it without a window. No admin rights.
"""

import os
import subprocess
from pathlib import Path

NAME = "Karaoke server.lnk"
CONHOST = r"C:\Windows\System32\conhost.exe"


def shortcut_command(repo: Path, distro: str) -> tuple[str, str]:
    return CONHOST, f"--headless wsl.exe -d {distro} --cd {repo} -- scripts/serve-forever.sh"


def _quote(text: str) -> str:
    """A PowerShell single-quoted string."""
    return "'" + text.replace("'", "''") + "'"


def shortcut_script(path: str, target: str, arguments: str) -> str:
    return "; ".join(
        [
            "$shell = New-Object -ComObject WScript.Shell",
            f"$link = $shell.CreateShortcut({_quote(path)})",
            f"$link.TargetPath = {_quote(target)}",
            f"$link.Arguments = {_quote(arguments)}",
            # Minimised, in case a window shows up after all.
            "$link.WindowStyle = 7",
            "$link.Description = 'Starts the karaoke server in WSL'",
            "$link.Save()",
        ]
    )


def _powershell(script: str) -> str:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return result.stdout.strip()


def startup_dir() -> Path:
    windows = _powershell("[Environment]::GetFolderPath('Startup')")
    linux = subprocess.run(["wslpath", "-u", windows], capture_output=True, text=True, check=True)
    return Path(linux.stdout.strip())


def install(repo: Path, distro: str | None = None) -> Path:
    distro = distro or os.environ.get("WSL_DISTRO_NAME") or "Ubuntu"
    folder = startup_dir()
    windows_path = _powershell("[Environment]::GetFolderPath('Startup')") + "\\" + NAME
    target, arguments = shortcut_command(repo, distro)
    _powershell(shortcut_script(windows_path, target, arguments))
    return folder / NAME


def remove() -> bool:
    path = startup_dir() / NAME
    if not path.exists():
        return False
    path.unlink()
    return True


def status() -> Path | None:
    try:
        path = startup_dir() / NAME
    except (OSError, subprocess.SubprocessError):
        return None
    return path if path.exists() else None
