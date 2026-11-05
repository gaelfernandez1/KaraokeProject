"""A real uvicorn server in a thread, for what TestClient cannot do (Server-Sent Events)."""

import asyncio
import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

import uvicorn
from fastapi import FastAPI


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@contextmanager
def live_server(app: FastAPI, host: str = "127.0.0.1") -> Iterator[str]:
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="warning"))
    thread = threading.Thread(target=lambda: asyncio.run(server.serve()), daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("the test server did not start")
        time.sleep(0.02)
    try:
        yield f"http://{host}:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def read_events(lines: Iterator[str], count: int) -> list[tuple[str, str]]:
    """The next `count` (event, data) pairs of an SSE stream."""
    events: list[tuple[str, str]] = []
    event = ""
    for line in lines:
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            events.append((event, line[5:].strip()))
            if len(events) == count:
                break
    return events
