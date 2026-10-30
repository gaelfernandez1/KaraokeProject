"""Galician pronouns that follow their verb are written onto it: "collín che" → "collinche".

Lyrics sites often write them apart, as Spanish does. Galician joins a pronoun to the verb before
it (enclisis) unless something calls it in front of the next verb (non, que, xa, nunca, cando…),
and the joined word follows the usual accent rules: "dixo lle" → "díxolle", "dará che" →
"darache", "dá lle" → "dálle". Only the space and the accent change: dialectal spelling (gheada,
seseo) stays as written.

To stay on the safe side a pronoun is joined only when it cannot be anything else (not "o", "a",
"nos" or "se") and the word before is a verb form this module knows: common verbs conjugated
(regular paradigms plus the irregular ones) and gerunds.
"""

import unicodedata

from karaoke_contracts import Line, Part, Word
from karaoke_engine.align.syllables import syllables

# Pronouns (and their contractions) that are never an article, a preposition or a conjunction.
PRONOUNS = {
    "me", "te", "che", "lle", "lles", "vos",
    "mo", "ma", "mos", "cho", "cha", "chos", "chas", "llo", "lla", "llos", "llas",
    "llelo", "llela", "llelos", "llelas", "nolo", "nola", "nolos", "nolas",
    "volo", "vola", "volos", "volas",
}  # fmt: skip

# After these the pronoun belongs in front of the next verb (proclisis), or the word is not a
# verb although it looks like one ("como" = "as", "para" = "for", "nada" = "nothing").
PROCLITIC = {
    "non", "nunca", "xamais", "tampouco", "nin", "ninguén", "nada", "ningún", "ningunha",
    "que", "se", "si", "cando", "como", "onde", "canto", "canta", "cantos", "cantas", "quen",
    "cal", "cales", "porque", "pois", "mentres", "aínda", "ata", "desde", "dende", "xa",
    "tamén", "sempre", "só", "soamente", "ben", "mal", "máis", "menos", "moito", "moita",
    "pouco", "pouca", "bastante", "case", "quizais", "quizá", "talvez", "seica", "acaso",
    "así", "tan", "tanto", "todo", "toda", "todos", "todas", "algo", "alguén", "algún",
    "algunha", "outro", "outra", "calquera", "cada", "para", "por", "entre", "sobre", "baixo",
    "contra", "fora", "fóra", "e", "ou", "mais", "pero", "eu", "ti", "tu", "el", "ela",
    "nós", "vós", "eles", "elas", "vostede", "isto", "iso", "aquilo",
}  # fmt: skip

_ENDINGS = {
    "ar": (
        "o as a amos ades an ei aches ou astes aron aba abas abamos abades aban ara aras "
        "aramos arades aran arei arás ará aremos aredes arán aría arías ariamos ariades arían "
        "e es emos edes en ase ases ásemos ásedes asen ar ares armos ardes aren ade ando"
    ),
    "er": (
        "o es e emos edes en ín iches eu estes eron ía ías iamos iades ían era eras eramos "
        "erades eran erei erás erá eremos eredes erán ería erías eriamos eriades erían a as "
        "amos ades an ese eses ésemos ésedes esen er eres ermos erdes eren ede endo"
    ),
    "ir": (
        "o es e imos ides en ín iches iu istes iron ía ías iamos iades ían ira iras iramos "
        "irades iran irei irás irá iremos iredes irán iría irías iriamos iriades irían a as "
        "amos ades an ise ises ísemos ísedes isen ir ires irmos irdes iren ide indo"
    ),
}

