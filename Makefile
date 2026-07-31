SHELL := /bin/bash

ifeq ($(filter container-smoke,$(MAKECMDGOALS)),)
-include .env
export
endif

API_DIR := apps/api
WEB_DIR := apps/web
UV_CACHE_DIR ?= /tmp/uv-cache
COMPOSE ?= docker compose

API_HOST ?= 0.0.0.0
API_PORT ?= 8000
WEB_PORT ?= 3000
API_BASE_URL ?= http://localhost:$(API_PORT)
CONTAINER_WAIT_TIMEOUT ?= 180

.DEFAULT_GOAL := help

.PHONY: help install install-api install-web dev dev-api dev-web db-up db-down db-migrate test test-api test-web test-db lint lint-api lint-web seed demo-reset-live health container-build container-up container-seed container-smoke container-down

help:
	@printf "MeterDesk commands:\n"
	@printf "  make install   Install API and Web dependencies\n"
	@printf "  make db-up     Start local Postgres with Docker Compose\n"
	@printf "  make dev       Start Postgres, FastAPI, and Next.js\n"
	@printf "  make health    Check API and database health endpoints\n"
	@printf "  make test      Run API and Web tests\n"
	@printf "  make test-db   Run Postgres-backed M3 migration/seed/API checks\n"
	@printf "  make lint      Run API and Web lint/type checks\n"
	@printf "  make seed      Reset and load M5 portfolio baseline data\n"
	@printf "  make demo-reset-live Reset live runtime state; override with TICKET_ID=TCK-1137\n"
	@printf "  make container-build Build API and Web runtime images\n"
	@printf "  make container-up Start the seeded container runtime\n"
	@printf "  make container-seed Migrate and reseed the container database\n"
	@printf "  make container-smoke Run the isolated no-key container smoke path\n"
	@printf "  make container-down Stop containers without removing volumes\n"

install: install-api install-web

install-api:
	cd $(API_DIR) && uv --cache-dir $(UV_CACHE_DIR) sync --frozen

install-web:
	cd $(WEB_DIR) && npm ci

db-up:
	$(COMPOSE) up -d postgres

db-down:
	$(COMPOSE) rm --stop --force postgres

db-migrate:
	cd $(API_DIR) && PYTHONPATH=src uv --cache-dir $(UV_CACHE_DIR) run --frozen alembic upgrade head

dev: db-up
	@printf "Starting MeterDesk API on :$(API_PORT) and Web on :$(WEB_PORT)\n"
	@( cd $(API_DIR) && PYTHONPATH=src uv --cache-dir $(UV_CACHE_DIR) run --frozen uvicorn meterdesk_api.main:app --reload --host $(API_HOST) --port $(API_PORT) ) & \
	api_pid=$$!; \
	( cd $(WEB_DIR) && API_BASE_URL=$(API_BASE_URL) npm run dev -- --hostname 0.0.0.0 --port $(WEB_PORT) ) & \
	web_pid=$$!; \
	trap 'kill $$api_pid $$web_pid 2>/dev/null' INT TERM EXIT; \
	wait $$api_pid $$web_pid

dev-api:
	cd $(API_DIR) && PYTHONPATH=src uv --cache-dir $(UV_CACHE_DIR) run --frozen uvicorn meterdesk_api.main:app --reload --host $(API_HOST) --port $(API_PORT)

dev-web:
	cd $(WEB_DIR) && API_BASE_URL=$(API_BASE_URL) npm run dev -- --hostname 0.0.0.0 --port $(WEB_PORT)

test: test-api test-web

test-api:
	cd $(API_DIR) && uv --cache-dir $(UV_CACHE_DIR) run --frozen pytest

test-web:
	cd $(WEB_DIR) && npm test

test-db: db-up seed
	cd $(API_DIR) && PYTHONPATH=src uv --cache-dir $(UV_CACHE_DIR) run --frozen python -m meterdesk_api.db_integration_check

lint: lint-api lint-web

lint-api:
	cd $(API_DIR) && uv --cache-dir $(UV_CACHE_DIR) run --frozen ruff check .
	cd $(API_DIR) && uv --cache-dir $(UV_CACHE_DIR) run --frozen ruff format --check .

lint-web:
	cd $(WEB_DIR) && npm run lint
	cd $(WEB_DIR) && npm run typecheck

seed: db-migrate
	cd $(API_DIR) && PYTHONPATH=src uv --cache-dir $(UV_CACHE_DIR) run --frozen python -m meterdesk_api.seed

demo-reset-live: db-migrate
	cd $(API_DIR) && PYTHONPATH=src uv --cache-dir $(UV_CACHE_DIR) run --frozen python -m meterdesk_api.demo_reset_live $(TICKET_ID)

health:
	curl --fail --silent http://localhost:$(API_PORT)/health
	@printf "\n"
	curl --fail --silent http://localhost:$(API_PORT)/health/db
	@printf "\n"

container-build:
	$(COMPOSE) build api web

container-up:
	$(COMPOSE) up -d --wait --wait-timeout $(CONTAINER_WAIT_TIMEOUT)

container-seed:
	$(COMPOSE) up -d --wait --wait-timeout $(CONTAINER_WAIT_TIMEOUT) postgres
	$(COMPOSE) run --rm --no-deps migrate
	$(COMPOSE) run --rm --no-deps seed

container-smoke:
	COMPOSE="$(COMPOSE)" ./scripts/container-smoke.sh

container-down:
	$(COMPOSE) down --remove-orphans
