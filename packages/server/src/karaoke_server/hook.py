"""The poster's hook: the line a song is remembered by.

Mirror of `web/src/lib/poster/hook.ts`; `fixtures/hook-cases.json` keeps the two in step.
"""

import re
import unicodedata

from karaoke_contracts import KaraokeDoc

# Spaces, commas, colons and dashes (en and em dashes too) at the end of a line.
_TRAILING = re.compile("[\\s,;:\u2013\u2014-]+$")


def _key(text: str) -> str:
    kept = "".join(c for c in text.lower() if c == " " or unicodedata.category(c)[0] in "LN")
    return kept.strip()


def hook_of(doc: KaraokeDoc) -> str | None:
    """The lead line sung most often (the chorus hook), else the first line of 3+ words."""
    lines = [" ".join(w.text for w in line.words) for line in doc.lines if line.role == "lead"]
    counts: dict[str, int] = {}
    for line in lines:
        counts[_key(line)] = counts.get(_key(line), 0) + 1
    best: str | None = None
    most = 1
    for line in lines:
        count = counts[_key(line)]
        if count > most and len(line.split(" ")) >= 2:
            best, most = line, count
    if best is None:
        best = next((line for line in lines if len(line.split(" ")) >= 3), None)
    if best is None:
        best = lines[0] if lines else None
    # A quoted line ends clean: "Ola, mar de Vigo," is printed «Ola, mar de Vigo».
    return _TRAILING.sub("", best) if best is not None else None
