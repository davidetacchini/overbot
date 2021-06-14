.PHONY: clean
clean:
	rm -rf ./__pycache__
	rm -rf */__pycache__

.PHONY: install
install:
	@pip install --upgrade pip
	@pip install --no-cache-dir --upgrade -r requirements.txt
	@pip install --no-cache-dir --upgrade -r requirements-dev.txt

.PHONY: format
format:
	isort .
	black --exclude=env --line-length=88 .
	flake8 .
