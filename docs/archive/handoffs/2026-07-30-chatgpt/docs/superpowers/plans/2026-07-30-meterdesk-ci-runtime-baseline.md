# MeterDesk CI and Runtime Baseline Implementation Plan

> **Archive status: Stale — do not execute.** This plan was generated from a static review before
> the handoff was integrated. Use the active P0-01 feature spec and generate a fresh implementation
> plan from the current codebase.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reproducible backend/frontend CI, production container images, a seeded full-stack
Compose runtime, and a no-provider-key smoke test without changing MeterDesk domain behavior.

**Architecture:** Build separate non-root API and Web runtime images from the repository root. Extend
Compose with one-shot migration/seed services plus long-running Postgres/API/Web services. Reuse the
existing Make interface as the single local/CI command surface, and gate pull requests with backend,
frontend, database-integration, and full-stack smoke jobs.

**Tech Stack:** Python 3.12, uv 0.11.16, FastAPI, Alembic, Postgres 16, Node 22, Next.js 15,
Docker/Compose, GitHub Actions.

## Global Constraints

- Preserve Duplicate Charge as the golden path.
- Keep Credit/Refund Dispute as a supporting governed workflow.
- Keep Usage Spike as an explicit coverage gap.
- Keep all financial mutations mock-only.
- Do not change planner, decision, approval, mutation, trace or eval semantics.
- Do not require a real OpenAI-compatible provider in CI or container smoke.
- Do not copy `.env` or secrets into images.
- Use committed `uv.lock` and `package-lock.json`.
- Runtime containers must use non-root users.
- Existing host-based `make dev`, `make test`, `make test-db`, `make lint`, `make seed` and
  `make demo-reset-live` must keep their current meaning.
- Do not introduce worker, Redis, authentication, OpenTelemetry, deployment or registry publishing.
- Treat `docs/codex-handoff/portfolio-hardening/specs/P0-01-ci-runtime-baseline.md` as the source of
  truth.

---

## File Structure

### Create

- `.dockerignore` — root build-context exclusions.
- `apps/api/Dockerfile` — locked, non-root FastAPI runtime image.
- `apps/web/Dockerfile` — locked, non-root Next standalone runtime image.
- `.github/workflows/ci.yml` — four required CI jobs.
- `scripts/ci/container-smoke.sh` — deterministic clean-stack smoke verification.
- `docs/runbooks/container-demo.md` — operator instructions.

### Modify

- `apps/web/next.config.ts` — enable standalone build output.
- `compose.yaml` — add migrate, seed, api and web services.
- `Makefile` — expose container build/up/seed/smoke/down targets.
- `README.md` — document host and container workflows separately.
- `docs/codex-handoff/portfolio-hardening/evidence-matrix.md` — record implemented evidence after
  verification.

### Do not modify unless a verified build failure requires it

- application schemas
- database models or migrations
- agent orchestration
- governance policies
- eval behavior
- frontend product components

If a build failure appears to require one of those files, stop that portion and report the conflict before
changing behavior.

---

### Task 1: Establish the root container build contract

**Files:**
- Create: `.dockerignore`
- Inspect only: `.gitignore`
- Verify: repository root build context

**Interfaces:**
- Produces: one root Docker build context suitable for both `apps/api/Dockerfile` and
  `apps/web/Dockerfile`.
- Consumes: existing root `README.md`, `apps/api/uv.lock`, `apps/web/package-lock.json`.

- [ ] **Step 1: Verify the current build files are absent**

Run:

```bash
test ! -f apps/api/Dockerfile
test ! -f apps/web/Dockerfile
test ! -f .dockerignore
```

Expected: all commands exit `0` on the reviewed baseline. If any file exists, read it and refresh this plan
before replacing it.

- [ ] **Step 2: Create `.dockerignore`**

It must exclude at least:

```text
.git
.github
.env
.env.*
!.env.example
**/.venv
**/__pycache__
**/.pytest_cache
**/.ruff_cache
**/node_modules
**/.next
**/coverage
**/test-results
**/playwright-report
*.log
.DS_Store
.superpowers
.codex
.agents
```

