"""CTC forced alignment in NumPy: which frames each lyric character occupies.

torchaudio dropped `forced_align` in 2.9, and the classic Viterbi over a CTC trellis is short
enough to own. States are blank, t1, blank, t2, ..., blank; a path moves to the same state, the
next one, or skips a blank when the two tokens around it differ.
"""

import itertools
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

LogProbs = npt.NDArray[np.floating]

_STAY, _NEXT, _SKIP = 0, 1, 2


@dataclass(frozen=True)
class Vocab:
    ids: dict[str, int]
    blank: int
    delimiter: str | None
    upper: bool


def vocab_from_json(mapping: dict[str, int], blank_token: str, delimiter: str | None) -> Vocab:
    letters = [token for token in mapping if len(token) == 1]
    return Vocab(
        ids=dict(mapping),
        blank=mapping[blank_token],
        delimiter=delimiter if delimiter in mapping else None,
        upper=not any(token.islower() for token in letters),
    )


def encode_words(words: Sequence[str], vocab: Vocab) -> tuple[list[int], list[int]]:
    """Token ids for the words, and the word index of each token (-1 for delimiters).

    Characters missing from the vocabulary fall back to their base letter (ç → c), or are
    dropped. A word with no tokens left (pure punctuation) contributes nothing.
    """
    ids: list[int] = []
    owner: list[int] = []
    for index, word in enumerate(words):
        tokens = [t for t in (_token(ch, vocab) for ch in word) if t is not None]
        if not tokens:
            continue
        if ids and vocab.delimiter is not None:
            ids.append(vocab.ids[vocab.delimiter])
            owner.append(-1)
        ids += tokens
        owner += [index] * len(tokens)
    return ids, owner


def forced_align(log_probs: LogProbs, tokens: Sequence[int], blank: int) -> list[tuple[int, int]]:
    """First and last frame (inclusive) of each token on the best CTC path."""
    frames, n = log_probs.shape[0], len(tokens)
    if n == 0:
        return []
    repeats = sum(1 for a, b in itertools.pairwise(tokens) if a == b)
    if frames < n + repeats:
        raise ValueError(f"audio too short for lyrics ({frames} frames for {n} tokens)")

    size = 2 * n + 1
    states = np.full(size, blank, dtype=np.int64)
    states[1::2] = tokens
    can_skip = np.zeros(size, dtype=bool)
    can_skip[3::2] = states[3::2] != states[1:-2:2]
    emit = log_probs[:, states].astype(np.float64)

    score = np.full(size, -np.inf)
    score[:2] = emit[0, :2]
    back = np.zeros((frames, size), dtype=np.int8)
    columns = np.arange(size)
    candidates = np.full((3, size), -np.inf)
    for t in range(1, frames):
        candidates[_STAY] = score
        candidates[_NEXT, 1:] = score[:-1]
        candidates[_SKIP, 2:] = np.where(can_skip[2:], score[:-2], -np.inf)
        choice = candidates.argmax(axis=0)
        score = candidates[choice, columns] + emit[t]
        back[t] = choice

    state = size - 1 if score[-1] >= score[-2] else size - 2
    path = np.empty(frames, dtype=np.int64)
    for t in range(frames - 1, -1, -1):
        path[t] = state
        state -= int(back[t, state])

    on_token = np.flatnonzero(path % 2 == 1)
    token_of = path[on_token] // 2
    first = np.full(n, frames, dtype=np.int64)
    last = np.full(n, -1, dtype=np.int64)
    np.minimum.at(first, token_of, on_token)
    np.maximum.at(last, token_of, on_token)
    return [(int(a), int(b)) for a, b in zip(first, last, strict=True)]


def word_spans(
    spans: Sequence[tuple[int, int]], token_word: Sequence[int], n_words: int
) -> list[tuple[int, int] | None]:
    """Frame span of each word from its tokens; None for words that had no tokens."""
    result: list[tuple[int, int] | None] = [None] * n_words
    for (first, last), word in zip(spans, token_word, strict=True):
        if word < 0:
            continue
        current = result[word]
        result[word] = (first, last) if current is None else (current[0], last)
    return result


def _token(ch: str, vocab: Vocab) -> int | None:
    cased = ch.upper() if vocab.upper else ch.lower()
    if cased in vocab.ids:
        return vocab.ids[cased]
    base = "".join(c for c in unicodedata.normalize("NFD", cased) if not unicodedata.combining(c))
    return vocab.ids.get(base) if len(base) == 1 else None
