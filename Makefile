clean:
	rm -rf ./__pycache__
	rm -rf ./classes/__pycache__
	rm -rf ./cogs/__pycache__
	rm -rf ./utils/__pycache__

install:
	pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

format:
	./scripts/format.sh

chlog:
	git-chglog
	git-chglog -o CHANGELOG.md

upgrade:
	pip install --no-cache-dir --upgrade pip -r requirements.txt -r requirements-dev.txt

run:
	python bot.py
