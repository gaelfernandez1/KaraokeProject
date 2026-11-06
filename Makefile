.PHONY: setup lint format typecheck test test-models contracts web check-env ci serve

# --inexact keeps packages that are already installed, so torch from `uv sync --extra ml`
# survives a later `make setup` on the GPU machine.
setup:
	uv sync --inexact
	uv run pre-commit install
	pnpm --dir web install

lint:
	uv run ruff format --check .
	uv run ruff check .
	# Every import a package makes is declared by that package (deptry reads its pyproject).
	for p in packages/*/; do (cd $$p && uv run deptry src) || exit 1; done
	uv run lint-imports

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy

# Six workers: about a minute and 2.5 GB of RAM. The tests that load real models run apart.
test:
	uv run pytest -q -n 6

# The tests that load real models, one file per process (each needs 2 to 3 GB and torch keeps it
# until the process ends). Never next to a karaoke being made: two models do not fit in 4 GB of
# GPU nor in the RAM WSL has.
test-models:
	@if [ -n "$$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null)" ] || \
		systemctl --user list-units 'karaoke-*.scope' --state=running --no-legend 2>/dev/null | grep -q .; then \
		echo "A karaoke is being made (the GPU is busy): try again when it ends." >&2; exit 1; \
	fi
	for f in $$(uv run pytest -q --co -m models | grep '::' | cut -d: -f1 | sort -u); do \
		uv run pytest -q -m models $$f || exit 1; \
	done

# Regenerates schemas/ from the pydantic models and the server's API, then the TS types.
contracts:
	uv run python -m karaoke_contracts.schema_export schemas
	uv run karaoke-server openapi --out schemas/openapi.json
	pnpm --dir web gen:contracts
	pnpm --dir web gen:api

web:
	pnpm --dir web lint
	pnpm --dir web check
	pnpm --dir web test
	pnpm --dir web build

check-env:
	uv run python scripts/check_env.py

# Regenerates the contracts first so a stale schema or TS type shows up locally, as in CI.
ci: contracts lint typecheck test web

# The server with the built web app (built once if missing). Not `uv run`: it would sync the
# environment without the GPU extras.
serve:
	test -f web/build/index.html || pnpm --dir web build
	.venv/bin/karaoke-server serve
