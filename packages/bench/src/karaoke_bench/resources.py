"""GPU memory sampling with NVML.

WSL cannot report memory per process, so the sampler reads the device's used memory and
subtracts what was in use when it started (Windows itself keeps about 1 GB busy).
"""

import threading
from collections.abc import Callable
from types import TracebackType
from typing import Any, Self


class GpuSampler:
    def __init__(self, query: Callable[[], float] | None = None, interval: float = 0.1) -> None:
        self._query = query
        self._interval = interval
        self._baseline = 0.0
        self._peak = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> Self:
        if self._query is None:
            self._query = _nvml_query()
        if self._query is not None:
            self._baseline = self._peak = self._query()
            self._thread = threading.Thread(target=self._sample, daemon=True)
            self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()

    @property
    def peak_mb(self) -> float | None:
        """Peak extra MiB used on the GPU while sampling; None without NVML."""
        if self._query is None:
            return None
        return max(0.0, self._peak - self._baseline)

    def _sample(self) -> None:
        assert self._query is not None
        while not self._stop.wait(self._interval):
            self._peak = max(self._peak, self._query())
        self._peak = max(self._peak, self._query())


def gpu_info() -> dict[str, str]:
    nvml = _nvml()
    if nvml is None:
        return {}
    handle = nvml.nvmlDeviceGetHandleByIndex(0)
    return {
        "gpu": str(nvml.nvmlDeviceGetName(handle)),
        "driver": str(nvml.nvmlSystemGetDriverVersion()),
        "gpu_memory_mb": str(round(nvml.nvmlDeviceGetMemoryInfo(handle).total / 2**20)),
    }


def _nvml_query() -> Callable[[], float] | None:
    nvml = _nvml()
    if nvml is None:
        return None
    handle = nvml.nvmlDeviceGetHandleByIndex(0)
    return lambda: float(nvml.nvmlDeviceGetMemoryInfo(handle).used) / 2**20


def _nvml() -> Any | None:
    try:
        import pynvml

        pynvml.nvmlInit()
    except Exception:
        return None
    return pynvml
