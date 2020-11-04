.PHONY: clean
clean:
	rm -rf ./__pycache__
	rm -rf */__pycache__

.PHONY: install
install:
	@pip install --upgrade pip
	@pip install -r requirements.txt
	@pip install -r requirements-dev.txt

.PHONY: format
format:
	isort .
	black --exclude=env --line-length=88 .
	flake8 .

.PHONY: chlog
chlog:
	git-chglog
	git-chglog -o CHANGELOG.md

.PHONY: upgrade
upgrade:
	@pip install --upgrade pip
	@pip install --upgrade -r requirements.txt
	@pip install --upgrade -r requirements-dev.txt

.PHONY: run
run:
	python bot.py
