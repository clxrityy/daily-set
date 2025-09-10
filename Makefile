PY ?= python3
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
UVICORN = $(VENV)/bin/uvicorn
PYTEST = $(VENV)/bin/pytest

.PHONY: help venv install init-db run run-dev test test-backend test-frontend clean dev frontend-install frontend-dev frontend-build deploy db-reset load-test realtime-dev nats-dev realtime-build

help:
	@echo "Targets:"
	@echo "  make venv       - create virtualenv at .venv"
	@echo "  make install    - install deps into .venv"
	@echo "  make init-db    - initialize sqlite db"
	@echo "  make db-reset   - delete local sqlite db (set.db) and re-initialize"
	@echo "  make run        - run uvicorn (prod-ish)"
	@echo "  make run-dev    - run uvicorn with --reload"
	@echo "  make test       - run pytest"
	@echo "  make frontend-install - install frontend deps"
	@echo "  make frontend-dev     - start Vite dev server"
	@echo "  make frontend-build   - build React app into app/static/dist"
	@echo "  make deploy      - build frontend and deploy with fly deploy"
	@echo "  make realtime-dev - run Go realtime gateway (requires Go)"
	@echo "  make nats-dev     - run local NATS broker via docker (requires Docker)"
	@echo "  make realtime-build - build Go realtime binary"

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

test: test-backend test-frontend test-realtime

test-backend: install
	$(PYTEST)

test-frontend: frontend-install
	cd frontend && npm test

test-realtime:
	cd realtime && go test

clean:
	rm -rf $(VENV) set.db __pycache__ .pytest_cache

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

deploy: frontend-build
	bash scripts/deploy.sh
	bash scripts/realtime_deploy.sh
	bash scripts/nats_deploy.sh

# Delete local SQLite DB and re-initialize schema
db-reset: install
	rm -f set.db
	$(PYTHON) -m app.init_db

# Run a simple k6 load test (requires k6 installed locally)
load-test:
	BASE_URL=http://127.0.0.1:8000 k6 run scripts/k6/simple.js

# --- Realtime (Go) helpers ---
realtime-build:
	cd realtime && go build -o realtime .

realtime-dev:
	cd realtime && REALTIME_ADDR=":8081" go run .

nats-dev:
	docker run --rm -p 4222:4222 -p 8222:8222 -p 6222:6222 --name nats-dev nats:latest -js

# Kill port 8081 (for realtime dev)
kill-port:
	bash scripts/kill_port.sh

# Development environment
dev: frontend-build
	bash scripts/dev_full.sh