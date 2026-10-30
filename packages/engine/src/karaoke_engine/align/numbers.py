"""Numbers as they are sung, from 0 to 9999, in the languages the bench covers with lyrics.

The alignment models only know letters: "2024" in a lyric must become the words a singer says.
No dependency covers Galician, so the rules live here, one table per language.
"""

from dataclasses import dataclass


def _w(words: str) -> tuple[str, ...]:
    return tuple(words.split())


@dataclass(frozen=True)
class _Rules:
    below_20: tuple[str, ...]
    tens: tuple[str, ...]  # 20, 30, ... 90
    tens_and: str  # joins tens and units: "vinte e un"
    hundred_alone: str  # 100
    hundreds: tuple[str, ...]  # 1xx, 200, ... 900
    hundreds_and: str  # joins hundreds and the rest: "cento un", "cento e um"
    thousand: str
    special: dict[int, str]  # irregular forms (Spanish 21-29)


_GL = _Rules(
    below_20=_w(
        "cero un dous tres catro cinco seis sete oito nove dez once doce trece "
        "catorce quince dezaseis dezasete dezaoito dezanove"
    ),
    tens=_w("vinte trinta corenta cincuenta sesenta setenta oitenta noventa"),
    tens_and=" e ",
    hundred_alone="cen",
    hundreds=_w(
        "cento douscentos trescentos catrocentos cincocentos seiscentos "
        "setecentos oitocentos novecentos"
    ),
    hundreds_and=" ",
    thousand="mil",
    special={},
)
_ES = _Rules(
    below_20=_w(
        "cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce "
        "trece catorce quince dieciséis diecisiete dieciocho diecinueve"
    ),
    tens=_w("veinte treinta cuarenta cincuenta sesenta setenta ochenta noventa"),
    tens_and=" y ",
    hundred_alone="cien",
    hundreds=_w(
        "ciento doscientos trescientos cuatrocientos quinientos seiscientos "
        "setecientos ochocientos novecientos"
    ),
    hundreds_and=" ",
    thousand="mil",
    special={
        21: "veintiuno",
        22: "veintidós",
        23: "veintitrés",
        24: "veinticuatro",
        25: "veinticinco",
        26: "veintiséis",
        27: "veintisiete",
        28: "veintiocho",
        29: "veintinueve",
    },
)
_PT = _Rules(
    below_20=_w(
        "zero um dois três quatro cinco seis sete oito nove dez onze doze treze "
        "catorze quinze dezasseis dezassete dezoito dezanove"
    ),
    tens=_w("vinte trinta quarenta cinquenta sessenta setenta oitenta noventa"),
    tens_and=" e ",
    hundred_alone="cem",
    hundreds=_w(
        "cento duzentos trezentos quatrocentos quinhentos seiscentos setecentos "
        "oitocentos novecentos"
    ),
    hundreds_and=" e ",
    thousand="mil",
    special={},
)
_EN = _Rules(
    below_20=_w(
        "zero one two three four five six seven eight nine ten eleven twelve "
        "thirteen fourteen fifteen sixteen seventeen eighteen nineteen"
    ),
    tens=_w("twenty thirty forty fifty sixty seventy eighty ninety"),
    tens_and=" ",
    hundred_alone="one hundred",
    hundreds=tuple(
        f"{unit} hundred" for unit in _w("one two three four five six seven eight nine")
    ),
    hundreds_and=" ",
    thousand="thousand",
    special={},
)
_RULES = {"gl": _GL, "es": _ES, "pt": _PT, "en": _EN}


def number_words(n: int, language: str) -> str | None:
    """The number in words, or None for other languages or numbers past 9999."""
    rules = _RULES.get(language)
    if rules is None or not 0 <= n <= 9999:
        return None
    if n < 1000:
        return _below_1000(n, rules)
    thousands, rest = divmod(n, 1000)
    head = rules.thousand
    if thousands > 1 or language == "en":
        head = f"{_below_1000(thousands, rules)} {rules.thousand}"
    return head if rest == 0 else f"{head} {_below_1000(rest, rules)}"


def _below_1000(n: int, rules: _Rules) -> str:
    if n == 100:
        return rules.hundred_alone
    hundreds, rest = divmod(n, 100)
    if hundreds == 0:
        return _below_100(n, rules)
    head = rules.hundreds[hundreds - 1]
    return head if rest == 0 else f"{head}{rules.hundreds_and}{_below_100(rest, rules)}"


def _below_100(n: int, rules: _Rules) -> str:
    if n in rules.special:
        return rules.special[n]
    if n < 20:
        return rules.below_20[n]
    tens, unit = divmod(n, 10)
    head = rules.tens[tens - 2]
    return head if unit == 0 else f"{head}{rules.tens_and}{rules.below_20[unit]}"
