"""Pipelines: a TOML file naming the class (and parameters) of each engine step.

Any class that satisfies the engine's step protocols works, so the separation and alignment
areas only add a TOML file pointing at theirs.
"""

import importlib
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast, get_args

from karaoke_engine.steps import Aligner, Segmenter, Separator, Transcriber

StepKind = Literal["separator", "transcriber", "segmenter", "aligner"]
Mode = Literal["lyrics", "asr"]
STEP_KINDS: tuple[StepKind, ...] = get_args(StepKind)
PROTOCOLS: dict[StepKind, type] = {
    "separator": Separator,
    "transcriber": Transcriber,
    "segmenter": Segmenter,
    "aligner": Aligner,
}
_REQUIRED: dict[Mode, list[StepKind]] = {
    "lyrics": ["aligner"],
    "asr": ["transcriber", "segmenter", "aligner"],
}
_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class PipelineError(ValueError):
    pass


@dataclass(frozen=True)
class StepSpec:
    kind: StepKind
    target: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {"kind": self.kind, "target": self.target, "params": self.params}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "StepSpec":
        return cls(data["kind"], data["target"], dict(data.get("params", {})))


@dataclass(frozen=True)
class Pipeline:
    name: str
    description: str
    steps: dict[StepKind, StepSpec]
    path: Path

    def required(self, mode: Mode) -> list[StepKind]:
        return list(_REQUIRED[mode])

    def check(self, mode: Mode) -> None:
        missing = [kind for kind in self.required(mode) if kind not in self.steps]
        if missing:
            raise PipelineError(f"pipeline '{self.name}' has no {', '.join(missing)} for {mode}")


def load_pipeline(path: Path) -> Pipeline:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    name = data.get("name", "")
    if not isinstance(name, str) or not _NAME.match(name):
        raise PipelineError(f"{path}: name must match {_NAME.pattern}, got {name!r}")
    steps: dict[StepKind, StepSpec] = {}
    for kind, body in data.get("steps", {}).items():
        if kind not in STEP_KINDS:
            raise PipelineError(f"{path}: unknown step '{kind}' (use {', '.join(STEP_KINDS)})")
        target = body.get("target", "")
        if not isinstance(target, str) or target.count(":") != 1:
            raise PipelineError(f"{path}: steps.{kind}.target must look like 'module:Class'")
        steps[cast(StepKind, kind)] = StepSpec(kind, target, dict(body.get("params", {})))
    return Pipeline(name, str(data.get("description", "")), steps, path)


def step_class(spec: StepSpec) -> type:
    module_name, _, attr = spec.target.partition(":")
    try:
        found = getattr(importlib.import_module(module_name), attr)
    except (ImportError, AttributeError) as exc:
        raise PipelineError(f"cannot import {spec.target}: {exc}") from exc
    if not isinstance(found, type):
        raise PipelineError(f"{spec.target} is not a class")
    return found


def step_version(spec: StepSpec) -> str:
    return str(getattr(step_class(spec), "version", "0"))


def build_step(spec: StepSpec) -> Any:
    step = step_class(spec)(**spec.params)
    protocol = PROTOCOLS[spec.kind]
    if not isinstance(step, protocol):
        raise PipelineError(f"{spec.target} does not implement {protocol.__name__}")
    return step
