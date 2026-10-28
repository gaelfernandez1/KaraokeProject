import itertools
import sys
import time

import pytest

from karaoke_bench.resources import GpuSampler


def test_sampler_peak_from_fake_query() -> None:
    readings = itertools.chain([1000.0, 1500.0, 1200.0], itertools.repeat(1100.0))

    with GpuSampler(query=lambda: next(readings), interval=0.001) as sampler:
        time.sleep(0.05)

    assert sampler.peak_mb == pytest.approx(500.0)


def test_sampler_never_negative() -> None:
    readings = itertools.chain([1000.0], itertools.repeat(800.0))

    with GpuSampler(query=lambda: next(readings), interval=0.001) as sampler:
        time.sleep(0.01)

    assert sampler.peak_mb == 0.0


def test_sampler_without_nvml_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pynvml", None)

    with GpuSampler() as sampler:
        pass

    assert sampler.peak_mb is None
