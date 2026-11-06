# Code quality

What each gate checks, how to pass it and how to audit the project in depth. The decision with the
reasons and what the audit found is
[`plan-v3/decisiones/012-calidad.md`](plan-v3/decisiones/012-calidad.md) (in Spanish).

## The gates (`make ci` locally, and the CI on GitHub)

| Gate | What it prevents | Command |
|---|---|---|
| ruff (format and lint) | besides style: blocking the server's event loop (`ASYNC`), security (`S`), swallowed errors (`BLE`), naive datetimes (`DTZ`), prints outside the CLIs (`T20`) | `make lint` |
| deptry | a package using something it does not declare (it would work by chance, because another package brings it) | `make lint` |
| import-linter | contracts → engine → bench and server, with no upward imports; and **the server process never loads torch or the models** (only each job's process does) | `make lint` |
| shellcheck | the usual bash mistakes in the scripts (a `cd` that fails, quoting, pipelines) | `make lint` |
| GitHub files and citation | workflows, Dependabot, issue forms and `CITATION.cff` that GitHub would reject | `make lint` (check-jsonschema with its bundled schemas) |
| Versions | a package, the web app or `CITATION.cff` stating another version, or a missing `CHANGELOG.md` entry | `make lint` (`scripts/release.py check`; guide in [`releasing.md`](releasing.md)) |
| Licences | a dependency with a licence that is not accepted (non-commercial, GPL, none…); in CI without the GPU part, locally with `--extra ml` the models' libraries too | `make lint` (`scripts/licenses.py`; the list is in [`NOTICE.md`](../NOTICE.md)) |
| Strict mypy | types in all the Python code | `make typecheck` |
| pytest | 880+ tests; in CI, with ffmpeg 8 (Ubuntu 26.04) | `make test` |
| Skip policy | in CI (`KARAOKE_STRICT_SKIPS=1`) a test may only be skipped for lack of a GPU, ML libraries, models or downloaded songs, systemd, or local-only measurements; any other skip (say, a missing ffmpeg) is a failure | `conftest.py` |
| Documentation links | a relative link in a Markdown file pointing to something that is not in the repository (a dead link on GitHub) | `make test` (`scripts/check_links.py`) |
| Contracts | the JSON schemas, the OpenAPI document and the generated TS types up to date | `make contracts` |
| Web: prettier, eslint with types, knip | besides style: unawaited promises, `any` coming out of unchecked JSON, dead code and dependencies | `pnpm --dir web lint` |
| Web: svelte-check, vitest, build | types (`strict`, `noImplicitOverride`, `noFallthroughCasesInSwitch`) and 340+ tests | `make web` |
| Browser (Playwright) | the app on a phone, a laptop and a TV against the stand-in server | `pnpm --dir web test:e2e` (also in CI) |
| Installer | `make install` breaking on a new machine | the CI runs it twice on a clean Ubuntu, with Node 22 and 26 |
| Workflow security | minimal permissions, actions pinned to a commit, injections | `uvx zizmor@1 --offline .github/workflows` (also in CI) |

A new rule only goes in with a clean baseline. What a rule cannot know is justified on the line
(`# noqa: S310 - fixed https URL`); never a `noqa` or an `eslint-disable` without a reason.

## Tests

- `make test` runs the suite in parallel (`-n 6`, about 60 s and 2.5 GB of RAM), without the tests
  marked `@pytest.mark.models`, which load real models (2–3 GB per file): those run apart with
  `make test-models`, one at a time and each file in its own process (together they reached
  4.9 GB), and they refuse to start while a karaoke is being made on the GPU.
- A test that needs ffmpeg asks for the `ffmpeg` fixture (in `conftest.py`); one that needs a GPU,
  models or songs is skipped with a clear reason.
- Outside CI, local only: `pnpm --dir web test:e2e:server` (the web app against the real server;
  it needs the example songs' audio) and the benchmark.

## Property-based tests

- `packages/contracts/tests/test_properties.py` (Hypothesis): the validator answers any JSON with
  problems, never with an exception; saving and loading a document loses nothing, whatever the
  text.
- `packages/server/tests/test_api_schema.py` (Schemathesis): requests generated from the server's
  own OpenAPI, as the owner and as a home guest; none returns a 5xx.
- The lyrics layout exists in Python and in TypeScript: both pass the shared cases in
  `fixtures/lyrics-layout/` (`python -m karaoke_engine.subtitles.conformance --write`); there are
  cases with long lines in portrait.

## Performance

- Engine: the benchmark measures each step's time and memory ([`benchmark.md`](benchmark.md)).
- Web: `pnpm --dir web perf` (JavaScript per screen, after `pnpm build`) and
  `pnpm --dir web perf:frames` (time between the lyrics' frames with the CPU slowed down ×4 and ×6,
  like an average phone).

## Auditing in depth (now and then)

| What | How |
|---|---|
| Python vulnerabilities | `uv export --all-extras --no-hashes --no-emit-workspace > /tmp/req.txt && uvx pip-audit -r /tmp/req.txt --no-deps --disable-pip` |
| Web vulnerabilities | `pnpm --dir web audit` |
| Secrets in the history | gitleaks (`gitleaks git .`), from a separate folder |
| Dead Python code | `uvx vulture packages --min-confidence 80 --exclude '*/tests/*'` (check by hand: pydantic models and routes show up as false positives) |
| A second opinion on types | `uvx pyrefly check` on `packages/*/src` (only to look for bugs; not a gate) |
| Review by area | contracts and alignment; subtitles, video and audio; benchmark; server; the player's web code; the party, editor and API web code |
