.PHONY: test lint format run tree

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check . --fix

run:
	uv run python -m affiliate_os

tree:
	find . -maxdepth 3 \
		-not -path './.venv*' \
		-not -path './.pytest_cache*' \
		-not -path './.ruff_cache*' \
		-not -path '*/__pycache__*' \
		-print | sort
