.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-40s\033[0m %s\n", $$1, $$2}'

setup: ## Setup a dev environment for working in this repo. Assumes in a venv or other isolation
	pip install -r requirements-dev.txt -r requirements-test.txt
	pre-commit install

test: setup ## run python tests
	pytest

tox: setup ## run tox to test on py3.6-9
	tox

build: ## build python packages
	pip install build
	python -m build --sdist --wheel --outdir dist/

lint: setup ## run python linting
	black statsd_asgi
	flake8
