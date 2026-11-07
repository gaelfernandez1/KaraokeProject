"""What a web page adds to lyrics copied from it, taken out before the lyrics are read.

People paste lyrics straight from Genius, Musixmatch, Letras, AZLyrics, Google or a video
description, and the clipboard brings more than the song: song recommendations and ticket adverts
in the middle, the page title, contributors and translations at the top, credits, copyright and
links at the end, section labels written without brackets ("CORO:", "(Estribillo x2)", "Repetir
coro"), stage directions such as "(risas)" and the timings of subtitle files. This drops what is
never sung and rewrites the labels as the bracket headers parse_lyrics reads, so nobody has to
tidy the lyrics by hand.

A line goes only when no song would sing it: page text that could also be a sung line ("Solo",
"Ponte guapa", "Letra de amor") is only dropped at the top or the bottom of the paste, or not at
all. The result is plain lyrics text: stripping it again changes nothing.
"""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

# Section labels, by language; the weak ones are also ordinary words ("Ponte guapa", "Solo"),
# so alone on a line they only count when written as labels: "Ponte:", "(Solo)", "PONTE".
_STRONG_LABELS = (
    r"intro|introducci[oó]n|introduci[oó]n|introdu[cç][aã]o|outro|"
    r"(?:pre|pr[eé]|post|p[oó]s)[-\s]?(?:chorus|coro|estribillo|refr[aã]o|retrouso|hook|refrain)|"
    r"verse|verso|estrofa|estrofe|couplet|strophe|strofa|"
    r"chorus|coro|estribillo|refr[aã]o|refr[aá]n|retrouso|refrain|ritornell?o|refrany|tornada|"
    r"hook|bridge|interlude|interludio|interl[uú]dio|breakdown|instrumental"
)
_WEAK_LABELS = r"puente|ponte|pont|final|solo|break|drop|coda|parte|part"
_LABELS = rf"(?:{_STRONG_LABELS}|{_WEAK_LABELS})"
_QUALIFIER = r"(?:\d{1,2}|[ivx]{1,4}|final|last|[uú]ltim[oa]|derradeir[oa]|reprise|instrumental)"
# Repeat marks, as parse_lyrics reads them.
_MARK = r"(?:[xX\u00d7]\s?[2-9]|[2-9]\s?[xX\u00d7])"
_REPEAT = rf"(?:{_MARK}|\(\s*(?:{_MARK}|bis)\s*\)|bis)"
_TIMES = r"([2-9])\s*(?:veces|vezes|times|fois|volte|mal)"

_LABEL_LINE = re.compile(
    rf"^(?P<label>{_LABELS})(?P<qual>(?:\s+{_QUALIFIER})*)\b(?P<tail>.*)$", re.IGNORECASE
)
_REPEAT_TAIL = re.compile(rf"^\s*(?P<mark>{_REPEAT}|{_TIMES})\s*:?\s*$", re.IGNORECASE)
_WHO_TAIL = re.compile(r"^\s*\((?P<who>[^()]*)\)\s*:?\s*$")
_TEXT_TAIL = re.compile(r"^\s*(?P<sep>[:\u2013\u2014-])\s*(?P<text>.+)$")
_REPEAT_WORD = r"repetir|repite|rep[ií]tese|repetimos|se repite|repete|repeat|bis"
_REPEAT_LABEL = re.compile(
    rf"^(?:{_REPEAT_WORD})\s+(?:(?:el|la|lo|o|a|os|as|the|de|do|da|del)\s+)?"
    rf"(?P<label>{_LABELS})(?P<qual>(?:\s+{_QUALIFIER})*)\b(?P<tail>.*)$",
    re.IGNORECASE,
)
_LABEL_REPEAT_WORD = re.compile(rf"^\s*\(?\s*(?:{_REPEAT_WORD})\s*\)?\s*:?\s*$", re.IGNORECASE)
_DECORATION = '*_~=#\u2013\u2014-\u00ab\u00bb"\u201c\u201d \t'
_CONNECTORS = frozenset({
    "e", "y", "i", "&", "and", "x", "ft", "ft.", "feat", "feat.", "featuring", "con", "with",
    "com", "+", "/", "et", "und", "vs", "vs.",
})  # fmt: skip

