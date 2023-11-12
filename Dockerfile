FROM python:3.11-slim

ENV POETRY_HOME="/opt/poetry" \
	POETRY_VIRTUALENVS_CREATE=false \
	POETRY_NO_INTERACTION=1 \
	POETRY_CACHE_DIR=/tmp/poetry_cache

RUN apt-get update && \
	apt-get install -y \
	libgit2-dev \
	git \
	gcc \
	curl && \
	curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app

COPY . .

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without dev --no-root

CMD [ "python3", "launcher.py" ]
