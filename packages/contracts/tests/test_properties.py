"""Properties of the contracts over generated inputs, not only the examples written by hand."""

import json
import math
import tempfile
from pathlib import Path
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from karaoke_contracts import KaraokeDoc, dump_doc, load_doc, validate_doc, validate_file

DEMO = Path(__file__).resolve().parents[3] / "fixtures/packages/demo-sintetico/karaoke.json"
BASE: dict[str, Any] = json.loads(DEMO.read_text(encoding="utf-8"))

json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False) | st.text(),
    lambda children: (
        st.lists(children, max_size=4) | st.dictionaries(st.text(max_size=8), children, max_size=4)
    ),
    max_leaves=25,
)


@settings(max_examples=150, deadline=None)
@given(
    replace=st.dictionaries(
        st.sampled_from(["lines", "duration", "audio", "singers", "schema_version", "language"]),
        json_values,
        max_size=3,
    )
)
def test_validating_any_json_answers_with_issues_not_exceptions(replace: dict[str, Any]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "karaoke.json"
        path.write_text(json.dumps({**BASE, **replace}), encoding="utf-8")
        issues = validate_file(path)
    assert isinstance(issues, list)


# Text a lyrics site or an editor can hand us: accents, combining marks, emoji, RTL, quotes.
lyric_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc")), min_size=1, max_size=12
).filter(lambda text: text.strip() != "")


@settings(max_examples=100, deadline=None)
@given(texts=st.lists(lyric_text, min_size=1, max_size=4), shift=st.floats(-0.5, 0.5))
def test_saving_and_loading_keeps_every_word_and_time(texts: list[str], shift: float) -> None:
    data = json.loads(json.dumps(BASE))
    words = data["lines"][0]["words"]
    for word, text in zip(words, texts, strict=False):
        word["text"] = text
        word["parts"] = []
    data["lines"][0]["start"] = max(0.0, data["lines"][0]["start"] + shift)
    doc = KaraokeDoc.model_validate(data)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "karaoke.json"
        dump_doc(doc, path)
        again = load_doc(path)
    assert again == doc
    # Checking it is total too: problems are listed, never raised.
    assert all(math.isfinite(line.start) for line in again.lines)
    assert isinstance(validate_doc(again), list)
