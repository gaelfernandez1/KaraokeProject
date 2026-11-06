"""Runs each job in a process of its own, inside a systemd scope that caps its memory.

The engine's models keep their memory until the process that loaded them ends, and on this
machine running out of memory once took WSL down whole. In a scope with MemoryMax, the kernel
stops only the job. Cancelling stops the whole scope (or, without systemd, the process group).
"""

import asyncio
import contextlib
import functools
import hashlib
import json
import logging
import os
import secrets
import shutil
import signal
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from karaoke_server.config import Settings
from karaoke_server.jobs.types import Event, Outcome

logger = logging.getLogger(__name__)

GIB = 1024**3
KILL_AFTER = 5.0
# Exit status of a process killed with SIGKILL, which is how the kernel stops it for memory.
KILLED = (-signal.SIGKILL, 128 + signal.SIGKILL)


@functools.cache
def scope_available() -> bool:
    try:
        result = subprocess.run(
            ["systemd-run", "--user", "--scope", "--quiet", "true"],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _runner(spec_path: Path) -> list[str]:
    return [sys.executable, "-m", "karaoke_server.jobs.runner", str(spec_path)]


class ProcessSpawner:
    def __init__(self, settings: Settings, command: Callable[[Path], list[str]] = _runner) -> None:
        self.settings = settings
        self.command = command
        # Units carry their library's mark: a server stops what it left behind, never the jobs
        # of another library on the same machine (the browser tests run their own).
        mark = hashlib.sha256(str(settings.data_dir.resolve()).encode()).hexdigest()[:8]
        self.unit_prefix = f"karaoke-{mark}-"

    def unit_for(self, job_id: str) -> str:
        # Unique per run: systemd keeps a unit's name for a moment after it ends.
        return f"{self.unit_prefix}{job_id}-{secrets.token_hex(3)}"

    def leftovers_pattern(self) -> str:
        return f"{self.unit_prefix}*.scope"

    def stop_leftovers(self) -> None:
        """Stops engines a server that died suddenly (a closed terminal, a crash) left running.

        Their job is about to run again: two engines would not fit in the GPU nor in the RAM.
        """
        if not scope_available():
            return
        try:
            subprocess.run(
                ["systemctl", "--user", "stop", self.leftovers_pattern()],
                capture_output=True, timeout=30, check=False,
            )  # fmt: skip
        except (OSError, subprocess.TimeoutExpired):
            logger.warning("could not stop engines left by a previous server")

    def memory_limit(self) -> int:
        if self.settings.memory_max:
            return self.settings.memory_max
        total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        return int(max(total - GIB, GIB))

    def full_command(self, unit: str, spec_path: Path) -> list[str]:
        base = self.command(spec_path)
        if not scope_available():
            return base
        swap = []
        if self.settings.memory_swap_max is not None:
            swap = ["-p", f"MemorySwapMax={self.settings.memory_swap_max}"]
        return [
            "systemd-run",
            "--user",
            "--scope",
            "--quiet",
            "--collect",
            f"--unit={unit}",
            "-p",
            f"MemoryMax={self.memory_limit()}",
            *swap,
            "--",
            *base,
        ]

    async def run(
        self, job_id: str, spec: dict[str, Any], log: Path, on_event: Callable[[Event], None]
    ) -> Outcome:
        log.parent.mkdir(parents=True, exist_ok=True)
        spec_path = log.parent / "spec.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        tmp = self.settings.tmp_dir / job_id
        tmp.mkdir(parents=True, exist_ok=True)
        env = {
            **os.environ,
            "TMPDIR": str(tmp),
            "PYTHONUNBUFFERED": "1",
            # The runner ends itself if this process goes away (see runner.die_with_parent).
            "KARAOKE_PARENT_PID": str(os.getpid()),
        }
        unit = self.unit_for(job_id)
        with log.open("ab") as stderr:
            process = await asyncio.create_subprocess_exec(
                *self.full_command(unit, spec_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=stderr,
                env=env,
                start_new_session=True,
            )
        last: Event | None = None
        try:
            assert process.stdout is not None
            while True:
                try:
                    raw = await process.stdout.readline()
                except ValueError:
                    # A line too long for the buffer: some library printing, not an event.
                    continue
                if not raw:
                    break
                try:
                    event = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(event, dict):
                    continue
                if event.get("event") in ("done", "error"):
                    last = event
                else:
                    on_event(event)
            code = await process.wait()
        except BaseException:
            # Cancelled, or anything else going wrong here: the job must not keep the GPU.
            await self._stop(unit, process)
            raise
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return self._outcome(code, last)

    @staticmethod
    def _outcome(code: int, last: Event | None) -> Outcome:
        if last and last.get("event") == "done" and code == 0:
            return Outcome(ok=True, result=dict(last.get("result") or {}))
        if last and last.get("event") == "error":
            return Outcome(
                ok=False,
                code=last.get("code") or "engine_failed",
                message=last.get("message"),
                transient=bool(last.get("transient")),
            )
        if code in KILLED:
            return Outcome(
                ok=False,
                code="out_of_memory",
                transient=True,
                message="The job ran out of memory and was stopped",
            )
        return Outcome(
            ok=False,
            code="engine_failed",
            transient=True,
            message=f"The engine stopped unexpectedly (exit status {code})",
        )

    async def _stop(self, unit: str, process: asyncio.subprocess.Process) -> None:
        """SIGTERM to everything the job started, then SIGKILL if it does not go."""
        if scope_available():
            await asyncio.to_thread(
                subprocess.run,
                ["systemctl", "--user", "kill", "--signal=SIGTERM", f"{unit}.scope"],
                capture_output=True,
            )
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            await asyncio.wait_for(process.wait(), KILL_AFTER)
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            if scope_available():
                await asyncio.to_thread(
                    subprocess.run,
                    ["systemctl", "--user", "kill", "--signal=SIGKILL", f"{unit}.scope"],
                    capture_output=True,
                )
            await process.wait()
        logger.info("%s stopped", unit)