Do not exclude:

```text
README.md
apps/api/pyproject.toml
apps/api/uv.lock
apps/api/migrations
apps/api/src
apps/web/package.json
apps/web/package-lock.json
apps/web/src
apps/web/next.config.ts
```

- [ ] **Step 3: Validate required build inputs are visible**

Run:

```bash
for path in   README.md   apps/api/pyproject.toml   apps/api/uv.lock   apps/api/src   apps/api/migrations   apps/web/package.json   apps/web/package-lock.json   apps/web/src   apps/web/next.config.ts
do
  test -e "$path" || { echo "missing build input: $path"; exit 1; }
done
```

Expected: exit `0`.

- [ ] **Step 4: Check formatting**

Run:

```bash
git diff --check
```

Expected: exit `0`.

- [ ] **Step 5: Commit**

```bash
git add .dockerignore
git commit -m "build: define container build context"
```

---

### Task 2: Add the locked non-root API image

**Files:**
- Create: `apps/api/Dockerfile`
- Inspect: `apps/api/pyproject.toml`
- Inspect: `apps/api/uv.lock`
- Inspect: `apps/api/alembic.ini`

**Interfaces:**
- Produces image target: `meterdesk-api`.
- Default process: Uvicorn on `0.0.0.0:8000`.
- Alternate Compose commands:
  - `alembic upgrade head`
  - `python -m meterdesk_api.seed`
- Environment consumed:
  - `DATABASE_URL`
  - `FRONTEND_ORIGIN`
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL`
  - `OPENAI_BASE_URL`

- [ ] **Step 1: Demonstrate the current API image build failure**

Run:

```bash
docker build -f apps/api/Dockerfile -t meterdesk-api:test .
```

Expected before implementation: FAIL because `apps/api/Dockerfile` does not exist.

- [ ] **Step 2: Create a multi-stage API Dockerfile**

Required structure:

```dockerfile
# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.11.16 AS uv