# Never sung, wherever they are.
_NEVER_SUNG = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"https?://|www\.\S|[\w.+-]+@[\w-]+\.[a-z]{2,}",  # links and e-mail
        r"[\u00a9\u2117\u00ae]",  # © ℗ ®
        r"^\d+\s*contributors?",  # Genius, glued to what follows
        r"^you might also like$",
        r"^get tickets as low as\b",
        r"^lyrics (?:powered|licensed|provided)\b|\bprovided by (?:musixmatch|lyricfind)\b",
        r"^submit corrections$|^esta letra (?:ainda )?n[aã]o foi revisad|essa informa[cç][aã]o "
        r"est[aá] errada",
        r"^genius\b.*\b(?:translations?|traducciones|tradu[cç][oõ]es|traductions|"
        r"[uü]bersetzungen|traduzioni|traduccions|romanizations?|[cç]eviriler|t[lł]umaczenia|"
        r"переводы)\b",
        # Another song's translation: "Artist - Title (Traducción al Español)".
        r"\s[-\u2013]\s.+\((?:[^()]*\b(?:translation|traducci[oó]n|tradu[cç][aã]o|"
        r"traduction|[uü]bersetzung|traduzione|traducci[oó]|[cç]eviri|t[lł]umaczenie|перевод|"
        r"romanized|romanization)\b[^()]*)\)$",
        # Credits and links of a description: "Prod: …", "Writer(s): …", "Instagram: …".
        r"^(?:writer\(s\)|writers?|songwriters?|songwriter\(s\)|composers?|composer\(s\)|"
        r"lyricists?|lyrics by|music by|words by|words and music by|produced by|producers?|"
        r"producer\(s\)|prod\.?|beats?|mix(?:ed|ing)?(?:\s*(?:&|and|y|e|/)\s*master(?:ed|ing)?)?|"
        r"master(?:ed|ing)?|recorded (?:at|by)|engineer|compositor(?:es|as?)?|"
        r"composi[cç][aã]o|composici[oó]n|compuest[ao] por|compost[ao] por|escrit[ao] por|"
        r"autor(?:es|as?)?|letra|letras|lyrics|m[uú]sica|letra (?:y|e) m[uú]sica|"
        r"producci[oó]n|producid[ao] por|produ[cç][aã]o|produzid[ao] por|arreglos|arranjos|"
        r"mezcla|mistura|grabaci[oó]n|gravaci[oó]n|grabado en|gravado en|v[ií]deo|videoclip|"
        r"direcci[oó]n|dire[cç][aã]o|dirixido por|dirigido por|directed by|dir\.?|realizaci[oó]n|"
        r"label|sello|selo|publishers?|editora|source|fuente|fonte|instagram|ig|spotify|youtube|"
        r"tiktok|twitter|facebook|fb|soundcloud|bandcamp|apple music|deezer|twitch|web|website|"
        r"booking|contacto|contact|management|e-?mail)\s*:",
        r"^(?:prod\.|produced by|producid[ao] por|produzid[ao] por|beat by|mixed by|mastered by)"
        r"\s+\S",
        # Timings: subtitle files, video transcripts, verse numbers alone.
        r"^\d{1,2}:\d{2}:\d{2}[,.]\d{1,3}\s*-->",
        r"^\d{1,2}:\d{2}(?::\d{2})?$",
        r"^[(\[]?\d{1,3}[.):\]]?$",
    )
]
# LRC tags ([ti:Title], [ar:Artist]…) are written in lowercase; a header «[Al: Ana]» is not one.
_LRC_TAG = re.compile(r"^\[(?:ti|ar|al|au|by|length|offset|re|ve|id|la|lang|tool|#)\s*:[^\]]*\]$")
_HASHTAGS = re.compile(r"^(?:[#@]\S+\s*)+$")

