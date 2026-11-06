"""Every installed dependency has a licence the project accepts (principle 8 of the plan).

    uv run python scripts/licenses.py      # lists the ones that do not pass; exit 1 if any

It reads the metadata of the environment it runs in: in CI that is everything but the GPU
extra; on the GPU machine (`uv sync --extra ml`) it checks the models' libraries too. Accepted:
permissive licences, weak copyleft used as an unmodified library (MPL, LGPL) and NVIDIA's CUDA
runtime, which is downloaded from PyPI, never shipped here. Anything else fails until it is
replaced or reviewed in REVIEWED with a reason. NOTICE.md lists the components that matter.
"""

import re
import sys
from collections.abc import Iterable
from email.message import Message
from importlib import metadata
from typing import Protocol

# Licence names as packages write them (SPDX ids, classifier names and the usual free text).
_ACCEPTED_NAMES = (
    r"(The )?MIT(-0|-CMU)?( License)?",
    r"(0BSD|BSD(-[23]-Clause| [23]-Clause License)?|3-Clause BSD License)( License)?",
    r"Apache(-2\.0| 2\.0| Software License| License( 2\.0|,? Version 2\.0)?)?( License)?",
    r"Apache-2\.0 WITH LLVM-exception",
    r"ISC( License)?( \(ISCL\))?",
    r"PSF-2\.0|Python Software Foundation License|Python-2\.0|CNRI-Python",
    r"Zlib|CC0-1\.0|BSL-1\.0|HPND",
    r"(The )?Unlicense( license)?( \(Unlicense\))?",
    r"MPL-2\.0|Mozilla Public License 2\.0 \(MPL 2\.0\)",
    r"LGPL-[0-9.]+(-only|-or-later)?|GNU (Library or )?Lesser General Public License.*",
)
_ACCEPTED = re.compile("|".join(f"(?:{name})" for name in _ACCEPTED_NAMES), re.IGNORECASE)
_NVIDIA = re.compile(r"^(LicenseRef-NVIDIA-Proprietary|NVIDIA Proprietary Software)?$")

# Packages whose metadata does not say their licence well enough, checked by hand.
REVIEWED: dict[str, str] = {}

# The project's own packages (MIT, see LICENSE).
_OWN = "karaoke-"


class _Distribution(Protocol):
    @property
    def metadata(self) -> Message: ...  # what importlib.metadata.Distribution gives

    @property
    def version(self) -> str: ...


def licence_of(meta: Message) -> str:
    """What the package says its licence is: the SPDX expression, the License field when it is a
    name (not the whole text), or the classifiers. Empty when it says nothing."""
    expression = meta.get("License-Expression")
    if expression:
        return str(expression).strip()
    field = str(meta.get("License") or "").strip()
    if field and "\n" not in field and len(field) <= 60:
        return field
    # "License :: OSI Approved" alone says nothing about which licence; its subclasses do.
    classifiers = [
        str(c).split(" :: ")[-1]
        for c in meta.get_all("Classifier") or []
        if c.startswith("License ::") and str(c).split(" :: ")[-1] != "OSI Approved"
    ]
    return "; ".join(classifiers)


# An SPDX expression: names joined by AND, OR and WITH, with parentheses. A name may be free text
# with spaces (classifier names), but never an operator.
_TOKEN = re.compile(r"\(|\)|\b(?:AND|OR|WITH)\b|[^()\s]+(?:\s+(?!(?:AND|OR|WITH)\b)[^()\s]+)*")


def _expression(tokens: list[str], at: int) -> tuple[bool, int]:
    """expression := term (OR term)*, where an OR needs one side accepted."""
    ok, at = _term(tokens, at)
    while at < len(tokens) and tokens[at] == "OR":
        right, at = _term(tokens, at + 1)
        ok = ok or right
    return ok, at


def _term(tokens: list[str], at: int) -> tuple[bool, int]:
    """term := factor (AND factor)*, where every side must be accepted."""
    ok, at = _factor(tokens, at)
    while at < len(tokens) and tokens[at] == "AND":
        right, at = _factor(tokens, at + 1)
        ok = ok and right
    return ok, at


def _factor(tokens: list[str], at: int) -> tuple[bool, int]:
    """factor := ( expression ) | name [WITH exception]; an exception only grants more."""
    if at >= len(tokens):
        raise ValueError("the expression ends too soon")
    if tokens[at] == "(":
        ok, at = _expression(tokens, at + 1)
        if at >= len(tokens) or tokens[at] != ")":
            raise ValueError("a parenthesis is not closed")
        return ok, at + 1
    if tokens[at] in {")", "AND", "OR", "WITH"}:
        raise ValueError(f"unexpected {tokens[at]}")
    ok = _ACCEPTED.fullmatch(tokens[at]) is not None
    at += 1
    if at < len(tokens) and tokens[at] == "WITH":
        at += 2
    return ok, at


def accepted(licence: str) -> bool:
    """True when the licence, read as an SPDX expression, allows using the package: every side of
    an AND accepted, one side of an OR. Classifier lists (joined with "; ") need all of them."""
    text = licence.strip()
    if _ACCEPTED.fullmatch(text):  # a name with its own parentheses, like "ISC License (ISCL)"
        return True
    if ";" in text:
        return all(accepted(part) for part in text.split(";") if part.strip())
    tokens = _TOKEN.findall(text)
    try:
        ok, at = _expression(tokens, 0)
    except ValueError:
        return False
    return ok and at == len(tokens)


def problems(dists: Iterable[_Distribution]) -> list[str]:
    """`<name> <version>: <licence>` for each package the project does not accept."""
    found = []
    seen = set()
    for dist in dists:
        name = str(dist.metadata["Name"])
        key = re.sub(r"[-_.]+", "-", name).lower()
        if key in seen or key.startswith(_OWN) or key in REVIEWED:
            continue
        seen.add(key)
        licence = licence_of(dist.metadata)
        if key.startswith(("nvidia-", "cuda-")) and (
            _NVIDIA.match(licence) or "Proprietary" in licence or accepted(licence)
        ):
            continue
        if not licence or not accepted(licence):
            found.append(f"{name} {dist.version}: {licence or 'no licence in its metadata'}")
    return found


def main() -> int:
    found = problems(metadata.distributions())
    for problem in found:
        print(problem, file=sys.stderr)
    if found:
        print(
            "\nThese licences are not accepted (scripts/licenses.py): replace the package, or "
            "review it and add it to REVIEWED with the reason.",
            file=sys.stderr,
        )
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
