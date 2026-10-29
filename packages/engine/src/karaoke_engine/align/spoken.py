"""A displayed word in the form the aligner should look for: letters as they are sung.

Only for aligning: the displayed text never changes.
"""

import re
import unicodedata

from karaoke_engine.align.numbers import number_words

_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "´": "'", "`": "'"})
_SYMBOLS: dict[str, dict[str, str]] = {
    "gl": {"&": "e", "%": "por cento", "+": "máis"},
    "es": {"&": "y", "%": "por ciento", "+": "más"},
    "pt": {"&": "e", "%": "por cento", "+": "mais"},
    "en": {"&": "and", "%": "percent", "+": "plus"},
}
_DIGITS = re.compile(r"\d+")
_SPACES = re.compile(r"\s+")


def spoken(word: str, language: str) -> str:
    """Lowercase sung form: numbers and symbols in words, no punctuation; may be empty."""
    text = unicodedata.normalize("NFC", word).lower().translate(_APOSTROPHES)
    for symbol, said in _SYMBOLS.get(language, {}).items():
        text = text.replace(symbol, f" {said} ")
    text = _DIGITS.sub(lambda m: f" {number_words(int(m.group()), language) or m.group()} ", text)
    text = "".join(ch if ch.isalnum() or ch == "'" else " " for ch in text)
    tokens = (token.strip("'") for token in _SPACES.split(text))
    return " ".join(token for token in tokens if token)