# Page text that could also be sung: dropped only above or below the lyrics.
_PAGE_EDGE = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^translations?\b",  # Genius
        r"^\d*embed$|^cancel$|^how to format lyrics\b|\bread more$",
        r"^(?:letra|letras|lyrics?|paroles|testo|songtext|tekst)\s*:?$",
        r"^(?:letra|lyrics|paroles|testo|songtext)\s+(?:de|da|do|of|to|von|di|del|for)\s+.+\s"
        r"[-\u2013\u2014]\s.+$",
        r"[(\[][^)\]]*\b(?:official|oficial|video|v[ií]deo|videoclip|lyric video|lyrics?|letra|"
        r"visuali[sz]er|audio)\b[^)\]]*[)\]]",  # "Ana - Mar (Video Oficial)"
        r"^(?:enviad[ao] por|legendad[ao] por|revis(?:ad[ao]|[oõ]es) por|traducid[ao] por|"
        r"traduzid[ao] por)\s+\S",
        r"^(?:ver|show|see) (?:tradu[cç][aã]o|traducci[oó]n|tradución|translation)\b",
        r"^(?:tradu[cç][aã]o|traducci[oó]n|tradución|translation)$",
        r"^thanks to .+ for\b|^report a problem$",
        # Credits without a colon, which a sung line could also start with.
        r"^(?:written|composed|directed|produced|mixed|recorded|filmed|edited) by\s+\S",
        r"^(?:dirixid[oa]|dirigid[oa]|producid[oa]|produzid[oa]|realizad[oa]|gravad[oa]|"
        r"grabad[oa]|mesturad[oa]|mezclad[oa]|escrit[oa]|compost[oa]|compuest[oa]) por\s+\S",
        r"^(?:suscr[ií]bete|subscr[ií]bete|subscribe|s[uú]scribete)\b",
        r"^(?:esc[uú]chal[ao]|esc[oó]ital[ao]|escoita|escucha|listen|stream|ouve|ou[cç]a|"
        r"disponible|dispo[ñn]ible|dispon[ií]vel|available|ya disponible|xa dispo[ñn]ible|"
        r"j[aá] dispon[ií]vel|out now)\b.*\b(?:spotify|youtube|apple music|deezer|tidal|"
        r"amazon music|plataformas|platforms|streaming)\b",
    )
]
_PAGE_TITLE = re.compile(r"^\S.*\sLyrics$|^[\"\u201c].+[\"\u201d] lyrics$")  # Genius, AZLyrics
_LANGUAGES = frozenset({
    "english", "español", "espanol", "português", "portugues", "français", "francais",
    "deutsch", "italiano", "galego", "català", "catala", "euskara", "polski", "türkçe",
    "turkce", "русский", "українська", "nederlands", "svenska", "norsk", "dansk", "suomi",
    "română", "magyar", "čeština", "slovenčina", "hrvatski", "srpski", "ελληνικά", "עברית",
    "العربية", "فارسی", "हिन्दी", "日本語", "한국어", "简体中文", "繁體中文", "中文", "filipino",
    "tagalog",
    "azərbaycanca", "bosanski", "slovenščina", "lietuvių", "latviešu", "eesti", "shqip",
    "български", "македонски", "ไทย", "romanization", "romanized",
})  # fmt: skip

# Genius: "You might also like" then three songs, each its title and its artist.
_MARKER = "You might also like"
_TICKETS = re.compile(r"^Get tickets as low as\b")
_GLUED_TICKETS = re.compile(r"(?<=\S)(?=Get tickets as low as\b)")
_SEE_LIVE = re.compile(r"^See .+ Live$")
_GLUED_EMBED = re.compile(r"^(?P<keep>.*?)\d*Embed$")