FROM python:3.12-slim AS builder
ENV UV_COMPILE_BYTECODE=1     UV_LINK_MODE=copy
WORKDIR /workspace
COPY --from=uv /uv /uvx /bin/
COPY README.md ./README.md
COPY apps/api/pyproject.toml apps/api/uv.lock ./apps/api/
WORKDIR /workspace/apps/api
RUN uv sync --frozen --no-dev --no-install-project
COPY apps/api/src ./src
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime
ENV PATH="/workspace/apps/api/.venv/bin:$PATH"     PYTHONPATH="/workspace/apps/api/src"     PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1
RUN groupadd --system meterdesk     && useradd --system --gid meterdesk --home-dir /nonexistent meterdesk
WORKDIR /workspace
COPY --from=builder --chown=meterdesk:meterdesk /workspace/README.md ./README.md
COPY --from=builder --chown=meterdesk:meterdesk /workspace/apps/api ./apps/api
COPY --chown=meterdesk:meterdesk apps/api/alembic.ini ./apps/api/alembic.ini
COPY --chown=meterdesk:meterdesk apps/api/migrations ./apps/api/migrations
WORKDIR /workspace/apps/api
USER meterdesk
EXPOSE 8000
CMD ["uvicorn", "meterdesk_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Codex may adjust layer ordering only if:

- lockfile remains authoritative;
- final image excludes dev dependencies;
- migrations are present;
- source imports work;
- final process is non-root;
- root README remains available for package metadata.

- [ ] **Step 3: Build the API image**

Run:

```bash
docker build -f apps/api/Dockerfile -t meterdesk-api:test .
```

Expected: PASS.

- [ ] **Step 4: Verify the process user**

Run:

```bash
docker run --rm --entrypoint sh meterdesk-api:test -c 'test "$(id -u)" -ne 0 && id'
```

Expected: PASS and non-zero UID.

- [ ] **Step 5: Verify imports and migration configuration**

Run:

```bash
docker run --rm   --entrypoint sh   meterdesk-api:test   -c 'python -c "import meterdesk_api.main" && alembic current'
```

Expected:

- application import succeeds;
- Alembic command can locate configuration;
- `alembic current` may fail to connect without `DATABASE_URL`, but must not fail because files/modules are absent.

If the command attempts the default localhost database and exits non-zero, split the check:

```bash
docker run --rm meterdesk-api:test python -c "import meterdesk_api.main"
docker run --rm --entrypoint sh meterdesk-api:test -c 'test -f alembic.ini && test -d migrations'
```

Both must pass.

- [ ] **Step 6: Confirm no development tool is required at runtime**

Run:

```bash
docker run --rm meterdesk-api:test python -c   "import fastapi, sqlalchemy, psycopg, meterdesk_api; print('runtime imports ok')"
```

Expected: `runtime imports ok`.

- [ ] **Step 7: Commit**

```bash
git add apps/api/Dockerfile
git commit -m "build: add MeterDesk API image"
```

---

### Task 3: Add the locked non-root Web image

**Files:**
- Create: `apps/web/Dockerfile`
- Modify: `apps/web/next.config.ts`
- Inspect: `apps/web/package.json`
- Inspect: `apps/web/package-lock.json`

**Interfaces:**
- Produces image target: `meterdesk-web`.
- Default process: standalone Next server on `0.0.0.0:3000`.
- Runtime environment:
  - `API_BASE_URL`
  - `PORT`
  - `HOSTNAME`

- [ ] **Step 1: Add a failing standalone-output assertion**

Run before implementation:

```bash
grep -q 'output: "standalone"' apps/web/next.config.ts
```

Expected: FAIL.

- [ ] **Step 2: Enable standalone output**

Set `apps/web/next.config.ts` to preserve the typed config while adding:

```ts
const nextConfig: NextConfig = {
  output: "standalone",
};
```

- [ ] **Step 3: Create `apps/web/Dockerfile`**

Required structure:

```dockerfile
# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS deps
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/ ./
RUN npm run build

FROM node:22-alpine AS runtime
ENV NODE_ENV=production     NEXT_TELEMETRY_DISABLED=1     HOSTNAME=0.0.0.0     PORT=3000
WORKDIR /app
RUN addgroup --system --gid 1001 nodejs     && adduser --system --uid 1001 nextjs
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
```

If the build proves that a generated asset directory is required, copy that exact directory. Do not add an empty
placeholder directory solely to satisfy Docker.

- [ ] **Step 4: Run the existing frontend verification**

```bash
cd apps/web
npm ci
npm run lint
npm run typecheck
npm test
npm run build
```

Expected: all commands pass and `.next/standalone/server.js` exists.

- [ ] **Step 5: Build the Web image**

From repository root:

```bash
docker build -f apps/web/Dockerfile -t meterdesk-web:test .
```

Expected: PASS.

- [ ] **Step 6: Verify the process user and server artifact**

```bash
docker run --rm --entrypoint sh meterdesk-web:test -c   'test "$(id -u)" -ne 0 && test -f server.js && id'
```

Expected: PASS and non-zero UID.

- [ ] **Step 7: Commit**

```bash
git add apps/web/Dockerfile apps/web/next.config.ts
git commit -m "build: add MeterDesk web image"
```

---

### Task 4: Extend Compose to the seeded full-stack topology

**Files:**
- Modify: `compose.yaml`
- Inspect: `.env.example`
- Inspect: `apps/api/src/meterdesk_api/settings.py`
- Inspect: `apps/web/src/lib/status.ts`
- Inspect: `apps/web/src/lib/meterdesk-api.ts`

**Interfaces:**
- Services:
  - `postgres`
  - `migrate`
  - `seed`
  - `api`
  - `web`
- Internal URLs:
  - Postgres: `postgres:5432`
  - API: `http://api:8000`
- Host URLs:
  - API: `http://localhost:${API_PORT:-8000}`
  - Web: `http://localhost:${WEB_PORT:-3000}`

- [ ] **Step 1: Capture the current Compose config**

Run:

```bash
docker compose config > /tmp/meterdesk-compose-before.yml
grep -q '^  postgres:' /tmp/meterdesk-compose-before.yml
```

Expected: PASS.

- [ ] **Step 2: Extend `compose.yaml`**

Use YAML anchors to avoid duplicating the API build/environment contract. The API,
migrate, and seed services must all declare the same explicit image name, for example
`image: meterdesk-api:local`, so `docker compose build api` produces the image later reused by the
one-shot services. The resolved config must express:

```yaml
services:
  postgres:
    # preserve current image, credentials, port, volume, healthcheck

  migrate:
    image: meterdesk-api:local
    build:
      context: .
      dockerfile: apps/api/Dockerfile
    command: ["alembic", "upgrade", "head"]
    environment:
      DATABASE_URL: postgresql+psycopg://meterdesk:meterdesk@postgres:5432/meterdesk
    depends_on:
      postgres:
        condition: service_healthy

  seed:
    image: meterdesk-api:local
    # same API image/build contract
    command: ["python", "-m", "meterdesk_api.seed"]
    environment:
      DATABASE_URL: postgresql+psycopg://meterdesk:meterdesk@postgres:5432/meterdesk
    depends_on:
      postgres:
        condition: service_healthy

  api:
    image: meterdesk-api:local
    # same API image/build contract
    environment:
      ENVIRONMENT: container
      DATABASE_URL: postgresql+psycopg://meterdesk:meterdesk@postgres:5432/meterdesk
      FRONTEND_ORIGIN: http://localhost:${WEB_PORT:-3000}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      OPENAI_MODEL: ${OPENAI_MODEL:-}
      OPENAI_BASE_URL: ${OPENAI_BASE_URL:-https://api.openai.com/v1}
    ports:
      - "${API_PORT:-8000}:8000"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"
      interval: 5s
      timeout: 3s
      retries: 20

  web:
    image: meterdesk-web:local
    build:
      context: .
      dockerfile: apps/web/Dockerfile
    environment:
      API_BASE_URL: http://api:8000
      PORT: "3000"
      HOSTNAME: 0.0.0.0
    ports:
      - "${WEB_PORT:-3000}:3000"
    depends_on:
      api:
        condition: service_healthy
```

Do not add `container_name` to new services; Compose-generated names reduce collision risk in CI.

- [ ] **Step 3: Validate the resolved Compose config**

Run:

```bash
docker compose config > /tmp/meterdesk-compose.yml
for service in postgres migrate seed api web; do
  grep -q "^  ${service}:" /tmp/meterdesk-compose.yml     || { echo "missing service: ${service}"; exit 1; }
done
```

Expected: PASS.

- [ ] **Step 4: Validate internal URLs**

Run:

```bash
grep -q 'postgres:5432' /tmp/meterdesk-compose.yml
grep -q 'http://api:8000' /tmp/meterdesk-compose.yml
```

Expected: PASS.

- [ ] **Step 5: Start Postgres and run migration**

```bash
docker compose down -v --remove-orphans
docker compose up -d postgres
docker compose run --rm migrate
```

Expected: migration exits `0`.

- [ ] **Step 6: Run seed twice**

```bash
docker compose run --rm seed
docker compose run --rm seed
```

Expected: both runs exit `0`; the second run demonstrates the current idempotent demo reset contract.

- [ ] **Step 7: Start API and Web**

```bash
docker compose up -d api web
docker compose ps
```

Expected: Postgres/API/Web running; API becomes healthy.

- [ ] **Step 8: Verify endpoints manually**

```bash
curl --fail --silent http://localhost:${API_PORT:-8000}/health
curl --fail --silent http://localhost:${API_PORT:-8000}/health/db
curl --fail --silent http://localhost:${API_PORT:-8000}/tickets
curl --fail --silent http://localhost:${WEB_PORT:-3000}/
```

Expected: all return success.

- [ ] **Step 9: Verify no live provider was required**

Run:

```bash
docker compose exec -T api python - <<'PY'
from meterdesk_api.settings import get_settings
settings = get_settings()
assert not settings.openai_api_key
print("seeded runtime does not require provider key")
PY
```

Expected: printed confirmation.

- [ ] **Step 10: Clean up**

```bash
docker compose down -v --remove-orphans
```

Expected: exit `0`.

- [ ] **Step 11: Commit**

```bash
git add compose.yaml
git commit -m "build: add seeded full-stack compose runtime"
```

---

### Task 5: Add stable Make targets and the smoke harness

**Files:**
- Create: `scripts/ci/container-smoke.sh`
- Modify: `Makefile`

**Interfaces:**
- Produces:
  - `make container-build`
  - `make container-up`
  - `make container-seed`
  - `make container-smoke`
  - `make container-down`
- Smoke exits non-zero on any failed invariant.
- Smoke always cleans its own Compose project and volumes.

- [ ] **Step 1: Add a failing Make target check**

Run:

```bash
make -n container-smoke
```

Expected before implementation: FAIL with “No rule to make target”.

- [ ] **Step 2: Create the executable smoke script**

Create `scripts/ci/container-smoke.sh` with these exact behavioral requirements:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-meterdesk-smoke-${GITHUB_RUN_ID:-local}-$$}"
export API_PORT="${API_PORT:-18000}"
export WEB_PORT="${WEB_PORT:-13000}"
export POSTGRES_PORT="${POSTGRES_PORT:-15432}"
unset OPENAI_API_KEY
unset OPENAI_MODEL

