"""A transcriber stand-in that dies like one killed for lack of memory (for test_transcribe)."""

import os
import signal


def die(vocals: str, language: str) -> None:
    os.kill(os.getpid(), signal.SIGKILL)
