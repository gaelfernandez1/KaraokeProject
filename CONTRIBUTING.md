# Contributing to Proxecto Karaoke en Galego

Thanks for your interest. The project is maintained by one person, so the best way to help is a clear
report or a small, focused pull request. For anything larger than a fix, open an issue first so we
can agree on the approach before you spend time on it.

- **Bugs and ideas**: use the [issue forms](https://github.com/gaelfernandez1/KaraokeProject/issues/new/choose).
- **Security problems**: privately, as described in [`SECURITY.md`](SECURITY.md).
- Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md).
- **Never attach or commit songs you have no rights to share.** The test songs are Creative
  Commons and are downloaded by a script; your own songs stay in ignored folders (`bench/data/`,
  `input/`).

## Setting up

You need Linux or Windows with WSL 2 (Ubuntu), Node 22 or newer and ffmpeg with libass. Making
karaokes needs an NVIDIA GPU from the RTX 20 series on (4 GB of video memory is enough); the tests,
the server and the web app run without one.

```bash
make install    # the engine, the server, the web app and the models
make setup      # plus the git hooks and the quality tools
make ci         # every check the CI runs
```

The development guide is [`docs/development.md`](docs/development.md); every technical guide is
listed in [`docs/README.md`](docs/README.md), and the overview is
[`docs/architecture.md`](docs/architecture.md). The planning documents and design decisions in
`docs/plan-v3/` are in Spanish.

## How the code is written

- **Languages**: code, comments, logs and commit messages in English. The interface is in
  Galician (the default), Spanish and English: every new string goes in all three
  (`web/src/lib/i18n/`).
- **Tests first.** A change in behaviour starts with a test that fails. A test that needs ffmpeg
  asks for the `ffmpeg` fixture; one that loads real models is marked `@pytest.mark.models` and
  runs with `make test-models`. In CI any other skipped test is a failure
  ([`docs/quality.md`](docs/quality.md)).
- **Measure the engine.** Anything that can change transcription, timing, speed or memory is
  measured with the benchmark before and after ([`docs/benchmark.md`](docs/benchmark.md)), and the
  report goes in `bench/results/`. "It sounds better" is a hypothesis, not a result.
- **Contracts.** `karaoke.json`, `theme.json` and the API are shared by the engine, the server and
  the web app. Changing one needs a short decision in `docs/plan-v3/decisiones/`, a schema
  version and `make contracts` (the generated schemas and types are committed).
- **Boundaries.** Contracts → engine → bench and server, never upwards, and the server process
  never imports torch or the models (`make lint` checks it).
- **Lyrics layout** exists twice, in Python and TypeScript, with shared cases: change both and
  regenerate the cases (`python -m karaoke_engine.subtitles.conformance --write`).
- **Licences.** New dependencies and models must have a permissive licence (MIT, BSD, Apache…);
  `make lint` checks every installed package. Models are pinned to a revision. See
  [`NOTICE.md`](NOTICE.md) and [`docs/languages-and-models.md`](docs/languages-and-models.md).

## Pull requests

1. Branch from `main` and keep one topic per pull request.
2. `make ci` passes locally; for the web app, also `pnpm --dir web test:e2e`, with screenshots at
   phone, laptop and TV sizes if something looks different (`node web/dev/shots.mjs`).
3. Add what changes for users under `## [Unreleased]` in [`CHANGELOG.md`](CHANGELOG.md).
4. Commit messages: an imperative subject of 50–72 characters ("Align repeated choruses
   separately") and a body of one to three short paragraphs that explains why.

The CI must be green before merging; `main` is protected and always passes.

## Licence

By contributing, you agree that your contribution is released under the project's
[MIT licence](LICENSE).
