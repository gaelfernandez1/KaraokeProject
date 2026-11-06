import importlib.util
from dataclasses import dataclass
from email.message import Message
from pathlib import Path
from types import ModuleType

import pytest


def _load_licenses() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "licenses", Path(__file__).with_name("licenses.py")
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


licenses = _load_licenses()


def meta(
    name: str = "pkg",
    expression: str | None = None,
    licence: str | None = None,
    classifiers: tuple[str, ...] = (),
) -> Message:
    message = Message()
    message["Name"] = name
    if expression is not None:
        message["License-Expression"] = expression
    if licence is not None:
        message["License"] = licence
    for classifier in classifiers:
        message["Classifier"] = classifier
    return message


@dataclass
class Dist:
    metadata: Message
    version: str = "1.0"


def test_expression_wins_over_classifiers() -> None:
    found = licenses.licence_of(
        meta(expression="Apache-2.0", classifiers=("License :: OSI Approved :: MIT License",))
    )
    assert found == "Apache-2.0"


def test_classifier_when_nothing_else() -> None:
    found = licenses.licence_of(meta(classifiers=("License :: OSI Approved :: BSD License",)))
    assert found == "BSD License"


def test_full_licence_text_falls_back_to_classifiers() -> None:
    text = "Copyright (c) 2001-2002 Enthought, Inc.\nAll rights reserved.\n\nRedistribution..."
    found = licenses.licence_of(
        meta(licence=text, classifiers=("License :: OSI Approved :: BSD License",))
    )
    assert found == "BSD License"


def test_permissive_and_weak_copyleft_pass() -> None:
    dists = [
        Dist(meta("a", expression="MIT")),
        Dist(meta("b", licence="BSD 3-Clause License")),
        Dist(meta("c", expression="Apache-2.0 OR BSD-2-Clause")),
        Dist(meta("d", expression="MPL-2.0 AND MIT")),
        Dist(meta("e", expression="LGPL-2.1-or-later")),
        Dist(meta("f", classifiers=("License :: OSI Approved :: Apache Software License",))),
        Dist(meta("g", licence="MIT License")),
        Dist(meta("h", classifiers=("License :: OSI Approved :: BSD License",))),
        Dist(meta("i", licence="ISC License (ISCL)")),
        Dist(meta("j", licence="Unlicense license")),
        Dist(meta("k", licence="Apache 2.0 License")),
        Dist(
            meta(
                "l",
                classifiers=("License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",),
            )
        ),
    ]
    assert licenses.problems(dists) == []


def test_unknown_licence_is_a_problem() -> None:
    dists = [
        Dist(meta("nc-lib", licence="Creative Commons Attribution-NonCommercial 4.0"), "0.2.4"),
        Dist(meta("gpl-lib", expression="GPL-3.0-only"), "2.0"),
        Dist(meta("silent")),
    ]
    assert licenses.problems(dists) == [
        "nc-lib 0.2.4: Creative Commons Attribution-NonCommercial 4.0",
        "gpl-lib 2.0: GPL-3.0-only",
        "silent 1.0: no licence in its metadata",
    ]


def test_nvidia_runtime_is_accepted() -> None:
    dists = [
        Dist(meta("nvidia-cublas-cu12", expression="LicenseRef-NVIDIA-Proprietary")),
        Dist(meta("nvidia-cusparselt-cu13", licence="NVIDIA Proprietary Software")),
        Dist(meta("cuda-toolkit")),
    ]
    assert licenses.problems(dists) == []


def test_proprietary_licence_outside_nvidia_is_a_problem() -> None:
    dists = [Dist(meta("closed", classifiers=("License :: Other/Proprietary License",)))]
    assert licenses.problems(dists) == ["closed 1.0: Other/Proprietary License"]


def test_workspace_packages_are_skipped() -> None:
    assert licenses.problems([Dist(meta("karaoke-engine"))]) == []


def test_reviewed_package_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(licenses.REVIEWED, "odd-metadata", "MIT, stated only in its repository")
    assert licenses.problems([Dist(meta("odd-metadata"))]) == []


@pytest.mark.parametrize(
    "licence",
    [
        "(MIT OR Apache-2.0) AND BSD-3-Clause",
        "MIT AND (Apache-2.0 OR GPL-3.0-only)",
        "(MIT) OR (Apache-2.0)",
        "Apache-2.0 WITH LLVM-exception",
    ],
)
def test_grouped_spdx_expressions_are_read_as_expressions(licence: str) -> None:
    assert licenses.accepted(licence)


def test_a_group_with_only_rejected_licences_fails() -> None:
    assert not licenses.accepted("BSD-3-Clause AND (GPL-3.0-only OR AGPL-3.0-only)")


@pytest.mark.parametrize(
    "classifiers",
    [
        ("License :: OSI Approved", "License :: OSI Approved :: MIT License"),
        ("License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",),
    ],
)
def test_common_classifiers_pass(classifiers: tuple[str, ...]) -> None:
    assert licenses.problems([Dist(meta("pkg", classifiers=classifiers))]) == []


def test_apache_licence_written_out_passes() -> None:
    assert licenses.problems([Dist(meta("pkg", licence="Apache License, Version 2.0"))]) == []
