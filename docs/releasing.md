# Releasing a version

Proxecto Karaoke en Galego has **a single version** for the whole product (the Python packages, the
web app and `CITATION.cff`), following [semantic versioning](https://semver.org/). `make lint`
checks that they all agree and that `CHANGELOG.md` has the entry (`scripts/release.py check`).

## Which number

| Change | Example | Version |
|---|---|---|
| Something stops working as before for existing users: karaoke packages that must be made again, an API or a command that changes, server data that is not migrated automatically | `karaoke.json` 2.0.0, removing an option of `karaoke make` | **major** (4.0.0) |
| Something new that breaks nothing | a language with its own model, a theme, a screen in the app | **minor** (3.1.0) |
| Fixes | a syllable split wrongly, a party bug | **patch** (3.0.1) |

The data contracts (`karaoke.json`, `theme.json`) also carry their own version (`schema_version`),
which changes as described in `plan-v3/decisiones/002-contratos-v0.md`.

There are no pre-releases (`3.1.0-rc.1`): Python writes them `3.1.0rc1`, and the version would no
longer read the same everywhere. To try a release before publishing it, its draft is enough.

## Steps

1. **On a branch**, move what is under `## [Unreleased]` in `CHANGELOG.md` into a new section
   `## [X.Y.Z] - YYYY-MM-DD` (the day it is published) and add its link at the end of the file.
   Write it for people who use the project: what changes for them, not which files were touched.
2. Bump the version in every file and regenerate what depends on it:
   ```bash
   uv run python scripts/release.py set X.Y.Z
   uv lock
   make contracts
   make ci
   ```
3. **Pull request to `main`** and, with the CI green, merge it.
4. **Tag** the merged commit and push the tag:
   ```bash
   git switch main && git pull
   git tag -a vX.Y.Z -m "Proxecto Karaoke en Galego X.Y.Z"
   git push origin vX.Y.Z
   ```
5. The **Release** workflow (`.github/workflows/release.yml`) checks that the tag matches the version
   and leaves the release as a **draft**, with the CHANGELOG section as its notes. If they do not
   match, it fails and creates nothing: delete the tag (`git push origin :vX.Y.Z`), fix it and go
   back to step 1.
6. On GitHub, **review the draft**, attach whatever it needs (a demo MP4, for example) and
   **publish it**. Releases are immutable: once published, their files and their tag no longer
   change. A mistake is fixed with a new version.

`python scripts/release.py notes X.Y.Z` shows locally the notes that will be published.
