# Languages and models

Proxecto Karaoke en Galego is built for Galician first, and it works with songs in any language.
This guide says what each language gets, how to add one and how to change a model. The rule is
always the same: a new model comes in **measured with the benchmark** ([`benchmark.md`](benchmark.md)),
with a **permissive licence** and **pinned to a revision**.

## What each language gets

| Piece | Languages | Where |
|---|---|---|
| Alignment with a dedicated model | Galician, Spanish, Portuguese, English, French, German | `align/models.py` (`DEFAULT_BY_LANGUAGE`) |
| Alignment with a multilingual model (Omnilingual, about 1,600 languages) | every other language | `align/models.py` (`FALLBACK_MODEL`) |
| Transcription without lyrics | Whisper's (about 100); for Galician, a model of its own | `transcribe.py` (`DEFAULT_BY_LANGUAGE`) |
| Numbers and symbols spoken as words | Galician, Spanish, Portuguese, English | `align/numbers.py`, `align/spoken.py` |
| Timed syllables | Galician, Spanish, Portuguese | `align/syllables.py` |
| Enclitic pronouns joined to the verb | Galician | `align/clitics.py` |
| The list when creating a karaoke | 23, Galician first | `web/src/lib/create/languages.ts` |
| The app's interface | Galician (default), Spanish, English | `web/src/lib/i18n/` |

The engine's paths are under `packages/engine/src/karaoke_engine/`. A language without a dedicated
model works all the same, with the multilingual one: if the benchmark says it does worse than a
dedicated model, it gets one.

## Adding a language to the list

1. Add it to `LANGUAGES` in `web/src/lib/create/languages.ts`: the ISO 639-1 code and its name in
   its own language.
2. If it is often written with three letters (ISO 639-2), add the mapping to `TWO_LETTERS` in
   `languages.py`, so that "glg" does not lose everything Galician.

With that it is aligned with Omnilingual and transcribed with Whisper large-v3-turbo.

## Giving it its own aligner

1. **Find a CTC model** for the language on Hugging Face (wav2vec2, XLS-R, w2v-BERT…) with a
   permissive licence and a vocabulary of letters (not phonemes).
2. **Register it** in `MODELS` in `align/models.py` as `CtcModelSpec(repo, revision, licence,
   fallbacks)`: the revision is the commit of the model's repository, and `fallbacks` maps letters
   the model never saw to the closest one (in Galician, `ç` → `z`).
3. **Measure it**: you need a set with reference timings in that language
   ([`benchmark.md`](benchmark.md), "Adding songs"). Create a pipeline in `bench/pipelines/` that
   uses the model and compare it with the multilingual one:
   ```bash
   uv run karaoke-bench run --pipeline bench/pipelines/<new>.toml --set <set>
   uv run karaoke-bench compare bench/results/<multilingual> bench/results/<new>
   ```
4. **If it wins**, put it in `DEFAULT_BY_LANGUAGE`, bump `version` in `LyricsAligner` (the
   benchmark's cache depends on it), add it to [`NOTICE.md`](../NOTICE.md) and leave the report in
   `bench/results/`.

## Changing a language's transcriber

The Whisper models are in `MODELS` in `transcribe.py` (`WhisperSpec(repo, revision, licence,
converted)`). faster-whisper uses CTranslate2: a Transformers model is converted once, in a separate
process because the conversion needs a lot of RAM (`converted=False` does it on its own). The WER is
measured with the language's set without lyrics (`--mode asr` in the benchmark), and the new default
goes in `DEFAULT_BY_LANGUAGE`, bumping `version` in `WhisperTranscriber`.

## Numbers, syllables and pronouns

They are the language's rules, with their tests in `packages/engine/tests/`:

- **Numbers** (`numbers.py`): how each figure is said («2024» → «dous mil vinte e catro»).
- **Syllables** (`syllables.py`): how a word is split when sung. A word without syllables lights up
  whole, so it is not required.
- **Pronouns** (`clitics.py`, Galician only): what is joined and what is not («dixo lle» →
  «díxolle», but not «en cada soño te vexo»).

## The interface in another language

1. Copy `web/src/lib/i18n/gl.ts` to `<code>.ts` and translate it: the `Messages` type makes every
   key required.
2. Add it to the `Locale` type (`web/src/lib/i18n/plural.ts`, with its plural rule) and to
   `LOCALES`, `LOCALE_NAMES` and `DICTIONARIES` in `web/src/lib/i18n/index.svelte.ts`.
3. `pnpm --dir web test` and screenshots on a phone, a laptop and a TV (`node web/dev/shots.mjs`):
   longer texts must not break the layout.

## Another separation model

audio-separator has a catalogue of models (RoFormer, MDX, Demucs…). To try one, copy
`bench/pipelines/sep-melkim-8s.toml`, change `model` and measure it with lyrics on `quick` and `gl`:
separation is judged by how well the result aligns afterwards, by time and by VRAM (3 GB at most).
If it wins, change `default_separator()` in `make.py` ([`audio.md`](audio.md)).

## Licences

- Only models and libraries with a permissive licence (MIT, BSD, Apache…). A model without a
  published licence may be in the benchmark for comparison, never as a default.
- `make lint` checks the licence of every installed package (`scripts/licenses.py`); on the GPU
  machine, also the models' libraries.
- [`NOTICE.md`](../NOTICE.md) lists the default models with their licences.
- `uv run karaoke-server prepare --lang <code>` downloads everything a language needs in advance, so
  the first song starts right away.
