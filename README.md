# A job queue example with Postgres

Visit the blog post which goes into more detail about the features of this project.

This README only describes the steps of getting the code
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

Initialize the schema:
    
    poetry run python init_schema.py
    
OR:

    make schema

## Running

Run the server:

    @export ENV=LOCAL && poetry run python runserver.py    

OR:

    make dev

Now you can view and create jobs on [localhost:5000](localhost:5000).

Go back to the server console to see what the workers are up to...


## Tinkering

You can change the parameters, such as polling frequency and the number of workers
in `env/local.env`.
