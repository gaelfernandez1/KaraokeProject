"""Every relative link in the repository's Markdown points to something in the repository.

    uv run python scripts/check_links.py     # lists the broken ones; exit 1 if any

"In the repository" means tracked by git (or new and not ignored): a file that exists only on
this machine is a dead link on GitHub. Runs in the test suite (scripts/test_check_links.py).
"""

import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[1]

_FENCE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]*`")
# [text](target "title") and ![alt](target); <img src="target">, <source srcset="target">.
_MARKDOWN_LINK = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_HTML_LINK = re.compile(r"""\b(?:src|srcset|href)=["']([^"']+)["']""")
_EXTERNAL = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)


def _targets(text: str) -> list[str]:
    text = _INLINE_CODE.sub("", _FENCE.sub("", text))
    found = _MARKDOWN_LINK.findall(text) + _HTML_LINK.findall(text)
    return [t for t in found if not _EXTERNAL.match(t) and not t.startswith("#")]


def _normalise(path: PurePosixPath) -> str:
    parts: list[str] = []
    for part in path.parts:
        if part == "..":
            if parts:
                parts.pop()
        elif part != ".":
            parts.append(part)
    return "/".join(parts)


def broken_links(source: str, text: str, tracked: set[str]) -> list[str]:
    """The links of `source` (a path relative to the repo) that point to nothing tracked."""
    folders = {str(parent) for path in tracked for parent in PurePosixPath(path).parents}
    broken = []
    for target in _targets(text):
        path = target.split("#", 1)[0].split("?", 1)[0]
        # On GitHub a link that starts with / starts at the root of the repository.
        start = PurePosixPath() if path.startswith("/") else PurePosixPath(source).parent
        resolved = _normalise(start / path.lstrip("/")).rstrip("/")
        if resolved and resolved not in tracked and resolved not in folders:
            broken.append(target)
    return broken


def _repo_files() -> set[str]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    # Deleted but not yet staged files are still listed: keep what is on disk.
    return {path for path in listed.splitlines() if (REPO / path).exists()}


def repo_problems() -> list[str]:
    """`<file>: <target>` for every broken link in the repository's Markdown."""
    tracked = _repo_files()
    return [
        f"{source}: {target}"
        for source in sorted(p for p in tracked if p.endswith(".md"))
        for target in broken_links(source, (REPO / source).read_text(encoding="utf-8"), tracked)
    ]


if __name__ == "__main__":
    problems = repo_problems()
    for problem in problems:
        print(problem, file=sys.stderr)
    sys.exit(1 if problems else 0)
