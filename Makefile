.PHONY: setup lint format typecheck test contracts web check-env ci serve

# --inexact keeps packages that are already installed, so torch from `uv sync --extra ml`
# survives a later `make setup` on the GPU machine.
setup:
	uv sync --inexact
	uv run pre-commit install
	pnpm --dir web install

lint:
	uv run ruff format --check .
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy

test:
	uv run pytest -q

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
