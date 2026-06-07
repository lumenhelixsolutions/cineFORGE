.PHONY: all install dev test lint build clean

PYTHON := python3.12
VENV := .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
MYPY := $(VENV)/bin/mypy
UVICORN := $(VENV)/bin/uvicorn

all: install dev

install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[vertex,fal,dev]"
	cd ui && npm install

dev:
	@echo "Starting backend..."
	$(UVICORN) backend.app:app --host 127.0.0.1 --port 8765 --reload &
	@echo "Starting frontend dev server..."
	cd ui && npm run dev

tauri-dev:
	cargo tauri dev

tauri-build:
	cargo tauri build

test:
	$(PYTEST) tests/unit/ -v

test-integration:
	$(PYTEST) tests/integration/ -v

test-e2e:
	$(PYTEST) tests/e2e/ -v --browser chromium

lint:
	$(MYPY) backend/ --strict

docs:
	python docs/export_docs.py

clean:
	rm -rf $(VENV) ui/node_modules ui/dist src-tauri/target
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