_VERBS = """
abandonar abrazar acabar aceptar achar achegar acompañar acordar adorar afastar afogar agardar
agarrar agochar alcanzar alegrar amar andar apagar apertar apostar apuntar arrancar arrastrar
arrimar asustar atopar atrapar avisar axudar bailar baixar beixar berrar bicar borrar botar
brillar buscar calar calmar cambiar camiñar cansar cantar casar celebrar chamar chegar chorar
coidar colgar comezar comprar confesar conquistar contar contestar cortar crear criar cruzar
culpar curar deixar deitar desexar despertar desfrutar disfrutar dubidar durar empezar enamorar
encantar encontrar enganar ensinar entrar entregar enviar escapar escoitar esperar espertar
esquivar estrañar extrañar explicar falar fallar fartar fechar festexar fiar fumar gañar ganar
gardar gastar gozar gritar guiar gustar importar intentar invitar lanzar lembrar levantar levar
librar ligar limpar loitar lograr mandar marchar matar mirar mostrar mudar necesitar negar notar
ocultar odiar ollar olvidar pagar pasar pasear pechar pegar pelexar pensar perdoar pillar pintar
pisar preguntar preparar presentar prestar probar quebrar quedar queimar quentar quitar rachar
regalar rematar respirar revelar rexeitar rezar robar rogar roubar saltar salvar sacar saudar
secar separar soltar sonar soñar soportar sospeitar superar suspirar tentar terminar tirar tocar
tomar traballar tratar trocar usar viaxar visitar voar voltar xantar xogar xuntar xurar
aprender atender bater beber coller comer conceder correr deber defender depender devolver
doer encender entender envolver escoller esconder lamber meter morrer mover perder prender
prometer querer recoller render resolver responder romper sorprender temer vender verter volver
coñecer esquecer merecer nacer ofrecer parecer aparecer desaparecer agradecer crecer padecer
recoñecer convencer torcer vencer acender
abrir acudir admitir compartir cubrir decidir describir discutir dividir durmir escribir existir
ferir fuxir insistir medir mentir partir pedir permitir prohibir recibir repetir resistir seguir
sentir servir subir sufrir unir vestir vivir consentir sorrir
"""

# Stem changes of some -ir verbs: e→i in the first person (sinto) and u→o in the second and third
# (sobes).
_E_TO_I = {"sentir", "mentir", "servir", "seguir", "vestir", "pedir", "medir", "ferir", "repetir",
           "consentir"}  # fmt: skip
_U_TO_O = {"subir", "fuxir", "durmir", "cubrir", "acudir"}

# Forms of irregular verbs (and irregular forms of otherwise regular ones).
_IRREGULAR = """
son es é somos sodes fun fuches foi fomos fostes foron era eras eramos erades eran fora foras
foramos forades foran serei serás será seremos seredes serán sería serías sexa sexas sexamos
sexades sexan fose foses sede ser sendo
estou estás está estamos estades están estiven estiveches estivo estivemos estivestes estiveron
estaba estabas estivera estea esteas estean estivese estar estando
teño tes ten temos tedes teñen tiven tiveches tivo tivemos tivestes tiveron tiña tiñas tiñamos
tiñan tivera terei terás terá teremos teredes terán tería terías teña teñas teñamos teñan tivese
ter tendo
hei has ha habemos habedes han houben houbo había haberei haxa houbese haber
vou vas vai imos ides van ía ías iamos iades ían irei irás irá iremos iredes irán iría vaia vaias
vaiamos vaian ir indo
veño vés vén vimos vindes veñen vin viñeches veu viñemos viñestes viñeron viña viñas viñera virei
virás virá virei veña veñas viñese vir vindo
fago fas fai facemos facedes fan fixen fixeches fixo fixemos fixestes fixeron facía facías fixera
farei farás fará faremos faredes farán faría farías faga fagas fagamos fagan fixese facede facer
facendo
digo dis di dicimos dicides din dixen dixeches dixo diximos dixemos dixestes dixeron dicía dicías
dixera direi dirás dirá diremos diredes dirán diría dirías diga digas digamos digan dixese dicide
dicir dicindo
podo podes pode podemos podedes poden puiden puideches puido puidemos puidestes puideron podía
puidera poderei poderá podería poida poidas puidese poder podendo
quixen quixeches quixo quixemos quixestes quixeron quixera queira queiras queiramos queiran quixese
sei sabes sabe sabemos sabedes saben souben soubeches soubo soubemos soubestes souberon sabía
soubera saberei saberá sabería saiba saibas soubese saber sabendo
dou dás dá damos dades dan dei deches deu demos destes deron daba dabas dera darei darás dará
daremos daredes darán daría darías dea deas deamos dean dese dade dar dando
vexo ves ve vemos vedes ven vin viches viu vimos vistes viron vía vías vira verei verás verá
vería vexa vexas vexamos vexan vise vede ver vendo
poño pos pon poñemos poñedes poñen puxen puxeches puxo puxemos puxestes puxeron puña puñas puxera
porei porás porá poría poña poñas puxese poñede pór poñendo
traio traes trae traemos traedes traen trouxen trouxeches trouxo trouxemos trouxestes trouxeron
traía trouxera traerei traerá traería traia traias trouxese traede traer traendo
leo les le lemos ledes len lin liches leu lemos lestes leron lía lera lerei lerá lería lea lese
ler lendo
creo cres cre cremos credes cren crin criches creu creron cría crera crerei crea crese crer crendo
oio oes oe oímos oídes oen oín oíches oíu oímos oístes oíron oía oíra oirei oirá oiría oia oíse
oíde oír oíndo
saio saes sae saímos saídes saen saín saíches saíu saíron saía saíra sairei sairá sairía saia
saíse saíde saír saíndo
caio caes cae caín caíches caeu caeron caía caera caerei caia caese caer caendo
río ris ri rimos rides rin rin riches riu riron ría rira rirei rirá ría rise ride rir rindo
valer vale valen valía valeu valerá
"""


