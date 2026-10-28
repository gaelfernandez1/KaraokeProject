.PHONY: setup lint format typecheck test contracts web ci

setup:
	uv sync
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

# Regenerates schemas/ from the pydantic models, then the TS types from schemas/.
contracts:
	uv run python -m karaoke_contracts.schema_export schemas
	pnpm --dir web gen:contracts

web:
	pnpm --dir web lint
	pnpm --dir web check
	pnpm --dir web test
	pnpm --dir web build

ci: lint typecheck test web
