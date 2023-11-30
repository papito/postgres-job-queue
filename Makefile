SHELL=/bin/sh

clean:
	rm -rf ./ff/.mypy_cache ./ff/__pycache__

install:
	poetry install

update:
	@poetry update

shell:
	@poetry shell

up:
	docker-compose -f docker-compose.yml -f docker-compose.test.yml up

test:
	poetry run pytest tests

dev:
	@export ENV=LOCAL && poetry run python runserver.py

schema:
	@export ENV=LOCAL && poetry run python init_schema.py

lint:
	poetry run isort jobq/ tests/
	poetry run black --line-length 120 jobq/ tests/
	poetry run flake8 jobq/ tests/
	poetry run mypy --check-untyped-defs jobq/ tests/
