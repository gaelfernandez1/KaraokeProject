# Documentation

The technical guides of Proxecto Karaoke en Galego. The project's presentation is in the
[README](../README.md) (Galician), also in [English](../README.en.md) and
[Spanish](../README.es.md). The planning documents and design decisions under
[`plan-v3/`](plan-v3/) are written in Spanish.

## Start here

| Guide | What for |
|---|---|
| [Architecture](architecture.md) | the pieces, how they fit and why, with the numbers |
| [Development](development.md) | setting up the environment and the everyday commands |
| [Server](server.md) | starting it, phones at home, away from home, backups and troubleshooting |

## Each part

| Guide | What it covers |
|---|---|
| [Audio](audio.md) | separating the vocals, the package's audio and the browser's audio engine |
| [Lyrics timing](lyrics-sync.md) | how each word and syllable is placed, transcription and the models |
| [Animated lyrics](subtitles.md) | the lyrics layout, the themes and the ASS generator |
| [Video](video.md) | backgrounds and MP4 export |
| [Web app](web.md) | routes, screens, the stand-in server and browser tests |
| [Benchmark](benchmark.md) | measuring an engine change, sets, metrics and adding songs |
| [Languages and models](languages-and-models.md) | what each language gets, adding one and changing a model |

## How the work is done

| Guide | What it covers |
|---|---|
| [Quality](quality.md) | the gates of `make ci` and the CI, and how to audit |
| [Releasing](releasing.md) | versions, changelog, tags and releases |
| [Decisions](plan-v3/decisiones/) | every design decision with what was measured and what was discarded (Spanish) |
| [Plan v3](plan-v3/00-vision.md) and [status](plan-v3/ESTADO.md) | the goal, the principles and how each area stands (Spanish) |

The bachelor's thesis the project grew from is in [`tfg/`](tfg/) (Galician).
