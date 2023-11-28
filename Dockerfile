FROM python:3.11-slim as py-builder
LABEL stage=builder

# https://python-poetry.org/docs#ci-recommendations
ENV POETRY_VERSION=1.5.0
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv

# Creating a virtual environment just for poetry and install it with pip
RUN python3 -m venv $POETRY_VENV \
	&& $POETRY_VENV/bin/pip install -U pip setuptools \
	&& $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}

COPY . /app

WORKDIR /app

# Add Poetry to PATH
ENV PATH="${PATH}:${POETRY_VENV}/bin"

RUN poetry check

RUN poetry config virtualenvs.in-project true &&  \
    poetry install --no-interaction --no-cache --without dev


FROM node:16 as js-builder
LABEL stage=builder

COPY . /app
WORKDIR /app
RUN npm install

# Create a new stage from the base python image
FROM python:3.11-slim as hypercorn-runner

WORKDIR /app

COPY --from=py-builder app/.venv /app/.venv
COPY --from=js-builder app/node_modules /app/node_modules

# Copy Application
COPY ff /app/ff

# Run Application
EXPOSE 5000

ENV ENV LOCAL
CMD [".venv/bin/hypercorn", "ff.cloud.runner", "--bind", "0.0.0.0:5000"]