cleanup() {
  exit_code=$?
  if [ "$exit_code" -ne 0 ]; then
    docker compose ps || true
    docker compose logs --no-color postgres api web || true
  fi
  docker compose down -v --remove-orphans || true
  exit "$exit_code"
}
trap cleanup EXIT

wait_for_url() {
  local url="$1"
  local attempts="${2:-60}"
  for ((i=1; i<=attempts; i++)); do
    if curl --fail --silent --show-error "$url" >/tmp/meterdesk-smoke-response; then
      return 0
    fi
    sleep 2
  done
  echo "timed out waiting for $url" >&2
  return 1
}

docker compose build api web
docker compose up -d postgres
docker compose run --rm migrate
docker compose run --rm seed
docker compose up -d api web

wait_for_url "http://localhost:${API_PORT}/health"
wait_for_url "http://localhost:${API_PORT}/health/db"
wait_for_url "http://localhost:${API_PORT}/tickets"
grep -q '"TCK-1042"' /tmp/meterdesk-smoke-response
grep -q '"TCK-1137"' /tmp/meterdesk-smoke-response

wait_for_url "http://localhost:${WEB_PORT}/"
grep -q 'MeterDesk' /tmp/meterdesk-smoke-response

echo "MeterDesk container smoke passed."
```

Codex may improve temporary-file handling, but must preserve:

- clean unique Compose project;
- non-default host ports;
- unset provider credentials;
- full cleanup;
- logs on failure;
- seeded ticket assertions;
- Web page assertion.

- [ ] **Step 3: Make the script executable**

```bash
chmod +x scripts/ci/container-smoke.sh
test -x scripts/ci/container-smoke.sh
```

Expected: PASS.

- [ ] **Step 4: Add Make targets**

Extend `.PHONY` and `help`. Required commands:

```make
container-build:
	$(COMPOSE) build api web

