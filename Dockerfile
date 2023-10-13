FROM python:3.11-slim

ENV POETRY_HOME="/opt/poetry" \
	POETRY_VIRTUALENVS_CREATE=false \
	POETRY_NO_INTERACTION=1

RUN apt-get update && \
	apt-get install -y \
	libgit2-dev \
	git \
	curl && \
	curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app

COPY . .

RUN poetry update && poetry install --without dev --no-ansi

CMD [ "python3", "bot.py" ]
