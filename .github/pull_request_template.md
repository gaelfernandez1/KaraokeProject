## What and why

<!-- What changes for someone using the karaoke, and why. Link the issue if there is one. -->

## How it was checked

- [ ] `make ci` passes
- [ ] Tests that failed before the change (TDD), for each behaviour it adds or fixes
- [ ] Engine quality or speed: measured with the benchmark, report in `bench/results/`
- [ ] Web: `pnpm --dir web test:e2e`, and screenshots at phone, laptop and TV sizes if it looks different
- [ ] Contracts: `make contracts` run and the generated files committed
- [ ] Docs and `CHANGELOG.md` (`Unreleased`) updated
