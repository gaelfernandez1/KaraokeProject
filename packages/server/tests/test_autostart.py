import os
import shutil
import subprocess
from pathlib import Path

from karaoke_server.autostart import shortcut_command, shortcut_script
from karaoke_server.config import REPO


def test_shortcut_command() -> None:
    target, arguments = shortcut_command(Path("/home/ana/KaraokeProject"), "Ubuntu")
    assert target == r"C:\Windows\System32\conhost.exe"
    assert arguments == (
        "--headless wsl.exe -d Ubuntu --cd /home/ana/KaraokeProject -- scripts/serve-forever.sh"
    )


def test_shortcut_script_quotes_paths() -> None:
    script = shortcut_script(r"C:\Users\ana\Start Menu\Karaoke server.lnk", "C:\\x.exe", "a 'b'")
    assert "CreateShortcut('C:\\Users\\ana\\Start Menu\\Karaoke server.lnk')" in script
    assert "Arguments = 'a ''b'''" in script
    assert "WindowStyle = 7" in script


def test_serve_forever_reads_the_settings_file_and_stops_on_purpose(tmp_path: Path) -> None:
    """Started from Windows there is no login shell: the settings come from a file of their own."""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy(REPO / "scripts" / "serve-forever.sh", repo / "scripts")
    server = repo / ".venv" / "bin" / "karaoke-server"
    server.parent.mkdir(parents=True)
    server.write_text('#!/bin/sh\necho "backups in $KARAOKE_BACKUP_DIR"\nexit 0\n')
    server.chmod(0o755)
    config = tmp_path / "config" / "karaoke"
    config.mkdir(parents=True)
    (config / "server.env").write_text("KARAOKE_BACKUP_DIR=/mnt/d/copias\n")
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "KARAOKE_DATA": str(tmp_path / "data"),
    }
    done = subprocess.run(
        ["bash", str(repo / "scripts" / "serve-forever.sh")], env=env, timeout=20, check=False
    )
    assert done.returncode == 0
    log = (tmp_path / "data" / "logs" / "forever.log").read_text()
    assert "backups in /mnt/d/copias" in log
