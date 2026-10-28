.PHONY: setup lint format typecheck test contracts ci

setup:
	uv sync
	uv run pre-commit install

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

contracts:
	uv run python -m karaoke_contracts.schema_export schemas

ci: lint typecheck test
