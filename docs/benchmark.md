# Benchmark (`karaoke-bench`)

The benchmark says with numbers whether a change to the engine improves transcription, timing or
speed. It measures any combination of steps (separating the vocals, transcribing, splitting into
lines and aligning) on songs with reference timings, and leaves a comparable report in
`bench/results/`.

## In two minutes

```bash
uv sync --extra ml                                   # baseline models (only on the GPU machine)
uv run karaoke-bench fetch --set jamendo             # 79 public songs (~400 MB, once)
uv run karaoke-bench run --pipeline bench/pipelines/base-turbo.toml --set quick --mode lyrics
uv run karaoke-bench compare bench/results/<before> bench/results/<after>
```

Audio never goes into git: everything downloaded or computed goes to `bench/data/` (ignored).

## Sets

| Set | What it is | What for |
|---|---|---|
| `jamendo` | 79 songs from [JamendoLyrics MultiLang](https://huggingface.co/datasets/jamendolyrics/jamendolyrics) (en, es, fr, de) with the start and end of each word annotated by hand; the properly written lyrics and the line timings come from [Jam-ALT](https://huggingface.co/datasets/jamendolyrics/jam-alt) | full measurements |
| `jamendo-<language>` | those of one language | measuring one language |
| `quick` | 20 fixed songs (5 per language, varied genres), in `bench/sets/quick.txt` | the quick daily check |
| `gl` | Galician songs with free licences and timings checked by ear (`bench/sets/gl/`) | the main goal |
| `stress` | 24 songs from `quick` with the tricks of real songs (a 30 s instrumental, ad-libs, echoes, "lyrics site" text with headers and `x2`, a missing line or two extra ones), with JamendoLyrics' exact timings shifted; the recipe is in `bench/sets/stress.toml` and it is built with `fetch --set stress` | the aligner's robustness, per group |
| `private` | your songs, in `bench/data/private/` | local only |
| `<set>/<id>` | a single song | debugging |

Both public sources are pinned to a revision in `bench/sets/jamendo.toml`. Changing it changes
every number, so it is only done on purpose.

## Modes

- **`lyrics` (with lyrics)**: separator (if any) and aligner with the lyrics a user would paste
  (Jam-ALT's or `lyrics.txt`). It measures timing.
- **`asr` (without lyrics)**: separator, transcriber, segmenter and aligner with the transcribed
  lines and the language the transcriber returns (that is how a silent language switch shows). It
  measures WER, CER, language and the timing of the words that match the reference.
- **`both`**: both, in two reports.

## Pipelines

A pipeline is a TOML file in `bench/pipelines/` that says which class does each step:

```toml
name = "my-test"                       # lowercase letters, digits and hyphens
description = "What changes from the baseline"

[steps.separator]                      # optional: without it the mix is used
target = "karaoke_bench.baseline.separation:DemucsSeparator"

[steps.aligner]
target = "karaoke_bench.baseline.ctc:CtcAligner"
params = { model = "proxectonos/Nos_ASR-wav2vec2-xls-r-300m-gl", revision = "05a9b49…" }
```

Steps: `separator`, `transcriber`, `segmenter` and `aligner`. Any class that implements the
protocols in `karaoke_engine.steps` works. For the benchmark to use it well:

- A class attribute `version` (text): bump it when what it produces changes, because it is part of
  the cache key.
- Nothing heavy at module level: `torch`, `transformers` and the like are imported inside the
  methods, because the benchmark imports the class to read `version`.
- Optional: a `load()` method with no arguments. The benchmark times it apart, as "load".
- Pin the revision of Hugging Face models.
- If the aligner also has `align_text(vocals, lyrics, language)` (the
  `karaoke_engine.steps.TextAligner` protocol), it receives the lyrics as pasted, with headers
  (`[Chorus]`), repeats (`x2`) and backing vocals in parentheses, and it may return a different
  number of lines, for example when it repeats a chorus or skips a line nobody sings. In `asr` mode
  it receives the segmenter's lines joined by line breaks. Other aligners keep receiving the clean
  lines.

Included pipelines:

| Pipeline | What it is |
|---|---|
| `smoke` | fake steps, no models; the aligner spreads the words evenly (the "dummy" to beat) |
| `base-legacy` | the v2 system with current libraries: Demucs, Whisper `small` guessing the language and the default CTC aligner |
| `base-turbo` | Demucs, Whisper `large-v3-turbo` with the chosen language and the default CTC aligner |
| `draft-gl` | Demucs and the aligner with Proxecto Nós' model; it drafts the Galician references |

## How a run works

Each step runs for every song in **its own process**: it loads the model once, leaves the GPU
clean when it ends and its memory is measured on its own. Each step's result is cached
(`bench/data/cache/`) with a key made of class, parameters, version and input, so trying another
aligner does not repeat the separation. `--no-cache` computes everything again.

If a step fails on a song (an exception, running out of memory or a dead process), that song comes
out with its error and the others go on: if the process dies, it is restarted for the remaining
ones (up to 3 times). An aligner that returns a different number of lines or timings outside the
song is marked as an error too. Each finished song enters the cache right away, so an interrupted
run (`Ctrl`+`C`, a power cut) picks up where it was when started again.

Each run leaves:

- `bench/results/<date>-<pipeline>-<set>-<mode>/report.md`: the report (versioned). Those of the
  `private` set go to `bench/data/results/`, which is not versioned: they are your songs;
- `.../results.json`: every number, the environment, the commit and the normalisation version
  (versioned);
- `bench/data/runs/<same name>/<song>.json`: the full outputs (not versioned).

The reports themselves are written in Spanish.

## Metrics

- **WER and CER** (only in `asr`): on the normalised lyrics, weighted by words or characters in
  each group. The normalisation (its version in `textnorm.NORMALIZATION_VERSION`) lowercases,
  unifies apostrophes, removes tags like `[Chorus]`, repeat marks (`x2`, `bis`) and punctuation,
  and splits on hyphens (`vou-te` → `vou te`). **Accents count**: in Galician `é` and `e` are
  different words. What goes in parentheses (backing vocals) stays, because it is sung. Numbers are
  not spelled out: the references are written in words.
- **Word timing**: the output's words are paired with the reference's (a Levenshtein alignment
  ignoring accents) and only those that match count:
  - absolute start error (median, mean and % ≤ 0.3 s);
  - absolute end error (median);
  - **bias**: the signed mean (positive = the lyrics come late);
  - **coverage**: % of the reference's words that were paired.

  They are equivalent to the AAE and PCO of the JamendoLyrics papers.
- **Line timing** (only in `lyrics`): the median start error of the lines, against Jam-ALT or the
  Galician reference.
- **Language**: the language asked for against the one the transcriber returns. Any difference
  counts as a language switch.
- **Speed**: seconds per step and song, real-time factor (seconds ÷ duration) and an estimate for a
  4-minute song (the sum of the medians × 240 s plus the loads).
- **Memory**: each step's peak VRAM with NVML, minus what was already in use at the start (Windows
  uses ~1 GB). If the step uses torch, also its own peak. The process's peak RAM.

## Comparing

```bash
uv run karaoke-bench compare bench/results/A bench/results/B [--out comparison.md]
```

A table per language with A, B and the difference, and the list of songs that got worse (+0.05 s
of median start error or +5 WER points). It warns when the normalisation, the set or the mode
changed.

## Galician references

There are no published timings for songs in Galician, so they are made like this:

1. **Draft**: `uv run karaoke-bench draft gl/<id> --pipeline bench/pipelines/draft-gl.toml`. It
   uses a model no baseline pipeline uses, so the baseline is not scored against itself.
2. **Review by ear**: `uv run karaoke-bench review gl/<id> --pipeline bench/pipelines/draft-gl.toml`
   and open <http://localhost:8765> in the browser (also from Windows). The page plays the song
   lighting up each word, with the voice's waveform below. Keys:

   | Key | What it does |
   |---|---|
   | `Space` | play or stop |
   | click on a line | listen to it from 1 s before |
   | `1` / `2` / `3` | the line is right / wrong (asks for a note) / unsure |
   | `A` | "the line starts here" (sets an anchor at the point that is playing) |
   | click on a word, `←`/`→` | move its start ±0.05 s (with `Shift`, its end) |
   | double click on the text | correct the line's lyrics |
   | `V` | speed 0.75× |
   | `M` | listen to the mix or the voice alone |
   | `Ctrl`+`S` | save |

3. **Realign**: `uv run karaoke-bench realign gl/<id> --pipeline bench/pipelines/draft-gl.toml`
   aligns again only the lines marked wrong, inside the gap their good neighbours or the anchors
   leave. Those lines are left as "to review" to listen to them again.
4. When nothing is left unreviewed or wrong, the **Song validated** button accepts it.

**Without listening to everything**: `uv run karaoke-bench triangulate gl/<id> --pipelines a.toml
b.toml c.toml` aligns the lyrics with several independent aligners (different models). Draft lines
where all of them place every word within 0.15 s of the median become "right", with the median
timings and an `auto: …` note. The rest become "unsure" and the command lists them: they are the
only ones that need listening to on the review page. If ≥ 70 % of the words end up right, the song
counts as validated. Lines already reviewed by ear are left alone. Beware: scoring one of those
aligners against that reference later favours it a little; better use aligners other than the one
being measured.

Only lines marked "right" count for timing, and only when the song is validated: until then the
report marks it "not validated" and it stays out of the timing figures. The text corrected on the
page is the one used for the WER and the one the aligner receives. A reference checked by ear is
reliable to about ±0.1 s, so in `gl` the % ≤ 0.3 s matters more than the median. `draft` does not
overwrite a reference with reviewed lines unless given `--force`.

## Adding songs

**Public ones in Galician** (or another language, in a set with a manifest):

1. Find a song with a CC licence (BY or BY-SA is best) and a stable direct download URL (the
   Internet Archive works well).
2. Add it to `bench/sets/gl/manifest.toml` with `id`, `title`, `artist`, `language`, `style`,
   `license`, `license_url`, `source`, `audio_url` and `sha256` (from `sha256sum`). If the song is
   part of a longer recording (a whole concert), add `clip = [start, end]` in seconds: the recording
   is downloaded, checked, and only that part is kept, without loss.
3. Create `bench/sets/gl/<id>/lyrics.txt` with the lyrics as they are shown and a `LICENSE` with
   author, work, licence and source.
4. `uv run karaoke-bench fetch --set gl`, then `draft`, `review` and `realign` as above.

**Private ones** (they never leave your machine): create `bench/data/private/<id>/` with:

- `audio.<ext>` (any format ffmpeg reads);
- `meta.toml` with `title = "…"`, `artist = "…"` and `language = "gl"`;
- `lyrics.txt` if you have the lyrics;
- `reference.json` if you have the timings. A `karaoke.json` corrected by hand also works: it is
  converted with `karaoke_bench.reference.reference_from_doc`.

If you have the timings in a hand-made word-by-word `.srt` subtitle (one entry per word; an entry
may hold two words or a word may be split into syllables), first create `lyrics.txt` with the
song's lines and convert it:

```bash
uv run karaoke-bench import-srt private/<id> my-timings.srt
```

The reference is marked **approximate**: a hand-made subtitle is reliable to a few tenths of a
second, so for those songs the report also gives the % of words within 0.5 s.

Without a reference, the benchmark only measures speed, memory and language. With `draft` and
`review` you can make one, as for the Galician set.

## Reference format (`reference.json`)

```json
{
  "song_id": "…", "language": "gl", "duration": 215.3,
  "timing": "manual | semiautomatic | approximate", "approved": true,
  "lines": [
    { "text": "Vou-te ver, d'aquí", "start": 12.3, "end": 15.8,
      "status": "draft | ok | wrong | unsure", "anchor": null, "note": null, "revised": false,
      "words": [ { "text": "Vou-te", "start": 12.3, "end": 12.7 } ] }
  ]
}
```

`text` is the line as it is shown. The words may be written another way (in JamendoLyrics they are
lowercase and without accents): they are paired ignoring accents.

## Example packages with real songs

`uv run karaoke-bench package jamendo/<id> --pipeline bench/pipelines/base-turbo.toml --out fixtures/packages/<slug>`
makes a karaoke package with Jam-ALT's lyrics and JamendoLyrics' manual timings. Only
`karaoke.json` and `LICENSE` are versioned; the audio is made locally with that same command.

## Benchmark noise

Running again without the cache gives almost the same numbers, but not identical ones (the GPU is
not fully deterministic). The measured variation is in the «Ruido» section of
[`plan-v3/decisiones/003-banco-y-metas.md`](plan-v3/decisiones/003-banco-y-metas.md): a difference
smaller than that noise is not an improvement.
