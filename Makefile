.PHONY: help dev test test-v build migrate seed backup clean

PYTHON = .venv/Scripts/python.exe
PYTEST = $(PYTHON) -m pytest

help:
	@echo "ApnaERP Makefile Commands:"
	@echo "  make dev       - Run development Uvicorn server"
	@echo "  make test      - Run all pytest integration tests"
	@echo "  make migrate   - Execute Alembic database migration"
	@echo "  make seed      - Seed RBAC permissions and default roles"
	@echo "  make backup    - Execute database backup"
	@echo "  make build     - Build production Docker image"

dev:
	$(PYTHON) -m uvicorn app.main:app --reload --port 8000

test:
	$(PYTEST) -v -p no:logging

migrate:
	$(PYTHON) -m alembic upgrade head

seed:
	$(PYTHON) -m app.db.seed_rbac

backup:
	$(PYTHON) cli.py backup create

build:
	docker build -t apnaerp:v1.3.0 .