container-up:
	$(COMPOSE) up -d postgres
	$(COMPOSE) run --rm migrate
	$(COMPOSE) run --rm seed
	$(COMPOSE) up -d api web

container-seed:
	$(COMPOSE) up -d postgres
	$(COMPOSE) run --rm migrate
	$(COMPOSE) run --rm seed

container-smoke:
	./scripts/ci/container-smoke.sh

container-down:
	$(COMPOSE) down --remove-orphans
```

Document volume reset as an explicit command rather than silently deleting local data in `container-down`.

- [ ] **Step 5: Verify Make command expansion**

```bash
make -n container-build
make -n container-up
make -n container-seed
make -n container-smoke
make -n container-down
```

Expected: all commands resolve.

- [ ] **Step 6: Run the smoke target**

```bash
make container-smoke
```

Expected:

```text
MeterDesk container smoke passed.
```

- [ ] **Step 7: Verify cleanup**

```bash
test -z "$(docker ps -a --filter 'name=meterdesk-smoke-' --format '{{.ID}}')"
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add Makefile scripts/ci/container-smoke.sh
git commit -m "test: add full-stack container smoke"
```

---

### Task 6: Add the GitHub Actions quality gates

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Jobs:
  - `backend-quality`
  - `frontend-quality`
  - `database-integration`
  - `container-smoke`
- No write permissions.
- No repository secrets.
- Container smoke depends on the other three jobs.

- [ ] **Step 1: Confirm the workflow is absent**

```bash
test ! -f .github/workflows/ci.yml
```

Expected: PASS on reviewed baseline.

- [ ] **Step 2: Create `.github/workflows/ci.yml`**

The workflow must include:

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

Backend job requirements:

```yaml
backend-quality:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v6
    - uses: actions/setup-python@v6
      with:
        python-version: "3.12"
    - uses: astral-sh/setup-uv@v8
      with:
        version: "0.11.16"
        enable-cache: true
        cache-dependency-glob: "apps/api/uv.lock"
    - run: cd apps/api && uv sync --frozen
    - run: make lint-api
    - run: make test-api
