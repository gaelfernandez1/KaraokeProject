# Third-party notices

The project's own code is released under the [MIT licence](LICENSE). It works with models, libraries,
fonts and songs made by others, each under its own licence. This file lists the ones that matter;
the full list of Python packages is checked on every change by
[`scripts/licenses.py`](scripts/licenses.py) (see [`docs/quality.md`](docs/quality.md)).

What the repository **contains** from third parties: the fonts, the example lyrics with their
timings, and the images in `docs/assets/`. Models, libraries and audio are **downloaded** on the
user's machine and never redistributed here.

## Models

Downloaded from Hugging Face the first time they are needed (`karaoke-server prepare` does it in
advance), each pinned to a revision in the code: separation in
[`make.py`](packages/engine/src/karaoke_engine/make.py), transcription in
[`transcribe.py`](packages/engine/src/karaoke_engine/transcribe.py) and alignment in
[`align/models.py`](packages/engine/src/karaoke_engine/align/models.py).

| Step | Model | Authors | Licence |
|---|---|---|---|
| Vocal separation | Mel-Band RoFormer vocals (`vocals_mel_band_roformer.ckpt`, through audio-separator) | Kimberley Jensen | MIT |
| Transcription, Galician | [`HiTZ/whisper-large-v3-gl`](https://huggingface.co/HiTZ/whisper-large-v3-gl) | HiTZ Center, University of the Basque Country | Apache-2.0 |
| Transcription, other languages | Whisper large-v3-turbo ([CTranslate2 conversion](https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo)) | OpenAI | MIT |
| Voice activity detection | Silero VAD (bundled with faster-whisper) | Silero Team | MIT |
| Alignment, Galician | [`proxectonos/Nos_ASR-wav2vec2-xls-r-300m-gl`](https://huggingface.co/proxectonos/Nos_ASR-wav2vec2-xls-r-300m-gl) | Proxecto Nós | Apache-2.0 |
| Alignment, English | [`facebook/wav2vec2-large-960h-lv60-self`](https://huggingface.co/facebook/wav2vec2-large-960h-lv60-self) | Meta | Apache-2.0 |
| Alignment, Spanish, French, German, Portuguese | `jonatasgrosman/wav2vec2-large-xlsr-53-*` | Jonatas Grosman | Apache-2.0 |
| Alignment, any other language | Omnilingual ASR CTC 300M ([conversion](https://huggingface.co/aadel4/omniASR-CTC-300M-v2)) | Meta | Apache-2.0 |

Used only by the benchmark, to compare: Demucs (MIT), `proxectonos/whisper-large-v3-turbo-gl-v1.0`
and `proxectonos/w2v-bert-2.0-gl` (Apache-2.0), `BSC-LT/whisper-large-v3-LoS` (Apache-2.0),
Omnilingual CTC 1B (Apache-2.0), `facebook/wav2vec2-base-960h` (Apache-2.0) and
`ifrz/wav2vec2-large-xlsr-galician`, which states no licence and is therefore never a default.

## Libraries

Installed by uv and pnpm from PyPI and npm. The main ones:

| Library | Licence | Used for |
|---|---|---|
| PyTorch, torchaudio | BSD-3-Clause | running the models |
| Transformers, Hugging Face Hub | Apache-2.0 | the alignment models and downloads |
| faster-whisper, CTranslate2 | MIT | transcription |
| audio-separator | MIT | vocal separation |
| NumPy, SciPy, librosa | BSD-3-Clause, BSD-3-Clause, ISC | audio |
| pydantic | MIT | the `karaoke.json` and `theme.json` contracts |
| FastAPI, Starlette, Uvicorn | MIT, BSD-3-Clause, BSD-3-Clause | the server |
| NVIDIA CUDA libraries (`nvidia-*`) | NVIDIA's proprietary licence | the GPU runtime |
| Svelte, SvelteKit, Vite | MIT | the web app |
| [signalsmith-stretch](https://github.com/Signalsmith-Audio/signalsmith-stretch) | MIT | changing the pitch in the browser |
| [lean-qr](https://github.com/davidje13/lean-qr) | MIT | the party QR code |

audio-separator asks for `diffq`, which is licensed for non-commercial use only (CC BY-NC 4.0),
for its Demucs models alone. The engine never uses those models, so `pyproject.toml` leaves `diffq`
out of the installation on Linux and WSL, the systems it supports. On native Windows, which it
does not support, audio-separator would install its Windows build, `diffq-fixed`, under the same
licence.

Two programs are used but not installed as dependencies:

- **ffmpeg**, from the system (`apt install ffmpeg`), for decoding, subtitles (libass) and video
  encoding. Its licence (LGPL or GPL) depends on how the system built it; the engine runs it as a
  separate program and does not distribute it.
- **yt-dlp** (Unlicense), run at its latest release through `uvx` when a song comes from a link.

## Fonts

All under the [SIL Open Font License 1.1](https://openfontlicense.org/); each licence file sits
next to its font.

| Font | Copyright | Where |
|---|---|---|
| Unbounded | The Unbounded Project Authors | the app's menu, titles and names |
| Figtree | The Figtree Project Authors | the app's text |
| Martian Mono | The Martian Mono Project Authors (Evil Martians) | the app's times, counts and the party's room code |
| Atkinson Hyperlegible Next | The Atkinson Hyperlegible Next Project Authors (Braille Institute) | the `contraste` lyrics theme |
| Nunito | The Nunito Project Authors | the `clasico` lyrics theme |
| Inter | The Inter Project Authors | the `moderno` lyrics theme |

## Map data

The night globe of the app (`web/src/lib/globe/`, built by `scripts/galicia_map.py`):

| Data | Source | Licence |
|---|---|---|
| The lights of Galicia: people per 400 m hexagon, 2023 | [Kontur Population](https://data.humdata.org/dataset/kontur-population-spain) (Kontur, via HDX) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| The boundary of Galicia and its four provinces at 1:10m | [Natural Earth](https://www.naturalearthdata.com/) | public domain |
| The relief and the coast | [Mapzen Terrain Tiles](https://registry.opendata.aws/terrain-tiles/) on AWS Open Data: SRTM (NASA, public domain), EU-DEM (produced using Copernicus data and information funded by the European Union) and ETOPO1 (NOAA, public domain) | free to use with this credit |
| The lighthouses of the coast: position, rhythm and range | [Wikidata](https://www.wikidata.org/) | [CC0](https://creativecommons.org/publicdomain/zero/1.0/) |

## Songs, lyrics and benchmark data

The audio is never in the repository: it is downloaded by `karaoke-bench fetch` from the source
each song names. The lyrics belong to each song and share its licence.

| Song | Artist | Licence | Used in |
|---|---|---|---|
| laverca | Clo Plas | CC BY-SA 4.0 | the demo (`fixtures/packages/cloplas-laverca`, images in `docs/assets/`) and the Galician benchmark |
| Feel (Stripped) | Cortez | CC BY | example package |
| Mère nature | LAW' | CC BY-SA | example package |
| Esencia | NANDOMALO | CC BY-SA | example package |
| un aire · O mundo do motor · Lene | Pantis · Cibrán · Fanny + Alexander | CC BY-NC-SA | Galician benchmark |
| Chapapote | Mortos En Vida | CC BY-NC-ND 3.0 | Galician benchmark only (no derivatives are made) |

Each song's folder has a `LICENSE` with its source and credits (`bench/sets/gl/*/`,
`fixtures/packages/*/`). The 79 public benchmark songs and their word timings come from
**JamendoLyrics MultiLang** (Durand, Stoller and Ewert, ICASSP 2023; MIT) with the revised lyrics
of **Jam-ALT** (Cífka et al., 2023 and 2025); every song keeps its own Creative Commons licence.

The screenshots and the animation in `docs/assets/` show these songs and are shared under
CC BY-SA 4.0, like "laverca".
