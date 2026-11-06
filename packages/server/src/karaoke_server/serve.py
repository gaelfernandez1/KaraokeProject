"""Running the server: one uvicorn process listening on the home port and on the tunnel port."""

import logging
import os
import signal
import socket

import uvicorn

from karaoke_server.app import create_app
from karaoke_server.config import Settings
from karaoke_server.logs import setup_logging

logger = logging.getLogger(__name__)


def _listen(host: str, port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    return sock


def serve(settings: Settings, verbose: bool = False) -> None:
    setup_logging(settings.logs_dir, verbose)
    app = create_app(settings)
    home = _listen(settings.home_host, settings.home_port)
    tunnel = _listen("127.0.0.1", settings.tunnel_port)
    info = app.state.services.network.info()
    logger.info("karaoke server on http://localhost:%s (home: %s)", settings.home_port, info.url)
    # The app reads the client and the proxy headers itself (zones): uvicorn must not rewrite them.
    config = uvicorn.Config(
        app, proxy_headers=False, log_config=None, server_header=False, timeout_graceful_shutdown=5
    )
    hang_up_as_terminate()
    uvicorn.Server(config).run(sockets=[home, tunnel])


def hang_up_as_terminate() -> None:
    """Closing the terminal sends SIGHUP: shut down as for Ctrl+C, stopping the running job,
    instead of dying on the spot and leaving its engine behind. Under `nohup` (SIGHUP ignored)
    it keeps ignoring it."""
    if signal.getsignal(signal.SIGHUP) is signal.SIG_DFL:
        signal.signal(signal.SIGHUP, lambda *_: os.kill(os.getpid(), signal.SIGTERM))
