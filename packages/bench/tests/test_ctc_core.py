import os
import time

import numpy as np
import numpy.typing as npt
import pytest

from karaoke_bench.baseline.ctc_core import encode_words, forced_align, vocab_from_json, word_spans


def peaked(path: list[int], vocab_size: int) -> npt.NDArray[np.float32]:
    """Log-probs where each frame strongly prefers the token given for it."""
    probs = np.full((len(path), vocab_size), 0.02 / (vocab_size - 1), dtype=np.float32)
    probs[np.arange(len(path)), path] = 0.98
    return np.log(probs)


def test_encode_words_folds_missing_letters() -> None:
    vocab = vocab_from_json(
        {"<pad>": 0, "|": 1, "o": 2, "l": 3, "a": 4, "á": 5, "c": 6},
        blank_token="<pad>",
        delimiter="|",
    )

    ids, owner = encode_words(["Olá", "ç!"], vocab)

    assert ids == [2, 3, 5, 1, 6]
    assert owner == [0, 0, 0, -1, 1]


def test_encode_words_uppercase_vocab_and_empty_words() -> None:
    vocab = vocab_from_json(
        {"<pad>": 0, "|": 1, "O": 2, "L": 3, "A": 4}, blank_token="<pad>", delimiter="|"
    )

    ids, owner = encode_words(["ola", "—", "la"], vocab)

    assert vocab.upper
    assert ids == [2, 3, 4, 1, 3, 4]
    assert owner == [0, 0, 0, -1, 2, 2]


def test_encode_words_space_delimiter() -> None:
    vocab = vocab_from_json({"[PAD]": 0, " ": 1, "a": 2}, blank_token="[PAD]", delimiter=" ")

    assert encode_words(["a", "a"], vocab) == ([2, 1, 2], [0, -1, 1])


def test_forced_align_recovers_peaked_path() -> None:
    log_probs = peaked([0, 0, 1, 1, 0, 0, 2, 2, 2, 0], vocab_size=3)

    assert forced_align(log_probs, [1, 2], blank=0) == [(2, 3), (6, 8)]


def test_forced_align_repeated_token_needs_blank() -> None:
    log_probs = peaked([0, 1, 1, 0, 1, 1, 0], vocab_size=2)

    assert forced_align(log_probs, [1, 1], blank=0) == [(1, 2), (4, 5)]


def test_forced_align_too_short() -> None:
    with pytest.raises(ValueError, match="too short"):
        forced_align(peaked([1, 1], vocab_size=2), [1, 1, 1], blank=0)


def test_word_spans_skip_delimiters() -> None:
    assert word_spans([(2, 3), (4, 4), (6, 8)], [0, -1, 1], 2) == [(2, 3), (6, 8)]


def test_word_spans_mark_words_without_tokens() -> None:
    assert word_spans([(1, 2), (5, 6)], [0, 2], 3) == [(1, 2), None, (5, 6)]


@pytest.mark.skipif(os.environ.get("CI") == "true", reason="timing check, local only")
def test_forced_align_is_fast_enough() -> None:
    rng = np.random.default_rng(0)
    log_probs = np.log(rng.dirichlet(np.ones(40), size=12_000).astype(np.float32))
    tokens = list(rng.integers(1, 40, size=1_500))

    started = time.perf_counter()
    forced_align(log_probs, tokens, blank=0)

    assert time.perf_counter() - started < 5.0
