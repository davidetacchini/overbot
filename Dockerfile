FROM python:3.11.6-bullseye

RUN mkdir app

WORKDIR /app

RUN export DEBIAN_FRONTEND=noninteractive; \
	apt-get update; \
	apt-get upgrade -y; \
	apt-get install -y \
	python3-dev \
	libgit2-dev \
	musl; \
	curl -sSL https://install.python-poetry.org | python3 -

COPY . .

RUN poetry install

CMD [ "python3" "bot.py" ]