# Stage directions in parentheses: not sung, unless the line sings the same word as an echo.
_DIRECTIONS = (
    r"risas?|risos|r[ií]e|riendo|rindo|laughs?|laughing|laughter|hablad[oa]|hablando|falad[oa]|"
    r"falando|spoken(?: word)?|speaking|recitad[oa]|recitando|susurrad[oa]|susurrando|susurro|"
    r"sussurrad[oa]|whisper(?:ed|ing)?|gritad[oa]|gritando|shout(?:ed|ing)|screaming|"
    r"instrumental|m[uú]sica|music|inaudible|ininteligible|unintelligible|incomprensible|"
    r"aplausos?|applause|silencio|silence|pausa|pause|fade(?: out| in)?|guitar solo|"
    r"solo de (?:guitarra|gaita|bater[ií]a|piano|saxo)|tarareo|tarareando|humming|suspiros?|"
    r"sighs?"
)
_INLINE_PAREN = re.compile(r"\(([^()]*)\)")
_DIRECTION = re.compile(rf"^(?:{_DIRECTIONS}|{_STRONG_LABELS})(?:\s+{_QUALIFIER})*$", re.IGNORECASE)
_LEADING_PAREN = re.compile(r"^\((?P<inner>[^()]+)\)\s*(?P<rest>\S.*)$")
_LRC_TIMES = re.compile(r"^(?:\s*\[\d{1,3}:\d{2}(?:[.:]\d{1,3})?\])+\s*")
_WORD_TIMES = re.compile(r"\s*<\d{1,3}:\d{2}(?:[.:]\d{1,3})?>\s*")
_INVISIBLE = re.compile("[\u200b-\u200d\u2060\ufeff]")
_BRACKET_LINE = re.compile(r"^\[[^\]]*\]")
_GLUED_BRACKET = re.compile(r"(?<=\S)(?=\[[^\[\]]*\])|(?<=\])(?=\S)")
_WORD = re.compile(r"\w+")
# Words that decorate a title above the lyrics: "Letra de Mar - Ana", "Mar Lyrics".
_TITLE_FILLERS = frozenset({
    "letra", "letras", "lyrics", "lyric", "paroles", "testo", "songtext", "tekst", "de",
    "da", "do", "del", "of", "to", "by", "por", "von", "di", "ft", "feat", "featuring",
    "official", "oficial", "video", "vídeo", "audio",
})  # fmt: skip


def strip_page_text(text: str, *, title: str | None = None, artist: str | None = None) -> str:
    """The lyrics in `text` without what the page they come from adds (see the module).

    With the song's `title` and `artist`, lines above the lyrics that only name the song go too.
    """
    text = unicodedata.normalize("NFC", _INVISIBLE.sub("", text))
    rows = _unglue(text.splitlines())
    rows = _drop_genius_inserts(rows)
    names = _Names.of(title, artist)
    start, end = _lyrics_span(rows, names)
    rows = rows[start:end]
    shouting = _mostly_capitals(rows)
    out: list[str] = []
    previous = ""
    for row in rows:
        for line in _clean(row.strip(), previous, shouting):
            out.append(line)
            if line:
                previous = line
    return "\n".join(out).strip("\n") + "\n" if any(out) else ""


def _label_line(row: str, *, shouting: bool = False) -> list[str] | None:
    """A section label written without brackets, as parse_lyrics headers (plus the sung line
    that follows on the same row, if any), or None if `row` is not one."""
    core = row.strip(_DECORATION)
    decorated = core != row.strip()
    for opening, closing in ("()", "{}"):
        if core.startswith(opening) and core.endswith(closing) and core.count(opening) == 1:
            core, decorated = core[1:-1].strip(), True
    if core.endswith(":"):
        core, decorated = core[:-1].rstrip(), True
    if not shouting and core.isupper():
        decorated = True
    repeat = _REPEAT_LABEL.match(core)
    if repeat:
        count = _times(repeat.group("tail"))
        if count is None:
            return None
        return [_header(repeat.group("label") + repeat.group("qual"), None, count)]
    match = _LABEL_LINE.match(core)
    if not match:
        return None
    label = match.group("label") + match.group("qual")
    tail = match.group("tail")
    if not tail.strip():
        weak = re.fullmatch(_WEAK_LABELS, match.group("label"), re.IGNORECASE)
        if weak and not decorated and not match.group("qual"):
            return None
        return [_header(label, None, 1)]
    if _REPEAT_TAIL.match(tail) or _LABEL_REPEAT_WORD.match(tail):
        return [_header(label, None, _times(tail) or 1)]
    who = _WHO_TAIL.match(tail)
    if who:
        return [_header(label, who.group("who").strip() or None, 1)]
    text = _TEXT_TAIL.match(tail)
    if text:
        if _looks_like_names(text.group("text")):
            return [_header(label, text.group("text").strip(), 1)]
        if text.group("sep") == ":":
            return [_header(label, None, 1), text.group("text").strip()]
    return None


def _header(label: str, singer: str | None, count: int) -> str:
    header = f"[{label.strip()}: {singer}]" if singer else f"[{label.strip()}]"
    return f"{header} x{count}" if count > 1 else header


