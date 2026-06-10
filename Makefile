SHELL := /bin/bash

-include .env
export

API_DIR := apps/api
WEB_DIR := apps/web
UV_CACHE_DIR ?= /tmp/uv-cache
COMPOSE ?= docker compose

API_HOST ?= 0.0.0.0
API_PORT ?= 8000
WEB_PORT ?= 3000
API_BASE_URL ?= http://localhost:$(API_PORT)

.DEFAULT_GOAL := help

.PHONY: help install install-api install-web dev dev-api dev-web db-up db-down db-migrate test test-api test-web test-db lint lint-api lint-web seed health

help:
	@printf "MeterDesk M0 commands:\n"
	@printf "  make install   Install API and Web dependencies\n"
	@printf "  make db-up     Start local Postgres with Docker Compose\n"
	@printf "  make dev       Start Postgres, FastAPI, and Next.js\n"
	@printf "  make health    Check API and database health endpoints\n"
	@printf "  make test      Run API and Web tests\n"
	@printf "  make test-db   Run Postgres-backed M3 migration/seed/API checks\n"
	@printf "  make lint      Run API and Web lint/type checks\n"
	@printf "  make seed      Reset and load M3 demo mock billing data\n"

install: install-api install-web

install-api:
	cd $(API_DIR) && uv --cache-dir $(UV_CACHE_DIR) sync

install-web:
	cd $(WEB_DIR) && npm install

db-up:
	$(COMPOSE) up -d postgres

db-down:
	$(COMPOSE) down

db-migrate:
	cd $(API_DIR) && PYTHONPATH=src uv --cache-dir $(UV_CACHE_DIR) run alembic upgrade head

dev: db-up
	@printf "Starting MeterDesk API on :$(API_PORT) and Web on :$(WEB_PORT)\n"
	@( cd $(API_DIR) && PYTHONPATH=src uv --cache-dir $(UV_CACHE_DIR) run uvicorn meterdesk_api.main:app --reload --host $(API_HOST) --port $(API_PORT) ) & \
	api_pid=$$!; \
	( cd $(WEB_DIR) && API_BASE_URL=$(API_BASE_URL) npm run dev -- --hostname 0.0.0.0 --port $(WEB_PORT) ) & \
	web_pid=$$!; \
	trap 'kill $$api_pid $$web_pid 2>/dev/null' INT TERM EXIT; \
	wait $$api_pid $$web_pid

dev-api:
	cd $(API_DIR) && PYTHONPATH=src uv --cache-dir $(UV_CACHE_DIR) run uvicorn meterdesk_api.main:app --reload --host $(API_HOST) --port $(API_PORT)

dev-web:
	cd $(WEB_DIR) && API_BASE_URL=$(API_BASE_URL) npm run dev -- --hostname 0.0.0.0 --port $(WEB_PORT)

test: test-api test-web

test-api:
	cd $(API_DIR) && uv --cache-dir $(UV_CACHE_DIR) run pytest

test-web:
	cd $(WEB_DIR) && npm test

test-db: db-up seed
	cd $(API_DIR) && PYTHONPATH=src uv --cache-dir $(UV_CACHE_DIR) run python -m meterdesk_api.db_integration_check

lint: lint-api lint-web

lint-api:
	cd $(API_DIR) && uv --cache-dir $(UV_CACHE_DIR) run ruff check .
	cd $(API_DIR) && uv --cache-dir $(UV_CACHE_DIR) run ruff format --check .

lint-web:
	cd $(WEB_DIR) && npm run lint
	cd $(WEB_DIR) && npm run typecheck

seed: db-migrate
	cd $(API_DIR) && PYTHONPATH=src uv --cache-dir $(UV_CACHE_DIR) run python -m meterdesk_api.seed

health:
	curl --fail --silent http://localhost:$(API_PORT)/health
	@printf "\n"
	curl --fail --silent http://localhost:$(API_PORT)/health/db
	@printf "\n"