def _forms(infinitive: str) -> set[str]:
    stem, kind = infinitive[:-2], infinitive[-2:]
    forms = {stem + ending for ending in _ENDINGS[kind].split()}
    if kind == "er" and stem.endswith("c"):  # coñecer → coñezo, coñeza
        soft = stem[:-1] + "z"
        forms |= {soft + e for e in ("o", "a", "as", "amos", "ades", "an")}
    if kind == "ar" and stem[-1:] in ("c", "g", "z"):  # buscar → busquei, busque
        hard = {"c": stem[:-1] + "qu", "g": stem + "u", "z": stem[:-1] + "c"}[stem[-1]]
        forms |= {hard + e for e in ("ei", "e", "es", "emos", "edes", "en")}
    if infinitive in _E_TO_I:  # sentir → sinto, sinta
        changed = stem[::-1].replace("e", "i", 1)[::-1]
        forms |= {changed + e for e in ("o", "a", "as", "amos", "ades", "an")}
    if infinitive in _U_TO_O:  # subir → sobes, sobe
        changed = stem[::-1].replace("u", "o", 1)[::-1]
        forms |= {changed + e for e in ("es", "e", "en")}
    return forms


VERB_FORMS: frozenset[str] = frozenset(
    {form for verb in _VERBS.split() for form in _forms(verb)} | set(_IRREGULAR.split())
)


def _variants(word: str) -> set[str]:
    """Dialectal spellings of a form: gheada (jaño for gaño) and a Spanish j for x (dijen)."""
    return {word, word.replace("j", "g"), word.replace("j", "x"), word.replace("h", "g")}


def is_verb(word: str) -> bool:
    lower = word.lower()
    if lower in PROCLITIC:
        return False
    if any(v in VERB_FORMS for v in _variants(lower)):
        return True
    # Gerunds: esperando, facendo, partindo.
    return len(lower) >= 6 and lower.endswith(("ando", "endo", "indo"))


