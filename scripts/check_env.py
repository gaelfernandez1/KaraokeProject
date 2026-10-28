"""Checks that this machine can develop and run the karaoke engine (`make check-env`).

Stdlib only, so it runs before anything is installed. The torch check runs only when the `ml`
extra is synced (`uv sync --extra ml`).
"""

import importlib.util
import shutil
import subprocess
import sys
from collections.abc import Callable

Check = tuple[str, bool, Callable[[], tuple[bool, str]]]


def _run(*cmd: str) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    return result.stdout + result.stderr


def _tool(name: str, *version_args: str) -> Callable[[], tuple[bool, str]]:
    def check() -> tuple[bool, str]:
        if shutil.which(name) is None:
            return False, "not installed"
        return True, _run(name, *version_args).strip().splitlines()[0]

    return check


def _node() -> tuple[bool, str]:
    if shutil.which("node") is None:
        return False, "not installed"
    version = _run("node", "--version").strip()
    return version.startswith("v22") or version.startswith("v24"), version


def _ffmpeg_feature(flag: str, name: str) -> Callable[[], tuple[bool, str]]:
    def check() -> tuple[bool, str]:
        if shutil.which("ffmpeg") is None:
            return False, "ffmpeg not installed"
        found = any(
            name in line.split() for line in _run("ffmpeg", "-hide_banner", flag).splitlines()
        )
        return found, "available" if found else f"ffmpeg built without {name}"

    return check


def _torch_cuda() -> tuple[bool, str]:
    if importlib.util.find_spec("torch") is None:
        return False, "torch missing: run `uv sync --extra ml`"
    import torch

    if not torch.cuda.is_available():
        return False, f"torch {torch.__version__} cannot see a CUDA GPU"
    props = torch.cuda.get_device_properties(0)
    x = torch.randn(1024, 1024, device="cuda")
    ok = bool(torch.isfinite(x @ x).all())
    vram = props.total_memory / 2**30
    matmul = "ok" if ok else "FAILED"
    return ok, f"torch {torch.__version__}, {props.name}, {vram:.1f} GiB VRAM, matmul {matmul}"


CHECKS: list[Check] = [
    ("uv", True, _tool("uv", "--version")),
    ("node 22+", True, _node),
    ("pnpm", True, _tool("pnpm", "--version")),
    ("ffmpeg", True, _tool("ffmpeg", "-hide_banner", "-version")),
    ("ffmpeg ass filter (libass)", True, _ffmpeg_feature("-filters", "ass")),
    ("ffmpeg h264_nvenc encoder", False, _ffmpeg_feature("-encoders", "h264_nvenc")),
    (
        "nvidia-smi",
        False,
        _tool("nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"),
    ),
    ("torch + CUDA (ml extra)", False, _torch_cuda),
]


def main() -> int:
    missing_required = False
    for name, required, check in CHECKS:
        try:
            ok, detail = check()
        except Exception as exc:  # a broken tool should be reported, not crash the report
            ok, detail = False, f"error: {exc}"
        status = "OK" if ok else ("FALTA" if required else "aviso")
        print(f"{status:6} {name:30} {detail}")
        missing_required |= required and not ok
    return 1 if missing_required else 0


if __name__ == "__main__":
    sys.exit(main())