```

Frontend job requirements:

```yaml
frontend-quality:
  runs-on: ubuntu-latest
  defaults:
    run:
      working-directory: apps/web
  steps:
    - uses: actions/checkout@v6
    - uses: actions/setup-node@v6
      with:
        node-version: "22"
        cache: npm
        cache-dependency-path: apps/web/package-lock.json
    - run: npm ci
    - run: npm run lint
    - run: npm run typecheck
    - run: npm test
    - run: npm run build
```

Do not set a job-level working directory for steps using `actions/*`; only `run` steps inherit it.

Database job requirements:

```yaml
database-integration:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v6
    - uses: actions/setup-python@v6
      with:
        python-version: "3.12"
    - uses: astral-sh/setup-uv@v8
      with:
        version: "0.11.16"
        enable-cache: true
        cache-dependency-glob: "apps/api/uv.lock"
    - run: cd apps/api && uv sync --frozen
    - run: make test-db
    - if: always()
      run: docker compose down -v --remove-orphans
```

Container job requirements:

```yaml
container-smoke:
  needs: [backend-quality, frontend-quality, database-integration]
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v6
    - run: make container-smoke
```

- [ ] **Step 3: Validate workflow YAML**

Use an available YAML parser. With Python:

```bash
python - <<'PY'
from pathlib import Path
import yaml

path = Path(".github/workflows/ci.yml")
data = yaml.safe_load(path.read_text())
assert "jobs" in data
assert set(data["jobs"]) == {
    "backend-quality",
    "frontend-quality",
    "database-integration",
    "container-smoke",
}
print("workflow structure ok")
PY
```

If PyYAML is unavailable in the root environment, use Ruby:

```bash
ruby -e 'require "yaml"; YAML.load_file(".github/workflows/ci.yml"); puts "workflow yaml ok"'
```

Expected: parser succeeds.

Note: YAML 1.1 parsers may interpret the key `on` as boolean. This is acceptable for syntax parsing; do not use
that parser to assert the `on` key.

- [ ] **Step 4: Check that the workflow contains no secrets**

```bash
! grep -R 'secrets\.' .github/workflows/ci.yml
! grep -R 'OPENAI_API_KEY:' .github/workflows/ci.yml
```

Expected: both commands pass.

- [ ] **Step 5: Verify local equivalents**

```bash
make lint
make test
make test-db
make container-smoke
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: gate MeterDesk builds and tests"
```

---

### Task 7: Document the two local execution modes

**Files:**
- Create: `docs/runbooks/container-demo.md`
- Modify: `README.md`
- Modify: `docs/codex-handoff/portfolio-hardening/evidence-matrix.md`

**Interfaces:**
- Documents:
  - host development
  - containerized seeded demo
  - live provider reset path
- Does not alter application behavior.

- [ ] **Step 1: Create the container runbook**

The runbook must contain:

```text
Prerequisites
Quick start
Service URLs
Seed/reset behavior
No-key seeded behavior
Live provider behavior
Container commands
Health checks
Log commands
Volume reset
Troubleshooting
Security notes
```

Required quick start:

```bash
cp .env.example .env
make container-build
make container-up
```

Required verification:

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/health/db
curl --fail http://localhost:3000/
```

Required cleanup:

```bash
make container-down
docker compose down -v --remove-orphans
```

The runbook must explicitly state:

- containerized seeded demo does not need an LLM key;
- seeded audit trail is not a live provider run;
- live provider still requires `OPENAI_API_KEY` and `OPENAI_MODEL`;
- all financial mutations remain mock-only;
- demo Postgres credentials are not production credentials.

- [ ] **Step 2: Update README**

Add a concise “Containerized seeded demo” section near Local setup. Preserve current host commands.

README must link:

```text
docs/runbooks/container-demo.md
```

README must not claim:

```text
deployed
production-ready
high availability
all tests passing
```

unless the actual evidence exists.

- [ ] **Step 3: Update evidence matrix**

For P0-01 rows:

- replace target implementation with actual file paths;
- add exact CI job names;
- add exact smoke command;
- keep status `Planned` until the workflow has run on GitHub;
- use `Verified` only after actual successful workflow run is available.

- [ ] **Step 4: Check documentation commands**

```bash
grep -q 'make container-up' README.md
grep -q 'make container-smoke' docs/runbooks/container-demo.md
grep -q 'mock-only' docs/runbooks/container-demo.md
grep -q 'seeded' docs/runbooks/container-demo.md
```

Expected: PASS.

- [ ] **Step 5: Run final local verification**

```bash
make lint
make test
make test-db
make container-build
make container-smoke
git diff --check
```

Expected: all pass.

- [ ] **Step 6: Review scope**

Run:

```bash
git diff --name-only HEAD~6..HEAD
```

Review the list. It should contain only P0-01 files. It must not contain agent decision, governance, approval,
mutation or eval implementation files.

- [ ] **Step 7: Commit**

```bash
git add README.md docs/runbooks/container-demo.md   docs/codex-handoff/portfolio-hardening/evidence-matrix.md
git commit -m "docs: document reproducible MeterDesk runtime"
```

---

## Final Verification Checklist

- [ ] `docker compose config` succeeds.
- [ ] API image builds.
- [ ] Web image builds.
- [ ] Both runtime processes are non-root.
- [ ] `make lint` passes.
- [ ] `make test` passes.
- [ ] `make test-db` passes.
- [ ] `make container-build` passes.
- [ ] `make container-smoke` passes.
- [ ] smoke uses clean volumes and non-default host ports.
- [ ] smoke does not use provider credentials.
- [ ] seeded tickets are returned.
- [ ] Web page contains MeterDesk.
- [ ] failure path prints service logs.
- [ ] existing host commands remain documented.
- [ ] no domain behavior was changed.
- [ ] GitHub Actions four jobs complete successfully after push.

## Completion Report Format

Codex must return:

```markdown
## Implemented behavior

## Files created

## Files modified

## Container image contract

## CI jobs

## Verification results
- command:
- exit status:
- relevant output:

## GitHub Actions result

## Deviations from plan

## Remaining limitations

## Commits
```

Do not declare completion before providing actual command results.
