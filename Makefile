.PHONY: setup lint format typecheck test ci

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

ci: lint typecheck test