_ACUTE = {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú"}
_PLAIN = {v: k for k, v in _ACUTE.items()}
_VOWELS = set("aeiouáéíóúàèìòùâêîôûãõüï")


def _syllables(word: str) -> list[str]:
    return syllables(word, "gl") or [word]


def _stress(word: str) -> int:
    """The stressed syllable of a word, counted from the end (0 = the last)."""
    parts = _syllables(word)
    for i, part in enumerate(parts):
        if any(ch.lower() in _PLAIN for ch in part):
            return len(parts) - 1 - i
    if len(parts) == 1:
        return 0
    letters = "".join(ch for ch in word.lower() if ch.isalpha())
    if letters[-1] not in _VOWELS and letters[-1] not in "ns":
        return 0  # falar, papel: stress on the last syllable
    core = letters[:-1] if letters[-1] in "ns" else letters
    # A falling diphthong at the end takes the stress: falei, cantou, partiu.
    if len(core) >= 2 and core[-1] in "iu" and core[-2] in "aeiou":
        return 0
    return 1


def _accent_index(syllable: str) -> int | None:
    """Where the accent of a syllable goes: the open vowel if there is one, else the last."""
    vowels = [i for i, ch in enumerate(syllable) if ch.lower() in _VOWELS]
    if not vowels:
        return None
    for i in vowels:
        if syllable[i].lower() in "aeoáéó":
            return i
    return vowels[-1]


def _set_accent(ch: str, on: bool) -> str:
    lower = ch.lower()
    new = _ACUTE.get(lower, lower) if on else _PLAIN.get(lower, lower)
    return new.upper() if ch.isupper() else new


def _accented_verb(verb: str, pronoun: str) -> str:
    """The verb as it is written with `pronoun` after it (only its accent can change)."""
    parts = _syllables(verb)
    stress = _stress(verb)
    after = stress + len(_syllables(pronoun))
    index = len(parts) - 1 - stress
    offset = sum(len(p) for p in parts[:index])
    target = _accent_index(parts[index])
    if target is None:
        return verb
    position = offset + target
    has_accent = verb[position].lower() in _PLAIN
    if after >= 2:
        on = True  # proparoxytone: always written with an accent
    elif not has_accent:
        on = False
    else:
        # Second to last and ending in a vowel or s: no accent, except one that marks a hiatus
        # (saín) or a one-syllable verb's diacritic (dá).
        hiatus = verb[position].lower() in "íú" and any(
            ch.lower() in _VOWELS
            for ch in verb[max(0, position - 1) : position] + verb[position + 1 : position + 2]
        )
        on = hiatus or len(parts) == 1
    return verb[:position] + _set_accent(verb[position], on) + verb[position + 1 :]


def join_enclitic(verb: str, pronoun: str) -> str:
    return _accented_verb(verb, pronoun) + pronoun


def _joinable(verb: Word, pronoun: Word) -> bool:
    return (
        pronoun.text.lower() in PRONOUNS
        and verb.text[-1:].isalpha()
        and is_verb(verb.text)
        and unicodedata.is_normalized("NFC", verb.text)
    )


def _join(verb: Word, pronoun: Word) -> Word:
    text = _accented_verb(verb.text, pronoun.text)
    verb_parts = verb.parts or [Part(text=verb.text, start=verb.start, end=verb.end)]
    # The accent changes one letter in place: rewrite the part that holds it.
    parts: list[Part] = []
    offset = 0
    for part in verb_parts:
        piece = text[offset : offset + len(part.text)]
        parts.append(part.model_copy(update={"text": piece}))
        offset += len(part.text)
    parts += pronoun.parts or [Part(text=pronoun.text, start=pronoun.start, end=pronoun.end)]
    confidences = [c for c in (verb.confidence, pronoun.confidence) if c is not None]
    return verb.model_copy(
        update={
            "text": text + pronoun.text,
            "end": pronoun.end,
            "parts": parts,
            "confidence": min(confidences) if confidences else None,
        }
    )


def join_clitics(lines: list[Line]) -> list[Line]:
    """Joins Galician enclitic pronouns written apart to their verb, keeping every timing."""
    out = []
    for line in lines:
        words: list[Word] = []
        for word in line.words:
            if words and _joinable(words[-1], word):
                words[-1] = _join(words[-1], word)
            else:
                words.append(word)
        out.append(
            line if len(words) == len(line.words) else line.model_copy(update={"words": words})
        )
    return out