def _times(tail: str) -> int | None:
    """How many times a label's tail asks for: 1 for none, None if the tail is something else."""
    tail = tail.strip().rstrip(":").strip()
    if not tail or _LABEL_REPEAT_WORD.match(tail):
        return 1
    if not _REPEAT_TAIL.match(tail):
        return None
    digit = re.search(r"[2-9]", tail)
    return int(digit.group()) if digit else 2


def _looks_like_names(text: str) -> bool:
    """«Ana», «9Louro & ORTIGA», «Todos»: who sings, not a sung line («Eu canto contigo»)."""
    words = text.replace(",", " ").split()
    return 0 < len(words) <= 6 and all(
        word.casefold() in _CONNECTORS or word[0].isupper() or word[0].isdigit() for word in words
    )


def _unglue(rows: Iterable[str]) -> list[str]:
    """Splits what a copy glued together: «…(Yeah)You might also like[Coro: Ana]» is three rows.

    A Genius marker glued to a line comes without its songs, and stands for the blank line
    between two stanzas, where Genius puts it.
    """
    out: list[str] = []
    for row in rows:
        text = row.replace(_MARKER, "\n\n") if row.strip() != _MARKER else row
        for piece in _GLUED_TICKETS.sub("\n", text).split("\n"):
            out += _split_glued_labels(piece)
    return out


def _split_glued_labels(row: str) -> list[str]:
    pieces = [piece for piece in _GLUED_BRACKET.split(row) if piece]
    if len(pieces) < 2 or not any(_glued_label(piece) for piece in pieces):
        return [row]
    out, text = [], ""
    for piece in pieces:
        if _glued_label(piece):
            if text.strip():
                out.append(text)
            out.append(piece)
            text = ""
        else:
            text += piece
    if text.strip():
        out.append(text)
    return out


def _glued_label(piece: str) -> bool:
    """«[Verso 1: Ana]» or «[Coro]», but not «[?]», «[00:12.34]» or «[inaudible]»."""
    if not (piece.startswith("[") and piece.endswith("]")):
        return False
    inside = piece[1:-1]
    return bool(re.search(r"[^\W\d_]", inside)) and (
        ":" in inside or _LABEL_LINE.match(inside) is not None
    )


def _drop_genius_inserts(rows: list[str]) -> list[str]:
    """Song recommendations ("You might also like" and three title-artist pairs) and ticket
    adverts ("See Ana Live", "Get tickets as low as $45") that Genius puts inside the lyrics."""
    out: list[str] = []
    i = 0
    while i < len(rows):
        row = rows[i].strip()
        i += 1
        if _TICKETS.match(row):
            if out and _SEE_LIVE.match(out[-1].strip()):
                out.pop()
            continue
        if row != _MARKER:
            out.append(rows[i - 1])
            continue
        for _ in range(3):
            if i + 1 >= len(rows) or not _recommended(rows[i], rows[i + 1]):
                break
            i += 2
        out.append("")
    return out


def _recommended(song: str, artist: str) -> bool:
    """A title and an artist, not the lyrics going on."""
    song, artist = song.strip(), artist.strip()
    return bool(
        song and artist and len(artist.split()) <= 6
        and not any(_BRACKET_LINE.match(row) or _label_line(row) for row in (song, artist))
    )  # fmt: skip


@dataclass(frozen=True)
class _Names:
    """The words of the song's title and artist, to know a line that only names the song."""

    title: frozenset[str]
    artist: frozenset[str]

    @classmethod
    def of(cls, title: str | None, artist: str | None) -> "_Names | None":
        words = cls(_words(title or ""), _words(artist or "") - _CONNECTORS)
        return words if words.title or words.artist else None

    def classify(self, row: str) -> tuple[bool, bool] | None:
        """(decorated, whole): None if the row says more than the song's name."""
        words = _words(row)
        known = self.title | self.artist
        rest = words - known - _CONNECTORS
        if not words & known or not rest <= _TITLE_FILLERS:
            return None
        decorated = bool(rest) or bool(words & self.title and words & self.artist)
        return decorated, bool(words & self.artist) or decorated


def _words(text: str) -> frozenset[str]:
    folded = unicodedata.normalize("NFKD", text.casefold())
    plain = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return frozenset(_WORD.findall(plain))


