"""One version for the whole product, and the notes of a release.

    python scripts/release.py check          # every file agrees and CHANGELOG.md has the entry
    python scripts/release.py set 3.1.0      # writes the version everywhere (not the changelog)
    python scripts/release.py notes 3.1.0    # that version's CHANGELOG.md section (release notes)

The Python packages, the web app and CITATION.cff carry the same version; `make lint` runs
`check` so they cannot drift apart. How a release is made: docs/releasing.md.
"""

import json
import re
import sys
import tomllib
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# The first one is the reference the others are compared with.
VERSION_FILES = (
    "pyproject.toml",
    "packages/contracts/pyproject.toml",
    "packages/engine/pyproject.toml",
    "packages/bench/pyproject.toml",
    "packages/server/pyproject.toml",
    "web/package.json",
    "CITATION.cff",
)

# X.Y.Z only: a semver pre-release (3.1.0-rc.1) is written 3.1.0rc1 by Python packaging, so the
# version could not read the same in every file, command and tag.
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
# A released section of CHANGELOG.md (Keep a Changelog): "## [3.0.0] - 2026-11-06".
RELEASE_HEADING = re.compile(r"^## \[(?P<version>[^\]]+)\] - \d{4}-\d{2}-\d{2}\s*$", re.MULTILINE)

_LINK_DEFINITION = re.compile(r"^\[[^\]]+\]: \S")

_PYPROJECT_VERSION = re.compile(r'^(version = ")[^"]*(")', re.MULTILINE)
# The first "version" key of package.json is the package's own (dependencies come later).
_PACKAGE_JSON_VERSION = re.compile(r'("version":\s*")[^"]*(")')
_CITATION_VERSION = re.compile(r'^(version: ")[^"]*(")', re.MULTILINE)
_CITATION_DATE = re.compile(r'^(date-released: ")[^"]*(")', re.MULTILINE)
_CITATION_VERSION_READ = re.compile(r'^version: "?([^"\s]+)"?\s*$', re.MULTILINE)


def _read(path: Path) -> str:
    if path.name == "pyproject.toml":
        return str(tomllib.loads(path.read_text())["project"]["version"])
    if path.name == "package.json":
        return str(json.loads(path.read_text())["version"])
    found = _CITATION_VERSION_READ.search(path.read_text())
    if found is None:
        raise ValueError(f"{path} has no version line")
    return found.group(1)


def read_versions(root: Path) -> dict[str, str]:
    """The version each file states, by path relative to the repo."""
    return {path: _read(root / path) for path in VERSION_FILES}


def latest_release(changelog: str) -> str | None:
    """The version of the newest released section ("Unreleased" does not count)."""
    found = RELEASE_HEADING.search(changelog)
    return found.group("version") if found else None


def release_notes(changelog: str, version: str) -> str:
    """The body of the section of `version`: what the GitHub release says."""
    heading = re.compile(rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}\s*$")
    lines = changelog.splitlines()
    start = next((i for i, line in enumerate(lines) if heading.match(line)), None)
    if start is None:
        raise LookupError(f"CHANGELOG.md has no section '## [{version}] - YYYY-MM-DD'")
    body = []
    for line in lines[start + 1 :]:
        # The next section, or the link definitions at the end of the file.
        if line.startswith("## ") or _LINK_DEFINITION.match(line):
            break
        body.append(line)
    return "\n".join(body).strip("\n")


def check(root: Path) -> list[str]:
    """Readable problems; empty when every file and the changelog agree."""
    versions = read_versions(root)
    reference_file = VERSION_FILES[0]
    reference = versions[reference_file]
    problems = [
        f"{path}: {version} ({reference_file} has {reference})"
        for path, version in versions.items()
        if version != reference
    ]
    if not SEMVER.match(reference):
        problems.append(f"{reference_file}: {reference} is not a semantic version (X.Y.Z)")
    changelog = root / "CHANGELOG.md"
    latest = latest_release(changelog.read_text()) if changelog.exists() else None
    if latest != reference:
        found = f"its newest release is {latest}" if latest else "it has no release section"
        problems.append(
            f"CHANGELOG.md: {found}; add '## [{reference}] - YYYY-MM-DD' above the older ones"
        )
    return problems


def set_version(root: Path, version: str, today: date | None = None) -> list[Path]:
    """Writes `version` in every file (and today's date in CITATION.cff); returns those files.

    Only the version lines change, so comments and formatting survive.
    """
    if not SEMVER.match(version):
        raise ValueError(f"{version!r} is not a semantic version (X.Y.Z)")
    released = (today or date.today()).isoformat()  # noqa: DTZ011 - a calendar date for people
    changed = []
    for relative in VERSION_FILES:
        path = root / relative
        text = path.read_text()
        if path.name == "pyproject.toml":
            text = _PYPROJECT_VERSION.sub(rf"\g<1>{version}\g<2>", text, count=1)
        elif path.name == "package.json":
            text = _PACKAGE_JSON_VERSION.sub(rf"\g<1>{version}\g<2>", text, count=1)
        else:
            text = _CITATION_VERSION.sub(rf"\g<1>{version}\g<2>", text, count=1)
            text = _CITATION_DATE.sub(rf"\g<1>{released}\g<2>", text, count=1)
        path.write_text(text)
        changed.append(path)
    return changed


def main(argv: list[str]) -> int:
    match argv:
        case ["check"]:
            problems = check(REPO)
            for problem in problems:
                print(problem, file=sys.stderr)
            return 1 if problems else 0
        case ["set", version]:
            for path in set_version(REPO, version):
                print(path.relative_to(REPO))
            print("Now: uv lock, make contracts and a CHANGELOG.md entry (docs/releasing.md).")
            return 0
        case ["notes", version]:
            try:
                print(release_notes((REPO / "CHANGELOG.md").read_text(), version))
            except LookupError as error:
                print(error, file=sys.stderr)
                return 1
            return 0
        case _:
            print(__doc__, file=sys.stderr)
            return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
