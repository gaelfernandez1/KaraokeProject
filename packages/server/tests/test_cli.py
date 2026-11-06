import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from karaoke_server.cli import main

from .conftest import write_package
from .live import free_port


def test_pair_command_prints_a_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from karaoke_server import network

    monkeypatch.setattr(
        network, "probe_network", lambda: network.NetworkState(None, None, None, None)
    )
    assert main(["--data", str(tmp_path), "pair"]) == 0
    out = capsys.readouterr().out
    assert any(len(word) == 8 and word.isupper() for word in out.split())


def test_pair_command_prints_the_links_to_open(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from karaoke_server import network

    state = network.NetworkState("mirrored", "192.168.1.20", "laptop.tail.ts.net", 8766)
    monkeypatch.setattr(network, "probe_network", lambda: state)
    assert main(["--data", str(tmp_path), "pair"]) == 0
    out = capsys.readouterr().out
    assert "http://192.168.1.20:8765/vincular?code=" in out
    assert "https://laptop.tail.ts.net/vincular?code=" in out


def test_import_and_devices_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    package = write_package(tmp_path / "pkg", title="Imported")
    assert main(["--data", str(tmp_path / "d"), "import", str(package)]) == 0
    assert "imported" in capsys.readouterr().out
    assert main(["--data", str(tmp_path / "d"), "devices"]) == 0
    assert main(["--data", str(tmp_path / "d"), "import", str(tmp_path / "missing")]) == 1


def test_openapi_command(tmp_path: Path) -> None:
    out = tmp_path / "openapi.json"
    assert main(["--data", str(tmp_path / "d"), "openapi", "--out", str(out)]) == 0
    schema = json.loads(out.read_text(encoding="utf-8"))
    assert "/api/jobs" in schema["paths"]
    assert "Job" in schema["components"]["schemas"]


def test_backup_command_needs_a_destination(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--data", str(tmp_path / "d"), "backup"]) == 2
    assert main(["--data", str(tmp_path / "d"), "backup", "--to", str(tmp_path / "b")]) == 0
    assert (tmp_path / "b" / "karaoke.db").is_file()


def test_serve_listens_on_both_ports(tmp_path: Path) -> None:
    port = free_port()
    while True:
        tunnel = port + 1
        try:
            import socket

            with socket.socket() as s:
                s.bind(("127.0.0.1", tunnel))
            break
        except OSError:
            port = free_port()
    env = {**os.environ, "KARAOKE_DATA": str(tmp_path / "d")}
    process = subprocess.Popen(
        [sys.executable, "-m", "karaoke_server.cli", "serve", "--port", str(port), "--fake-engine"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + 30
        while True:
            try:
                home = httpx.get(f"http://127.0.0.1:{port}/api/me", timeout=1)
                remote = httpx.get(f"http://127.0.0.1:{tunnel}/api/me", timeout=1)
                break
            except httpx.TransportError as exc:
                if time.monotonic() > deadline or process.poll() is not None:
                    output = process.stdout.read() if process.stdout else ""
                    raise AssertionError(output) from exc
                time.sleep(0.2)
        assert home.json()["zone"] == "local"
        assert remote.json()["zone"] == "remote"
    finally:
        process.send_signal(signal.SIGINT)
        # uvicorn ends with the signal it was stopped by, as a well-behaved program should.
        assert process.wait(timeout=20) in (0, -signal.SIGINT)


def test_a_closed_terminal_stops_the_server_cleanly_unless_nohup_asked_to_ignore_it() -> None:
    import signal

    from karaoke_server.serve import hang_up_as_terminate

    previous = signal.getsignal(signal.SIGHUP)
    try:
        signal.signal(signal.SIGHUP, signal.SIG_IGN)  # nohup
        hang_up_as_terminate()
        assert signal.getsignal(signal.SIGHUP) == signal.SIG_IGN
        signal.signal(signal.SIGHUP, signal.SIG_DFL)
        hang_up_as_terminate()
        assert callable(signal.getsignal(signal.SIGHUP))
    finally:
        signal.signal(signal.SIGHUP, previous)


def test_version_prints_the_product_version(capsys: pytest.CaptureFixture[str]) -> None:
    from importlib import metadata

    from karaoke_server.cli import main as cli_main

    with pytest.raises(SystemExit) as exit_info:
        cli_main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"karaoke-server {metadata.version('karaoke-server')}"
