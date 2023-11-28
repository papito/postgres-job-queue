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
	docker-compose up

dev:
	poetry run python runserver.py

schema:
	@export ENV=LOCAL && poetry run python init_schema.py

lint:
	poetry run isort jobq
	poetry run black --line-length 120 jobq/
	poetry run flake8 jobq/
	poetry run mypy --check-untyped-defs jobq/

info:
	@poetry env info
