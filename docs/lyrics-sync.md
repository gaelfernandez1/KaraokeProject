# Lyrics timing (`karaoke_engine.align`)

How the engine places each word of the lyrics at the moment it is sung. The decisions and the
numbers are in [`plan-v3/decisiones/005-sincronia.md`](plan-v3/decisiones/005-sincronia.md) (in
Spanish), and how to measure in [`benchmark.md`](benchmark.md).

## What it does

1. **Reads the lyrics as they are pasted** (`lyrics.parse_lyrics`). First it leaves out what the
   web page added to the copy (`pasted.strip_page_text`), so nobody has to tidy the lyrics by hand:
   - Genius: the "You might also like" block with its three songs, "See … Live / Get tickets as
     low as …", the contributors, translations and "… Lyrics" title at the top, the description
     ending in "Read More" and the trailing "Embed";
   - credits, copyright and links from Musixmatch, Google, Letras, AZLyrics or a video
     description ("Writer(s): …", "Fuente: Musixmatch", "Composição: …", "Prod: …", "© …",
     "Instagram: …", URLs, hashtags), and the song's title and artist written above the lyrics
     (`make` knows them);
   - timings from subtitle and LRC files or video transcripts, and verse numbers alone;
   - stage directions in parentheses ("(risas)", "(spoken)", "(instrumental)"), unless the line
     sings the same word as an echo ("Pon a música (música)").

   A line goes only when no song would sing it: text that could also be sung ("Solo", "Ponte
   guapa", "Letra de amor") is only dropped above or below the lyrics, or not at all. Then the
   song's own structure:
   - headers such as `[Estribillo]` or `[Verso 1: Ana]`: they give the section and who sings;
     labels without brackets count too (`CORO:`, `Verso 2 (Ana):`, `(Estribillo x2)`, `**Verse**`,
     `{Chorus}`, `Repetir estribillo`, `Coro: first line`);
   - who sings a line in a duet (`Ela: …`, `Él: …`, `Os dous: …`), until someone else does;
   - repeats (`x2`, `×3`, `(x2)`, `(bis)`, or `x2` alone on a line to repeat the verse);
   - a chorus that is only named (`[Estribillo]` with nothing under it): the last one with that
     name is repeated, or the last chorus under another of its names (`Repite el coro` after an
     `[Estribillo]`);
   - backing vocals in parentheses: they come out as separate lines, marked as backing.

   The text that is shown does not change — not the gheada, not the seseo, not the punctuation —
   with one exception in Galician: pronouns written apart after their verb are joined to it, as the
   standard asks («dixo lle» → «díxolle», «collín che» → «collinche»; see "Pronouns" below).
2. **Turns each word into what is said** (`spoken.spoken`), only to align: lowercase, no
   punctuation, and numbers and symbols in words in Galician, Spanish, Portuguese and English
   (`2024` → «dous mil vinte e catro»; `&` → «e»).
3. **Computes the CTC emissions** of the separated voice with the language's model
   (`emissions.EmissionModel`). It works in 30 s windows with 2 s of context, and only the columns
   the lyrics use leave the GPU.
4. **Looks at where the voice sounds** (`activity.vocal_activity`): the separated voice's energy
   compared with the song's own singing.
5. **Searches for the best path** (`ctc.align_segments`), with three freedoms classic CTC alignment
   does not have:
   - a **filler** between lines that explains any sound at a cost: ad-libs, backing vocals not in
     the lyrics, leftovers of the instrumental;
   - **skipping a whole line** at a cost: lines the site has and nobody sings;
   - an **extra cost for each letter** where the voice is silent, so the lyrics do not slip into
     the instrumental breaks.
6. **Adjusts the ends**: a word ends where its voice stops (at the first pause longer than 0.3 s),
   with a 0.1 s margin. Moving the starts to the voice's onset too (`refine_onsets`) is available,
   but it makes JamendoLyrics worse and is off.
7. **Syllables** (`syllables.syllables`, Galician, Spanish and Portuguese): each word of two or
   more syllables whose letters each have a token gets `parts`. Each part starts when the CTC places
   its first letter and ends where the next one starts. A word with numbers or letters the model
   does not know is left without parts; the player lights it up whole.

Each word's **confidence** is the geometric mean of the CTC probability of its letters. A word with
no letter the model knows (a number in a language without rules, an emoji) sticks to its neighbour
with confidence 0. Skipped lines do not come out. Backing lines come out with `role: "backing"`
(contract 1.1.0), and those under a header with a singer, with its `singer`.

## Models

The models are downloaded once from Hugging Face to the local cache and pinned to a revision. Each
language's default comes from the benchmark (decision 005).

| Name | Model | Licence | Use |
|---|---|---|---|
| `nos-xlsr-300m-gl` | [proxectonos/Nos_ASR-wav2vec2-xls-r-300m-gl](https://huggingface.co/proxectonos/Nos_ASR-wav2vec2-xls-r-300m-gl) | Apache-2.0 | Galician |
| `nos-w2vbert-gl` | [proxectonos/w2v-bert-2.0-gl](https://huggingface.co/proxectonos/w2v-bert-2.0-gl) | Apache-2.0 | Galician |
| `omni-ctc-300m`, `omni-ctc-1b` | Meta's Omnilingual ASR CTC ([original](https://github.com/facebookresearch/omnilingual-asr), Apache-2.0), in [aadel4](https://huggingface.co/aadel4/omniASR-CTC-1B-v2)'s conversion to `Wav2Vec2ForCTC` | Apache-2.0 | any language (about 1600) |
| `w2v2-large-en` | [facebook/wav2vec2-large-960h-lv60-self](https://huggingface.co/facebook/wav2vec2-large-960h-lv60-self) | Apache-2.0 | English |
| `w2v2-en`, `xlsr-en` | [facebook/wav2vec2-base-960h](https://huggingface.co/facebook/wav2vec2-base-960h), [jonatasgrosman/wav2vec2-large-xlsr-53-english](https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-english) | Apache-2.0 | English (comparison) |
| `xlsr-es`, `xlsr-fr`, `xlsr-de`, `xlsr-pt` | [jonatasgrosman/wav2vec2-large-xlsr-53-*](https://huggingface.co/jonatasgrosman) | Apache-2.0 | Spanish, French, German, Portuguese |
| `ifrz-gl` | [ifrz/wav2vec2-large-xlsr-galician](https://huggingface.co/ifrz/wav2vec2-large-xlsr-galician) | no published licence | only to compare in the benchmark |

## Parameters (`LyricsAligner`)

The defaults come from the sweeps in decision 005: filler 3 per frame, skipping a line 6 per
letter (a backing line, 4), silence 4, no cheap skips at the edges and no moving of the starts. Skips
cost per letter: with a fixed cost per line, the cheapest path pushed many short lines into the
audio instead of the long ones that are really sung.

| Parameter | What it does |
|---|---|
| `model` | a name from the table; without it, the language's (and Omnilingual if the language has none) |
| `filler_penalty` | the cost per frame of explaining a sound with the filler; higher forces the lyrics to cover more |
| `skip_penalty` | the cost per letter of skipping a lead line |
| `backing_skip_penalty` | the cost per letter of skipping a backing line (lower: backing vocals often overlap the voice or cannot be heard) |
| `edge_skip_penalty` | the cost per letter of leaving out lines at the start or end of the lyrics (for clips or short versions); off, because on whole songs it can drop a verse that is sung |
| `silence_penalty` | the extra cost per letter in a stretch without voice |
| `refine_onsets` | move the starts to the voice's onset |
| `parts` | give words syllables with timings (gl, es, pt) |
| `overlap_backing` | give backing lines that do not fit in their place a second pass in which they may overlap the lead voice (off: with the public songs it places more words wrong than right, `decisiones/006`) |
| `char_map` | letters written another way for alignment, for example `{ j = "x" }` for the gheada |

## Making a karaoke

```bash
uv run karaoke make song.m4a --lyrics lyrics.txt --lang gl --out my-karaoke
uv run karaoke make song.m4a --lrclib --title "Title" --artist "Band"    # lyrics from LRCLIB
uv run karaoke make song.m4a                                             # no lyrics: transcribe
uv run karaoke make song.m4a --lyrics lyrics.txt --overlap-backing       # overlapping backing
```

- **With `--lyrics`**: the lyrics as pasted from a website.
- **With `--lrclib`**: looks the lyrics up on [LRCLIB](https://lrclib.net), an open and free lyrics
  database. It only sends the title and the artist, and nothing unless asked. It keeps the entry
  with the closest duration (±5 s); if there is none, it transcribes.
- **Without lyrics**: transcribes the separated voice with Whisper (for Galician, the Galician model
  the benchmark chose), always in the language asked for. It removes the stretches where the voice
  is silent, because Whisper fills silences with stock phrases, and looping repeats. It splits the
  text into lines by sentence and about every nine words, and aligns it like pasted lyrics.

The first transcription in Galician downloads and converts HiTZ's model (about 6 GB). The
conversion needs about 6 GB of free memory for a few minutes: close other programs. It runs in a
separate process, and if it is interrupted it starts over next time.

The package's `provenance` says where the lyrics came from (`user`, `lrclib` or `asr`) and which
models were used. Singers in the headers (`[Verso: Ana]`) go to `singers`, and backing lines carry
`role: "backing"` (contract 1.1.0, `decisiones/006`).

It accepts any audio or video ffmpeg reads. It separates the voice, aligns the lyrics, leaves the
audio levelled in m4a and writes `karaoke.json` last: if something fails half-way, no package is
left that looks good. To listen to it, copy the folder to `bench/data/paquetes/` and open it from
the web app's library (`pnpm --dir web dev`, see [`web.md`](web.md)).

## Measuring

```bash
uv run karaoke-bench run --pipeline bench/pipelines/<pipeline>.toml --set quick --mode lyrics
uv run karaoke-bench run --pipeline bench/pipelines/<pipeline>.toml --set stress --mode lyrics
uv run karaoke-bench compare bench/results/<before> bench/results/<after>
```

## Pronouns joined to the verb (Galician)

Lyrics sites often write the pronoun apart, as in Spanish: «dixo lle», «collín che», «quero te».
In Galician it is attached to the verb before it (enclisis), and the joined word follows the accent
rules: «díxolle», «collinche», «quérote», «darache» (it loses the accent of «dará»), «dálle» (it
keeps the diacritic). `align.clitics.join_clitics` does it after aligning, in `karaoke make` with
`--lang gl`, without touching the timings: the verb and the pronoun become syllables of the new
word.

To avoid mistakes, it only joins:

- pronouns that cannot be anything else (che, lle, lles, cho, llo, me, te, vos…; not «o», «a»,
  «nos» or «se», which are also articles, contractions or conjunctions);
- after a known verb form (frequent conjugated verbs, irregular ones and gerunds), also with
  gheada or seseo («jaño che» → «jáñoche»);
- never after the words that pull the pronoun in front of the next verb: «non che digo», «que che
  quero», «xa che dixen» stay as they are.

For a package already made: `uv run karaoke join-clitics <package>`.