def _lyrics_span(rows: list[str], names: _Names | None) -> tuple[int, int]:
    """Where the lyrics start and end once the page text above and below them is left out."""
    start = _after_description(rows)
    while start < len(rows):
        row = rows[start].strip()
        if not (not row or _junk(row) or _top_junk(row) or _names_the_song(rows, start, names)):
            break
        start += 1
    end = len(rows)
    while end > start:
        row = rows[end - 1].strip()
        if not row or _junk(row):
            end -= 1
            continue
        glued = _GLUED_EMBED.match(row)
        if glued and glued.group("keep") and not glued.group("keep").endswith(" "):
            rows[end - 1] = glued.group("keep")
        break
    return start, end


def _after_description(rows: list[str]) -> int:
    """Genius may start with the song's description, which ends in "Read More"."""
    seen = 0
    for i, row in enumerate(rows):
        if _BRACKET_LINE.match(row.strip()) or seen > 30:
            break
        if row.strip():
            seen += 1
        if row.rstrip().endswith("Read More"):
            return i + 1
    return 0


def _junk(row: str) -> bool:
    """Page text that may sit above or below the lyrics."""
    return _never_sung(row) or any(pattern.search(row) for pattern in _PAGE_EDGE)


def _top_junk(row: str) -> bool:
    """Only above the lyrics: Genius's title and its list of translations."""
    return bool(_PAGE_TITLE.match(row)) or row.casefold() in _LANGUAGES


def _names_the_song(rows: list[str], i: int, names: _Names | None) -> bool:
    """A line above the lyrics that only names the song: «Letra de Mar - Ana» always; a bare
    «Mar» only if a header follows or its stanza names the artist too, since many songs open
    with their title."""
    if names is None:
        return False
    found = names.classify(rows[i].strip())
    if found is None:
        return False
    decorated, _ = found
    if decorated:
        return True
    artist = False
    for raw in rows[i:]:
        row = raw.strip()
        if not row:
            break
        if _BRACKET_LINE.match(row) or _label_line(row):
            return True
        found = names.classify(row)
        if found is None:
            return False
        artist = artist or found[1]
    return artist


def _never_sung(row: str) -> bool:
    return (
        any(pattern.search(row) for pattern in _NEVER_SUNG)
        or bool(_LRC_TAG.match(row))
        or bool(_HASHTAGS.match(row))
    )


def _mostly_capitals(rows: list[str]) -> bool:
    """Lyrics written all in capitals: then capitals do not mark a label."""
    lettered = [row for row in rows if any(ch.isalpha() for ch in row)]
    return len(lettered) > 3 and sum(row.isupper() for row in lettered) * 2 > len(lettered)


def _clean(row: str, previous: str, shouting: bool) -> list[str]:
    """One row of the lyrics as parse_lyrics should read it: none, one or two rows."""
    if not row:
        return [""]
    if _never_sung(row):
        return []
    row = _WORD_TIMES.sub(" ", _LRC_TIMES.sub("", row)).strip()
    if not row:
        return []
    if row.startswith("{") and row.endswith("}") and row.count("{") == 1:
        row = f"[{row[1:-1]}]"
    if _BRACKET_LINE.match(row):
        return [row]
    labelled = _label_line(row, shouting=shouting)
    if labelled is not None:
        return labelled[:1] + _sung(labelled[1:], previous)
    leading = _LEADING_PAREN.match(row)
    if leading:
        labelled = _label_line(f"({leading.group('inner')})", shouting=shouting)
        if labelled is not None:
            return labelled + _sung([leading.group("rest")], previous)
    return _sung([row], previous)


def _sung(rows: list[str], previous: str) -> list[str]:
    """The rows without their stage directions, leaving out those with nothing left to sing."""
    cleaned = (_drop_directions(row, previous) for row in rows)
    return [row for row in cleaned if any(ch.isalnum() for ch in row)]


def _drop_directions(row: str, previous: str) -> str:
    """«Vai o vento (risas)» → «Vai o vento», but «Pon a música (música)» is an echo."""
    sung = _words(_INLINE_PAREN.sub(" ", row)) | _words(previous)

    def keep(match: re.Match[str]) -> str:
        inside = match.group(1).strip()
        if _DIRECTION.match(inside) and not _words(inside) <= sung:
            return " "
        return match.group()

    return re.sub(r"\s+", " ", _INLINE_PAREN.sub(keep, row)).strip()
