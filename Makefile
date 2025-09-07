PY ?= python3
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
UVICORN = $(VENV)/bin/uvicorn
PYTEST = $(VENV)/bin/pytest

.PHONY: help venv install init-db run run-dev test clean frontend-install frontend-dev frontend-build deploy

help:
	@echo "Targets:"
	@echo "  make venv       - create virtualenv at .venv"
	@echo "  make install    - install deps into .venv"
	@echo "  make init-db    - initialize sqlite db"
	@echo "  make run        - run uvicorn (prod-ish)"
	@echo "  make run-dev    - run uvicorn with --reload"
	@echo "  make test       - run pytest"
	@echo "  make frontend-install - install frontend deps"
	@echo "  make frontend-dev     - start Vite dev server"
	@echo "  make frontend-build   - build React app into app/static/dist"
	@echo "  make deploy      - build frontend and deploy with fly deploy"

venv:
	test -d $(VENV) || $(PY) -m venv $(VENV)

install: venv
	$(PIP) install -r requirements.txt

init-db: install
	$(PYTHON) -m app.init_db

run: install
	$(UVICORN) app.main:app --host 127.0.0.1 --port 8000

run-dev: install
	$(UVICORN) app.main:app --reload

test: install
	$(PYTEST)

clean:
	rm -rf $(VENV) set.db __pycache__ .pytest_cache

dev:
	make frontend-build
	$(UVICORN) app.main:app --reload

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

deploy: frontend-build
	bash scripts/deploy.sh

