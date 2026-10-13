SHELL := /bin/bash
BACKEND_DIR := src/backend
FRONTEND_DIR := src/frontend
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 5173
PYTHON := $(abspath $(BACKEND_DIR)/.venv/bin/python)
RUFF := $(abspath $(BACKEND_DIR)/.venv/bin/ruff)
.PHONY: install backend-install frontend-install check test build verify verify-plan contract-export contract-check frontend-api-generate frontend-api-check backend-check backend-test frontend-build db-current db-migrate
install: backend-install frontend-install
backend-install:
	uv sync --project $(BACKEND_DIR) --locked --no-install-project
frontend-install:
	npm ci --prefix $(FRONTEND_DIR)
backend-check:
	cd $(BACKEND_DIR) && $(RUFF) check . && $(RUFF) format --check .
backend-test:
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest
contract-export:
	cd $(BACKEND_DIR) && $(PYTHON) -m hippobox.export_openapi ../../contracts/openapi.json
contract-check:
	cd $(BACKEND_DIR) && $(PYTHON) -m hippobox.export_openapi ../../contracts/openapi.json --check
frontend-api-generate:
	npm run generate:api --prefix $(FRONTEND_DIR)
frontend-api-check:
	npm run api:check --prefix $(FRONTEND_DIR)
check: backend-check contract-check frontend-api-check
	npm run typecheck --prefix $(FRONTEND_DIR)
test: backend-test
frontend-build:
	npm run build --prefix $(FRONTEND_DIR)
build: frontend-build
	cd $(BACKEND_DIR) && HIPPOBOX_SKIP_FRONTEND_BUILD=1 $(PYTHON) -m hatchling build
verify-plan:
	@echo 'Full foundation verification: lint/format, offline API contract/types, backend regression, frontend build, wheel/sdist, real-browser flows and installed-package smoke. PostgreSQL history uses a separate Docker target.'
verify: check test build
	npm run test:e2e --prefix $(FRONTEND_DIR)
	$(PYTHON) scripts/check-package.py
	git diff --check
# Explicit operator actions only; verify never contacts the configured database.
db-current:
	cd $(BACKEND_DIR) && $(PYTHON) -m alembic current
db-migrate:
	cd $(BACKEND_DIR) && $(PYTHON) -m alembic upgrade head
.PHONY: test-migrations-postgres
test-migrations-postgres:
	cd $(BACKEND_DIR) && HIPPOBOX_TEST_POSTGRES=1 $(PYTHON) -m pytest tests/test_migrations.py
.PHONY: frontend-test
frontend-test: frontend-build
	npm run test:e2e --prefix $(FRONTEND_DIR)
.PHONY: package-check
package-check: build
	$(PYTHON) scripts/check-package.py

.PHONY: dev dev-local backend-dev backend-dev-local frontend-dev
dev:
	BACKEND_PORT="$(BACKEND_PORT)" FRONTEND_PORT="$(FRONTEND_PORT)" $(PYTHON) scripts/dev.py
dev-local:
	VDB_ENABLED=false REDIS_IN_MEMORY=true $(MAKE) dev
backend-dev-local:
	VDB_ENABLED=false REDIS_IN_MEMORY=true $(MAKE) backend-dev
backend-dev:
	cd $(BACKEND_DIR) && $(PYTHON) -m uvicorn hippobox.server:app --reload --host 127.0.0.1 --port "$(BACKEND_PORT)"
frontend-dev:
	cd $(FRONTEND_DIR) && BACKEND_PORT="$(BACKEND_PORT)" npm run dev:vite -- --host 127.0.0.1 --port "$(FRONTEND_PORT)" --strictPort

# Release operations use docker/.env; config output deliberately omits secrets.
RELEASE_COMPOSE := docker compose --env-file docker/.env -f docker/compose.release.yml
.PHONY: release-config release-pull release-up release-status release-logs
release-config:
	$(RELEASE_COMPOSE) config --quiet
release-pull:
	$(RELEASE_COMPOSE) pull
release-up:
	$(RELEASE_COMPOSE) up -d --wait
release-status:
	$(RELEASE_COMPOSE) ps
release-logs:
	$(RELEASE_COMPOSE) logs --tail=100
