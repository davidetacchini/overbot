FROM ubuntu:22.04

ENV	POETRY_VIRTUALENVS_CREATE=false \
	POETRY_VIRTUALENVS_IN_PROJECT=false

RUN mkdir app

WORKDIR /app

RUN	apt-get update && apt-get install -y software-properties-common; \
	add-apt-repository -y ppa:fkrull/deadsnakes; \
	apt-get update; \
	apt-get install -y \
	python3.11 \
	python3.11-dev \
	python3-pip \
	libgit2-dev \
	curl \
	gcc \
	git \
	wget \
	&& python3.11 -m pip install --upgrade pip poetry

COPY . .

RUN python3.11 -m poetry update && python3.11 -m poetry install --without dev

CMD [ "python3.11", "bot.py" ]