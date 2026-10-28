import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def _load_check_env() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_env", Path(__file__).with_name("check_env.py")
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_env = _load_check_env()


@pytest.mark.parametrize(
    ("version", "ok"),
    [("v22.22.1", True), ("v24.3.0", True), ("v26.0.0", True), ("v20.18.0", False), ("", False)],
)
def test_node_accepts_22_and_newer(version: str, ok: bool) -> None:
    assert check_env.node_version_ok(version) is ok


def test_tool_that_fails_is_not_reported_ok() -> None:
    ok, _detail = check_env._tool("false")()

    assert ok is False


def test_tool_that_works_is_reported_ok() -> None:
    ok, _detail = check_env._tool("true")()

    assert ok is True
