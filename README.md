# A job queue example with Postgres

[See the blog post](https://renegadeotter.com/2023/11/30/job-queues-with-postrgres.html)
which goes into more detail about the features of this project. This README only describes the steps of getting the code
up and running locally.

## Prerequisites
 * Python 3.11 or higher
 * [Poetry](https://python-poetry.org/)
 * Docker Compose
 * Make (optional)

## Initializing
Install the libraries:

    poetry install

Bring up the local and test databases (this will run in its own window):

    docker-compose -f docker-compose.yml -f docker-compose.test.yml up
    
    OR
    
    make up

Initialize the schema:
    
    poetry run python init_schema.py
    
    OR
    
    make schema

## Running

Run the server:

    @export ENV=LOCAL && poetry run python runserver.py
    
    OR
    
    make dev

Now you can view and create jobs on [localhost:5000](http://localhost:5000). 
Go back to the server console to see what the workers are doing.

## Testing

    poetry run pytest tests
    
    OR
    
    make test

## Linting

    poetry run isort jobq/ tests/
    poetry run black --line-length 120 jobq/ tests/
    poetry run flake8 jobq/ tests/
    poetry run mypy --check-untyped-defs jobq/ tests/ 
    
    OR
    
    make lint

## Tinkering

You can change the parameters, such as polling frequency and the number of workers
in `env/local.env`.
