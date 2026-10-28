import logging

import pyphen

logger = logging.getLogger(__name__)

# ISO 639-1 codes (as returned by Whisper) -> pyphen dictionary codes.
# Verified against pyphen 0.14.0: it ships base codes for gl/es/ca/fr (no
# regional variant) and full codes for pt_PT/en_US/it_IT/de_DE. Basque (eu) has
# no dictionary at all, so it is intentionally absent and falls back to Spanish.
SUPPORTED_LANGS: dict[str, str] = {
    "gl": "gl",
    "es": "es",
    "pt": "pt_PT",
    "en": "en_US",
    "ca": "ca",
    "fr": "fr",
    "it": "it_IT",
    "de": "de_DE",
}

_DEFAULT_LANG = "es"
_SYLLABLE_SEP = "-"

_dict_cache: dict[str, pyphen.Pyphen] = {}


def _get_dict(lang: str) -> pyphen.Pyphen:
    pyphen_code = SUPPORTED_LANGS.get(lang)
    if pyphen_code is None:
        logger.warning("Unsupported language '%s', falling back to '%s'", lang, _DEFAULT_LANG)
        pyphen_code = SUPPORTED_LANGS[_DEFAULT_LANG]
    if pyphen_code not in _dict_cache:
        logger.info("Loading pyphen dictionary '%s' for language '%s'", pyphen_code, lang)
        _dict_cache[pyphen_code] = pyphen.Pyphen(lang=pyphen_code)
    return _dict_cache[pyphen_code]


def syllabify(word: str, lang: str = "es") -> list[str]:
    return _get_dict(lang).inserted(word).split(_SYLLABLE_SEP)


def syllabify_text(text: str, lang: str = "es") -> str:
    return " ".join(_SYLLABLE_SEP.join(syllabify(token, lang)) for token in text.split())
