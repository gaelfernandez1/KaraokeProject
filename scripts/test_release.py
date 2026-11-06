import importlib.util
import json
from datetime import date
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load_release() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release", Path(__file__).with_name("release.py"))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = _load_release()

PYPROJECT = """[project]
name = "{name}"
version = "{version}"
description = "A package"
dependencies = ["pydantic>=2.12"]

[tool.uv]
# version = "not this one"
"""

CITATION = """cff-version: 1.2.0
title: "Proxecto Karaoke en Galego"
version: "{version}"
date-released: "2025-10-31"
preferred-citation:
  type: thesis
  year: 2025
"""

CHANGELOG = """# Changelog

## [Unreleased]

## [{version}] - 2026-11-06

### Added

- Everything.

## [2.0.0] - 2026-07-07

- Older.
"""


def make_repo(root: Path, version: str = "3.0.0") -> Path:
    for path in release.VERSION_FILES:
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        if path.endswith("pyproject.toml"):
            file.write_text(PYPROJECT.format(name=file.parent.name, version=version))
        elif path.endswith("package.json"):
            file.write_text(json.dumps({"name": "web", "version": version, "private": True}))
        else:
            file.write_text(CITATION.format(version=version))
    (root / "CHANGELOG.md").write_text(CHANGELOG.format(version=version))
    return root


def test_check_passes_when_every_file_agrees(tmp_path: Path) -> None:
    assert release.check(make_repo(tmp_path)) == []


def test_check_names_the_file_that_differs(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "web/package.json").write_text(json.dumps({"name": "web", "version": "0.0.1"}))
    problems = release.check(root)
    assert len(problems) == 1
    assert "web/package.json" in problems[0]
    assert "0.0.1" in problems[0]
    assert "3.0.0" in problems[0]


def test_check_wants_a_changelog_entry_for_the_version(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "CHANGELOG.md").write_text(CHANGELOG.format(version="2.9.0"))
    problems = release.check(root)
    assert len(problems) == 1
    assert "CHANGELOG.md" in problems[0]
    assert "3.0.0" in problems[0]


def test_check_reports_a_version_that_is_not_semver(tmp_path: Path) -> None:
    root = make_repo(tmp_path, version="3.0")
    assert any("not a semantic version" in problem for problem in release.check(root))


def test_set_version_rewrites_only_version_lines(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    before = {path: (root / path).read_text() for path in release.VERSION_FILES}
    changed = release.set_version(root, "3.1.0", today=date(2026, 12, 1))
    assert sorted(changed) == sorted(root / path for path in release.VERSION_FILES)
    for path, text in before.items():
        after = (root / path).read_text()
        differing = [
            (old, new)
            for old, new in zip(text.splitlines(), after.splitlines(), strict=True)
            if old != new
        ]
        assert differing, path
        for old, new in differing:
            assert ("3.0.0" in old and "3.1.0" in new) or (
                "2025-10-31" in old and "2026-12-01" in new
            )
    assert release.read_versions(root) == dict.fromkeys(release.VERSION_FILES, "3.1.0")
    assert '# version = "not this one"' in (root / "pyproject.toml").read_text()
    assert "year: 2025" in (root / "CITATION.cff").read_text()


def test_set_version_rejects_non_semver(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    with pytest.raises(ValueError, match="semantic version"):
        release.set_version(root, "3.0")
    assert release.read_versions(root) == dict.fromkeys(release.VERSION_FILES, "3.0.0")


def test_repo_versions_agree() -> None:
    assert release.check(REPO) == []


NOTES_CHANGELOG = """# Changelog

## [Unreleased]

### Added

- Not released yet.

## [3.1.0] - 2026-12-01

### Fixed

- A bug.

## [3.0.0] - 2026-11-06

### Added

- Everything.

[Unreleased]: https://example.com/compare/v3.1.0...HEAD
[3.1.0]: https://example.com/compare/v3.0.0...v3.1.0
"""


def test_release_notes_returns_the_section_body() -> None:
    assert release.release_notes(NOTES_CHANGELOG, "3.1.0") == "### Fixed\n\n- A bug."


def test_release_notes_stops_at_the_next_version() -> None:
    notes = release.release_notes(NOTES_CHANGELOG, "3.0.0")
    assert notes == "### Added\n\n- Everything."


def test_release_notes_ignores_unreleased() -> None:
    assert "Not released yet" not in release.release_notes(NOTES_CHANGELOG, "3.1.0")


def test_release_notes_missing_version_raises() -> None:
    with pytest.raises(LookupError, match=r"3\.2\.0"):
        release.release_notes(NOTES_CHANGELOG, "3.2.0")


def test_set_version_rejects_prereleases(tmp_path: Path) -> None:
    # Python would write 3.1.0-rc.1 as 3.1.0rc1: one version could not read the same everywhere.
    root = make_repo(tmp_path)
    with pytest.raises(ValueError, match="semantic version"):
        release.set_version(root, "3.1.0-rc.1")
