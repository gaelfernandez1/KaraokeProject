"""Written syllables of Galician, Spanish and Portuguese words, for lighting a word part by part.

Rules of the Romance languages, not a dictionary: vowel nuclei (diphthongs stay together, an
accented i or u breaks them), one consonant goes with the next vowel, onset clusters (pr, bl,
tr...) stay together, and ch, ll, nh, rr, qu, gu count as one consonant. Punctuation stuck to the
word rides on the first or last part, so the parts always spell the word as written.
"""

import itertools

_LANGUAGES = {"gl", "es", "pt"}
_OPEN = set("aeoáéóàèòâêôãõ")
_CLOSE = set("iuïü")
_ACCENTED_CLOSE = set("íú")
_VOWELS = _OPEN | _CLOSE | _ACCENTED_CLOSE
_CLUSTERS = {"pl", "pr", "bl", "br", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "tr", "kr", "kl"}
_DIGRAPHS = ("ch", "ll", "nh", "rr", "lh")


def syllables(word: str, language: str) -> list[str] | None:
    """The word split into syllables, or None (other language, one syllable, no letters)."""
    if language not in _LANGUAGES:
        return None
    letters = [i for i, ch in enumerate(word) if ch.isalpha()]
    if not letters:
        return None
    units = _units(word, letters)
    nuclei = _nuclei(units)
    if len(nuclei) < 2:
        return None
    # Each syllable starts at the first unit after the consonants its predecessor keeps.
    starts = [0]
    for (_, end), (begin, _) in itertools.pairwise(nuclei):
        consonants = list(range(end, begin))
        starts.append(begin - _onset_size(units, consonants))
    cuts = [units[s][0] for s in starts[1:]]
    edges = [0, *cuts, len(word)]
    return [word[a:b] for a, b in itertools.pairwise(edges)]


def _units(word: str, letters: list[int]) -> list[tuple[int, str, bool]]:
    """(index in the word, lowercase text, is vowel) per sound unit; digraphs make one unit."""
    units: list[tuple[int, str, bool]] = []
    i = 0
    while i < len(letters):
        index = letters[i]
        ch = word[index].lower()
        nxt = word[letters[i + 1]].lower() if i + 1 < len(letters) else ""
        after = word[letters[i + 2]].lower() if i + 2 < len(letters) else ""
        pair = ch + nxt
        if pair in _DIGRAPHS or (ch in "qg" and nxt == "u" and after and after in "eiéí"):
            units.append((index, pair, False))
            i += 2
            continue
        vowel = ch in _VOWELS or (ch == "y" and nxt not in _VOWELS)
        units.append((index, ch, vowel))
        i += 1
    return units


def _nuclei(units: list[tuple[int, str, bool]]) -> list[tuple[int, int]]:
    """[start, end) unit ranges of each syllable nucleus."""
    nuclei: list[tuple[int, int]] = []
    i = 0
    while i < len(units):
        if not units[i][2]:
            i += 1
            continue
        start = i
        while i + 1 < len(units) and units[i + 1][2] and not _hiatus(units[i][1], units[i + 1][1]):
            i += 1
        nuclei.append((start, i + 1))
        i += 1
    return nuclei


def _hiatus(a: str, b: str) -> bool:
    if a == b:
        return True
    if a in _OPEN and b in _OPEN:
        return True
    return (a in _ACCENTED_CLOSE and b in _OPEN) or (a in _OPEN and b in _ACCENTED_CLOSE)


def _onset_size(units: list[tuple[int, str, bool]], consonants: list[int]) -> int:
    """How many of the consonants between two nuclei start the next syllable."""
    if not consonants:
        return 0
    if len(consonants) == 1:
        return 1
    last_two = units[consonants[-2]][1] + units[consonants[-1]][1]
    return 2 if last_two in _CLUSTERS else 1
