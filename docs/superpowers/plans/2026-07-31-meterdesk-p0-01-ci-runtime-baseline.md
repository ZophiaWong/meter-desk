# MeterDesk P0-01 CI and Runtime Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver MeterDesk P0-01 as one end-to-end pull request with reproducible quality gates, non-root API and Web images, a seeded five-service Compose runtime, a cleanup-safe no-key smoke path, operational documentation, and reviewable local and GitHub evidence.

**Architecture:** Keep the existing Next.js, FastAPI, Postgres, agent, approval, mutation, trace, and eval behavior unchanged. Add packaging and orchestration around those boundaries: one API image reused by `migrate`, `seed`, and `api`; one standalone Web image; Compose-owned project isolation; a guarded smoke script; and one GitHub Actions workflow whose container job depends on the three quality jobs.

**Tech Stack:** Python 3.12, uv 0.11.16, Ruff, pytest, Node.js 22, npm, Next.js 15 standalone output, ESLint, TypeScript, Vitest, Docker 28+, Docker Compose v2.35+, Postgres 16 Alpine, Bash, GitHub Actions.

## Global Constraints

- Baseline commit is `86c737d18d10fd6795c27291f326c534ce1aa1b1` from `origin/main`; implementation branch is `hardening/p0-01-ci-runtime-baseline`.
- Deliver all P0-01 work in one pull request; do not split the workstream without maintainer approval.
- Preserve Duplicate Charge as the golden path, Credit/Refund Dispute as a supporting workflow, and Usage Spike as an explicit coverage gap.
- Do not change business decisions, agent planning, approval routing, mutation idempotency, governance enforcement, trace scoring, eval semantics, or seeded scenario expectations.
- Customer replies remain draft-only; financial mutations remain mock-only and approval-gated.
- Do not add real payment, billing, support, messaging, or accounting integrations; do not add provider routing, authentication, workers, telemetry, pgvector, or large-scale RAG.
- Install API and Web dependencies from committed `apps/api/uv.lock` and `apps/web/package-lock.json`; every install fails on manifest/lock disagreement.
- API and Web runtime containers run as numeric user/group `10001:10001`.
- Default Postgres, API, and Web publications bind to `127.0.0.1`; remote access requires the one
  explicit `CONTAINER_BIND_ADDRESS` override.
- Preserve the application OpenAI base URL when `OPENAI_BASE_URL` is unset, while allowing the smoke
  path to pass an explicitly empty value.
- Normal `make container-down` preserves named volumes. Only the smoke harness may remove volumes, and only after validating its unique `meterdesk-smoke-` project name.
- Smoke passes empty provider configuration explicitly and never prints Compose configuration, `.env`, or secret-bearing environment values.
- Interview collateral under `intv/` is outside this change.
- Promote evidence to `Verified` only after the named command or GitHub job actually succeeds and remains reviewable.

## Confirmed Baseline

- `make lint` fails only on five findings in `apps/api/src/meterdesk_api/eval/regression.py`: import ordering, two unused imports, and two over-length lines.
- `make test` passes with API `68 passed, 6 skipped` and Web `21 passed` under Node 22.22.2 with temp directories rooted at `/tmp`.
- `compose.yaml` defines only `postgres`, fixes `container_name: meterdesk-postgres`, and retains the named volume `meterdesk-postgres-data`.
- No `.github/workflows`, Dockerfiles, root `.dockerignore`, container smoke harness, or container runbook exists.
- Official action documentation confirms the approved majors: `actions/checkout@v6`, `actions/setup-python@v6`, `actions/setup-node@v6`, and `astral-sh/setup-uv@v8`; pin uv itself to `0.11.16`.

## File and Interface Map

### Create

- `.github/workflows/ci.yml`: PR, main-push, and manual CI with four required jobs.
- `.dockerignore`: root build-context exclusion policy, including all real `.env*` files.
- `apps/api/Dockerfile`: frozen production API build and non-root Uvicorn runtime; also supports Alembic and seed commands.
- `apps/web/Dockerfile`: `npm ci` build and non-root Next standalone runtime.
- `apps/api/tests/test_markdown_links.py`: behavioral tests for valid and missing local Markdown targets.
- `scripts/container-smoke.sh`: isolated full-stack build/start/assert/diagnose/cleanup harness.
- `scripts/check_markdown_links.py`: repository-local Markdown link checker for current, non-archived documentation.
- `docs/runbooks/container-demo.md`: seeded container-demo runbook.
- `docs/superpowers/plans/2026-07-31-meterdesk-p0-01-ci-runtime-baseline.md`: this plan.

### Modify

- `apps/api/src/meterdesk_api/eval/regression.py:1-29,102,370`: fix only the five confirmed Ruff findings.
- `apps/web/next.config.ts:1-5`: enable standalone output.
- `compose.yaml:1-25`: replace the Postgres-only topology with `postgres`, `migrate`, `seed`, `api`, and `web` while preserving default credentials, ports, and volume name.
- `Makefile:1-92`: make installs frozen and add the five stable container targets without changing existing host target meanings.
- `README.md:84-147`: preserve host setup and add the seeded container quick start and runbook link.
- `docs/README.md`: index the new runbook and current P0-01 state.
- `docs/specs/system-architecture.md`: record the implemented image and Compose boundary without changing application ownership.
- `docs/specs/implementation-roadmap.md`: promote P0-01 from planning to implementation and identify the next re-review point.
- `docs/specs/hardening/roadmap.md`: update the active-workstream status and P0-01 runtime surface.
- `docs/specs/hardening/p0-01-ci-runtime-baseline.md`: record implementation and verification status using exact artifacts and limitations.
- `docs/evidence/engineering-evidence-matrix.md`: replace P0-01 targets with actual files, commands, job names, and reviewable results.

### Runtime Interfaces

- Compose consumes `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`, `API_PORT`,
  `WEB_PORT`, `CONTAINER_BIND_ADDRESS`, `METERDESK_API_IMAGE`, `METERDESK_WEB_IMAGE`, and optional
  explicit live-provider variables.
- Compose produces internal endpoints `postgres:5432` and `http://api:8000`; host defaults remain Postgres `5432`, API `8000`, and Web `3000`.
- `migrate`, `seed`, and `api` consume the same API image. `api` starts only after successful seed; `web` starts only after API health succeeds.
- `scripts/container-smoke.sh` consumes optional `COMPOSE` and timeout overrides, owns only a unique `meterdesk-smoke-*` project, and returns the primary build/start/assertion exit code even when cleanup also fails.
- Host `db-up` waits for the existing Postgres healthcheck with `CONTAINER_WAIT_TIMEOUT` before a
  dependent migration or seed command can start.
- The Web runtime consumes `API_BASE_URL=http://api:8000`; existing server-side `fetchApi()` and `getSystemStatus()` functions remain unchanged.

---

### Task 1: Establish the clean behavior-neutral quality baseline

**Files:**
- Modify: `apps/api/src/meterdesk_api/eval/regression.py:1-29,102,370`

**Interfaces:**
- Consumes: existing `EvalResultSummary.details`, `EvalVersionDiff`, and regression comparison behavior.
- Produces: the identical regression results under a Ruff-clean source file.

- [ ] **Step 1: Reproduce the exact five-finding failure**

Run:

```bash
env "PATH=/home/poter/.nvm/versions/node/v22.22.2/bin:$PATH" \
  TEMP=/tmp TMP=/tmp TMPDIR=/tmp make lint
```

Expected: exit 2 from Make after Ruff reports one `I001`, two `F401`, and two `E501` findings, all in `eval/regression.py`.

- [ ] **Step 2: Remove only the unused imports and apply Ruff import ordering**

The schema import becomes:

```python
from meterdesk_api.schemas import (
    EvalCaseRegressionSummary,
    EvalCaseSummary,
    EvalDimensionDiff,
    EvalRegressionSummary,
    EvalResultSnapshotSummary,
    EvalResultSummary,
    EvalVersionDiff,
    ToolTraceSummary,
)
```

Do not change any callable, branch, comparison field, or returned value.

- [ ] **Step 3: Wrap only the two over-length expressions**

Use equivalent parenthesized expressions:

```python
failed_checks = (
    result.details.get("failed_checks", []) if isinstance(result.details, dict) else []
)
```

```python
diffs.append(
    EvalVersionDiff(field=field, baseline=baseline_value, current=current_value)
)
```

- [ ] **Step 4: Verify the focused file and all existing behavior**

Run:

```bash
cd apps/api
uv --cache-dir /tmp/uv-cache run --frozen ruff check src/meterdesk_api/eval/regression.py
uv --cache-dir /tmp/uv-cache run --frozen ruff format --check src/meterdesk_api/eval/regression.py
uv --cache-dir /tmp/uv-cache run --frozen pytest tests/test_m4_eval_lab.py
```

Expected: all three commands exit 0.

- [ ] **Step 5: Commit the isolated baseline cleanup**

```bash
git add apps/api/src/meterdesk_api/eval/regression.py
git commit -m "style(api): establish clean Ruff baseline"
```

### Task 2: Add the four-job GitHub Actions contract

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: committed lockfiles, existing lint/test/build commands, `make test-db`, and the later `make container-smoke` target.
- Produces: jobs named exactly `backend-quality`, `frontend-quality`, `database-integration`, and `container-smoke`; the final job depends on the first three.

- [ ] **Step 1: Confirm the workflow acceptance surface is absent**

Run:

```bash
test -f .github/workflows/ci.yml
```

Expected: exit 1 because no workflow exists. This configuration-only task is accepted through YAML parsing and real GitHub execution rather than a source-grep unit test.

- [ ] **Step 2: Create the workflow with exact triggers, permissions, and job dependency**

Use this shape:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
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
          working-directory: apps/api
      - run: uv sync --frozen
        working-directory: apps/api
      - run: uv run --frozen ruff check .
        working-directory: apps/api
      - run: uv run --frozen ruff format --check .
        working-directory: apps/api
      - run: uv run --frozen pytest
        working-directory: apps/api
      - run: uv run --frozen python ../../scripts/check_markdown_links.py
        working-directory: apps/api

  frontend-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: apps/web/package-lock.json
      - run: npm ci
        working-directory: apps/web
      - run: npm run lint
        working-directory: apps/web
      - run: npm run typecheck
        working-directory: apps/web
      - run: npm test
        working-directory: apps/web
      - run: npm run build
        working-directory: apps/web

  database-integration:
    runs-on: ubuntu-latest
    env:
      COMPOSE_PROJECT_NAME: meterdesk-db-${{ github.run_id }}-${{ github.run_attempt }}
      POSTGRES_PORT: "55432"
      DATABASE_URL: postgresql+psycopg://meterdesk:meterdesk@localhost:55432/meterdesk
      OPENAI_API_KEY: ""
      OPENAI_MODEL: ""
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - uses: astral-sh/setup-uv@v8
        with:
          version: "0.11.16"
          enable-cache: true
          working-directory: apps/api
      - run: uv sync --frozen
        working-directory: apps/api
      - run: make test-db
      - if: always()
        run: docker compose down --volumes --remove-orphans

  container-smoke:
    needs: [backend-quality, frontend-quality, database-integration]
    runs-on: ubuntu-latest
    env:
      OPENAI_API_KEY: ""
      OPENAI_MODEL: ""
      OPENAI_BASE_URL: ""
    steps:
      - uses: actions/checkout@v6
      - run: make container-smoke
```

- [ ] **Step 3: Parse the workflow and inspect the resolved contract**

Run:

```bash
ruby -e 'require "yaml"; workflow = YAML.load_file(".github/workflows/ci.yml", aliases: true); abort "jobs missing" unless workflow.fetch("jobs").keys == %w[backend-quality frontend-quality database-integration container-smoke]'
git diff --check -- .github/workflows/ci.yml
```

Expected: both commands exit 0. Remote behavioral acceptance remains the four actual GitHub job results in Task 8.

- [ ] **Step 4: Commit the CI contract**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add locked quality and runtime gates"
```

### Task 3: Build frozen non-root API and Web images

**Files:**
- Create: `.dockerignore`
- Create: `apps/api/Dockerfile`
- Create: `apps/web/Dockerfile`
- Modify: `apps/web/next.config.ts:1-5`

**Interfaces:**
- Consumes: `README.md`, API `pyproject.toml`/`uv.lock`/source/Alembic migrations, and Web `package.json`/`package-lock.json`/Next source.
- Produces: `meterdesk-api:local` with Uvicorn, Alembic, and seed entrypoints; `meterdesk-web:local` with standalone `server.js`; both configured as `10001:10001`.

- [ ] **Step 1: Confirm real image builds fail while the image contracts are absent**

Run:

```bash
docker build --file apps/api/Dockerfile --tag meterdesk-api:local .
docker build --file apps/web/Dockerfile --tag meterdesk-web:local .
```

Expected: both fail because the Dockerfiles do not exist. Image behavior is accepted through real builds and runtime inspection, not source-text assertions.

- [ ] **Step 2: Add the root build-context exclusions**

`.dockerignore` must exclude real environment files while retaining examples, plus Git data, agent artifacts, virtual environments, caches, dependency trees, Next output, tests and test artifacts, coverage, and logs. Use anchored rules for `.env*` and recursive rules for nested artifacts:

```dockerignore
.env*
!.env.example
**/.env*
!**/.env.example
.git
.agents
.codex
.superpowers
**/.venv
**/__pycache__
**/.pytest_cache
**/.ruff_cache
**/node_modules
**/.next
**/coverage
**/*.log
**/tests
**/*.test.*
docs/archive
intv
```

- [ ] **Step 3: Add the API multi-stage image**

Use `ghcr.io/astral-sh/uv:0.11.16-python3.12-bookworm-slim` for the build stage and `python:3.12-slim-bookworm` for runtime. Install with `uv sync --frozen --no-dev --no-install-project`, copy the API source, then install the project with `uv sync --frozen --no-dev --no-editable`. Copy the resulting application tree into the runtime, create numeric UID/GID 10001, set `.venv/bin` on `PATH`, expose 8000, and run:

```dockerfile
USER 10001:10001
CMD ["uvicorn", "meterdesk_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Do not declare provider values or copy a root `.env`.

- [ ] **Step 4: Add the Web standalone image and configuration**

Set:

```typescript
const nextConfig: NextConfig = {
  output: "standalone",
};
```

Use Node 22 Bookworm Slim stages. The dependency stage runs `npm ci`; the build stage runs `npm run build`; the runtime copies `.next/standalone` and `.next/static`, creates UID/GID 10001, sets `HOSTNAME=0.0.0.0`, exposes 3000, and runs:

```dockerfile
USER 10001:10001
CMD ["node", "server.js"]
```

- [ ] **Step 5: Run real image acceptance**

Run:

```bash
docker build --file apps/api/Dockerfile --tag meterdesk-api:local .
docker build --file apps/web/Dockerfile --tag meterdesk-web:local .
test "$(docker image inspect --format '{{.Config.User}}' meterdesk-api:local)" = "10001:10001"
test "$(docker image inspect --format '{{.Config.User}}' meterdesk-web:local)" = "10001:10001"
docker run --rm --entrypoint sh meterdesk-api:local -c 'test "$(id -u)" -ne 0 && test ! -e /workspace/.env && test ! -e /app/.env'
docker run --rm --entrypoint sh meterdesk-web:local -c 'test "$(id -u)" -ne 0 && test ! -e /workspace/.env && test ! -e /app/.env'
```

Expected: every command exits 0; inspect returns exactly `10001:10001` for both images.

- [ ] **Step 6: Commit the image contract**

```bash
git add .dockerignore apps/api/Dockerfile apps/web/Dockerfile \
  apps/web/next.config.ts
git commit -m "build: add frozen non-root application images"
```

### Task 4: Add the isolated five-service Compose runtime and smoke harness

**Files:**
- Modify: `compose.yaml:1-25`
- Modify: `Makefile:1-92`
- Create: `scripts/container-smoke.sh`

**Interfaces:**
- Consumes: the two images from Task 3, existing environment names, `/health`, `/health/db`, `/tickets`, `TCK-1042`, `TCK-1137`, and the Web `/` page.
- Produces: stable `make container-build`, `container-up`, `container-seed`, `container-smoke`, and `container-down` commands.

- [ ] **Step 1: Run the real topology assertion and verify the old Compose file fails it**

Run:

```bash
test "$(docker compose config --services | paste -sd ' ' -)" = "postgres migrate seed api web"
```

Expected: exit 1 because the rendered service list is only `postgres`.

- [ ] **Step 2: Replace Compose with the five-service dependency chain**

Define one API image/build anchor and one API environment anchor. Preserve Postgres 16 Alpine, local-only default credentials, `${POSTGRES_PORT:-5432}:5432`, and `meterdesk-postgres-data`. Use these dependencies:

```yaml
migrate:
  depends_on:
    postgres:
      condition: service_healthy
  command: ["alembic", "upgrade", "head"]

seed:
  depends_on:
    migrate:
      condition: service_completed_successfully
  command: ["python", "-m", "meterdesk_api.seed"]

api:
  depends_on:
    seed:
      condition: service_completed_successfully
  healthcheck:
    test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

web:
  environment:
    API_BASE_URL: http://api:8000
  depends_on:
    api:
      condition: service_healthy
```

The API database URL is `postgresql+psycopg://meterdesk:meterdesk@postgres:5432/meterdesk` under
defaults. Key and model use empty defaults. An unset base URL preserves the application default;
the smoke path passes all three provider variables as explicitly empty values.

- [ ] **Step 3: Make every existing dependency execution frozen and add stable targets**

Change `uv sync` to `uv sync --frozen`, `npm install` to `npm ci`, and add `--frozen` to every `uv run`. Preserve all existing target names and meanings. Add:

```make
CONTAINER_WAIT_TIMEOUT ?= 180

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
```

Normal down must not include `--volumes` or `-v`.

The existing `db-up` target uses `up -d --wait --wait-timeout $(CONTAINER_WAIT_TIMEOUT) postgres`
so a cold host database reaches its existing healthcheck before Alembic starts.

- [ ] **Step 4: Implement guarded smoke lifecycle and failure preservation**

The script must use `set -Eeuo pipefail`, split `${COMPOSE:-docker compose}` into an array, generate
and validate a lowercase `meterdesk-smoke-<run>-<attempt>-<pid>` name, assign host port `0` for all
three loopback-only published ports, and use project-specific image tags. It behaviorally verifies
that a key/model-only configuration retains the application base URL. Export empty
`OPENAI_API_KEY`, `OPENAI_MODEL`, and `OPENAI_BASE_URL` for the actual smoke runtime so Compose's
automatic `.env` loading cannot inject live configuration.

The EXIT trap must:

1. capture `$?` before diagnostics;
2. print `compose ps` and the last 200 log lines only when the primary operation fails;
3. reject cleanup unless the project still begins with `meterdesk-smoke-`;
4. run `down --volumes --remove-orphans` only for that project;
5. return the primary failure when both primary work and cleanup fail;
6. return the cleanup failure only when primary work succeeded.

After `compose build api web` and `compose up -d --wait`, resolve ephemeral host ports with `compose port`, use bounded curl retries, and assert:

- `/health` says `status=ok`;
- `/health/db` says `database=reachable`;
- `/tickets` contains `TCK-1042` and `TCK-1137`;
- `/` contains `MeterDesk`, `TCK-1042`, and `TCK-1137`;
- API environment contains no provider key or model;
- the key/model-only Compose contract retains `https://api.openai.com/v1`, while the actual no-key
  runtime retains an explicitly empty base URL;
- all three ephemeral publications resolve on `127.0.0.1`;
- POST `/tickets/TCK-1042/agent-runs` returns 503 with the existing missing-provider message;
- both image config users equal `10001:10001`.

- [ ] **Step 5: Verify the rendered Compose contract**

Run:

```bash
docker compose config --services
```

Expected service output, one per line: `postgres`, `migrate`, `seed`, `api`, `web`. Do not print `docker compose config` without `--services` because a local `.env` may contain secrets.

- [ ] **Step 6: Run the real build and isolated smoke path**

```bash
make container-build
make container-smoke
```

Expected: both exit 0; smoke reports both tickets, visible Web content, a 503 missing-provider response, non-root users, and successful project-scoped cleanup.

- [ ] **Step 7: Prove the default volume is not a cleanup target**

Before and after smoke, record only volume names:

```bash
docker volume ls --format '{{.Name}}' | sort
```

Expected: the existing default MeterDesk volume name remains after smoke. Do not run default-project `docker compose down --volumes`.

- [ ] **Step 8: Commit the runtime surface**

```bash
git add compose.yaml Makefile scripts/container-smoke.sh
git commit -m "feat(runtime): add isolated seeded Compose smoke path"
```

### Task 5: Add the container runbook and deterministic local-link check

**Files:**
- Create: `scripts/check_markdown_links.py`
- Create: `apps/api/tests/test_markdown_links.py`
- Create: `docs/runbooks/container-demo.md`
- Modify: `README.md:84-147`
- Modify: `docs/README.md`

**Interfaces:**
- Consumes: the exact Make targets and Compose behavior from Task 4.
- Produces: a host-development path that remains unchanged, a separate seeded-container path, and a checker that exits non-zero for a missing local Markdown target.

- [ ] **Step 1: Write behavioral tests for valid and missing local targets**

Each test writes a temporary Markdown file tree, invokes the checker as a subprocess with explicit file arguments, and asserts exit status plus diagnostics. The missing-target test must fail before the checker exists; the valid-target test must assert an exit 0 summary. No test may inspect the checker source text.

- [ ] **Step 2: Run the focused test and observe the missing checker failure**

```bash
cd apps/api
uv --cache-dir /tmp/uv-cache run --frozen pytest tests/test_markdown_links.py -v
```

Expected: fail because `scripts/check_markdown_links.py` does not exist.

- [ ] **Step 3: Implement the local-link checker**

Use Python standard library only. Scan tracked current Markdown files under `README.md`, `AGENTS.md`, and `docs/`, excluding `docs/archive/`; ignore `http`, `https`, `mailto`, and fragment-only targets; strip query/fragment components; URL-decode paths; resolve relative paths against the containing Markdown file; and report every missing target before exiting 1. Exit 0 with a checked-file/link count otherwise.

- [ ] **Step 4: Add the README link before the runbook and verify failure**

Add `[Container Demo Runbook](docs/runbooks/container-demo.md)` to README, then run:

```bash
python3 scripts/check_markdown_links.py
```

Expected: exit 1 naming only the not-yet-created runbook target.

- [ ] **Step 5: Write the complete container quick start and runbook**

README keeps `cp .env.example .env`, `make install`, `make db-up`, and `make dev` intact. Add a separate seeded-container sequence:

```bash
make container-build
make container-up
make container-smoke
make container-down
```

The runbook must state prerequisites, default URLs, `container-seed` reset semantics, Compose project/volume behavior, no-key seeded replay versus explicit live-provider execution, `/health` and `/health/db`, safe log commands, normal cleanup, separately labeled destructive volume removal, port overrides, local-only database credentials, mock-only financial mutations, draft-only customer replies, and common build/health/port failures.

- [ ] **Step 6: Run tests, links, and command/document parity checks**

```bash
python3 scripts/check_markdown_links.py
cd apps/api && uv --cache-dir /tmp/uv-cache run --frozen pytest tests/test_markdown_links.py -v && cd ../..
rg -n "container-(build|up|seed|smoke|down)" README.md docs/runbooks/container-demo.md Makefile
```

Expected: checker exits 0; all five targets appear in Make and the runbook, and the quick-start targets appear in README.

- [ ] **Step 7: Commit operational documentation and the plan**

```bash
git add README.md docs/README.md docs/runbooks/container-demo.md scripts/check_markdown_links.py \
  apps/api/tests/test_markdown_links.py \
  docs/superpowers/plans/2026-07-31-meterdesk-p0-01-ci-runtime-baseline.md
git commit -m "docs: add seeded container demo runbook"
```

### Task 6: Synchronize current specs and local evidence

**Files:**
- Modify: `docs/specs/system-architecture.md`
- Modify: `docs/specs/implementation-roadmap.md`
- Modify: `docs/specs/hardening/roadmap.md`
- Modify: `docs/specs/hardening/p0-01-ci-runtime-baseline.md`
- Modify: `docs/evidence/engineering-evidence-matrix.md`

**Interfaces:**
- Consumes: actual files and successful local commands from Tasks 1-5.
- Produces: current runtime architecture and evidence statements that distinguish local verification from pending remote CI.

- [ ] **Step 1: Record only the affected architecture and roadmap changes**

Add the current five-service topology and non-root image boundary to System Architecture. Update Implementation Roadmap and Hardening Roadmap so P0-01 is implemented locally and awaiting or holding named CI evidence. Do not edit Product Scope, Agent Governance, or Eval Strategy because this workstream intentionally changes none of those contracts.

- [ ] **Step 2: Update the focused P0-01 status and artifact list**

Replace “implementation not started” language with exact implementation artifacts, local command results, CI state, and limitations. Keep remote CI described as pending until a real GitHub run succeeds.

- [ ] **Step 3: Promote only locally executed evidence rows**

After successful local runs, the API image, Web image, seeded full-stack runtime, and no-key smoke rows may become `Verified` with exact commands and image/service artifacts. Keep all four GitHub job rows `Planned` until their actual PR run succeeds. Record the current test counts and Docker/Compose versions without treating them as product performance claims.

- [ ] **Step 4: Verify documentation consistency and working-tree hygiene**

```bash
python3 scripts/check_markdown_links.py
rg -n "implementation not started|No workflow|No Dockerfile|Compose starts only Postgres" \
  README.md docs/specs docs/evidence --glob '!docs/archive/**'
git diff --check
git status --short
```

Expected: link check and diff check exit 0; the search returns no stale current-state claim; status lists only P0-01 files and never an `intv/` path.

- [ ] **Step 5: Commit local spec and evidence synchronization**

```bash
git add docs/specs/system-architecture.md docs/specs/implementation-roadmap.md \
  docs/specs/hardening/roadmap.md docs/specs/hardening/p0-01-ci-runtime-baseline.md \
  docs/evidence/engineering-evidence-matrix.md
git commit -m "docs: record P0-01 runtime evidence"
```

### Task 7: Run full verification and independent review

**Files:**
- Modify only files required to resolve verified P0-01 review findings.

**Interfaces:**
- Consumes: the complete candidate branch.
- Produces: a locally verified and independently reviewed PR candidate with no Critical or Important findings.

- [ ] **Step 1: Check the active goal at the verification boundary**

Call `get_goal` and confirm the P0-01 objective remains active.

- [ ] **Step 2: Invoke verification and debugging workflows**

Read and follow `superpowers:verification-before-completion`. If any command fails, read and follow `superpowers:systematic-debugging` before editing; preserve the acceptance threshold.

- [ ] **Step 3: Run the full host quality contract**

```bash
env "PATH=/home/poter/.nvm/versions/node/v22.22.2/bin:$PATH" \
  TEMP=/tmp TMP=/tmp TMPDIR=/tmp make lint
env "PATH=/home/poter/.nvm/versions/node/v22.22.2/bin:$PATH" \
  TEMP=/tmp TMP=/tmp TMPDIR=/tmp make test
env "PATH=/home/poter/.nvm/versions/node/v22.22.2/bin:$PATH" \
  TEMP=/tmp TMP=/tmp TMPDIR=/tmp make test-db
```

Expected: all exit 0. Record Ruff/format results, API pass/skip counts, Web pass count, and the database integration success message.

- [ ] **Step 4: Run the complete container acceptance contract**

```bash
make container-build
make container-smoke
test "$(docker image inspect --format '{{.Config.User}}' meterdesk-api:local)" = "10001:10001"
test "$(docker image inspect --format '{{.Config.User}}' meterdesk-web:local)" = "10001:10001"
docker run --rm --entrypoint sh meterdesk-api:local -c 'test "$(id -u)" -ne 0 && test -z "${OPENAI_API_KEY:-}"'
docker run --rm --entrypoint sh meterdesk-web:local -c 'test "$(id -u)" -ne 0'
```

Expected: all exit 0. The smoke output must include the missing-provider 503 assertion and successful project-scoped cleanup.

- [ ] **Step 5: Run documentation and Git hygiene checks**

```bash
python3 scripts/check_markdown_links.py
git diff --check origin/main...HEAD
git status --short
```

Expected: links and diff check exit 0; status is clean after committed changes.

- [ ] **Step 6: Dispatch an independent read-only reviewer**

Read and follow `superpowers:requesting-code-review`. Give the reviewer `origin/main...HEAD`, the active P0-01 spec, this plan, and explicit checks for scope drift, secret exposure, default-volume deletion, cleanup failure masking, lockfile regeneration, root runtime users, and CI dependency/cleanup correctness.

- [ ] **Step 7: Resolve all Critical and Important findings**

Verify every finding against current code. Apply focused fixes, add or strengthen the relevant test, and ask the reviewer to re-check changed areas. Record lower-severity limitations rather than silently broadening scope.

- [ ] **Step 8: Re-run Steps 3-5 after the final review fix**

All commands must succeed on the reviewed tree before publication.

### Task 8: Publish, verify GitHub Actions, finalize evidence, and merge

**Files:**
- Modify: `docs/specs/hardening/p0-01-ci-runtime-baseline.md` only if the final CI result changes its recorded evidence.
- Modify: `docs/evidence/engineering-evidence-matrix.md` to promote the four CI rows after actual success.

**Interfaces:**
- Consumes: reviewed local commits and GitHub repository `ZophiaWong/meter-desk`.
- Produces: a ready PR, four successful checks on the final PR head, one ruleset-compatible squash merge, and a fetched `origin/main` tree identical to the verified implementation.

- [ ] **Step 1: Check the goal and synchronize the base**

Call `get_goal`, then run:

```bash
git fetch origin main
git status --short
git rebase origin/main
```

Expected: worktree clean; rebase succeeds. If new upstream changes alter paths, commands, migrations, services, or specs, stop and refresh the affected plan section before continuing.

- [ ] **Step 2: Run final verification on the synchronized tree**

Repeat Task 7 Steps 3-5. Capture the verified branch tip with `git rev-parse HEAD`.

- [ ] **Step 3: Push the feature branch and create a ready-for-review PR**

Push `hardening/p0-01-ci-runtime-baseline` without deleting or rewriting any user branch. Create a non-draft PR whose body includes scope, behavior-neutral design boundaries, every actual local result, no-key/non-root checks, evidence state, and remaining limitations.

- [ ] **Step 4: Wait for and inspect all four GitHub jobs**

Use the GitHub checks interface or `gh pr checks --watch`. Require successful conclusions for:

```text
backend-quality
frontend-quality
database-integration
container-smoke
```

If a job fails, inspect its logs, use systematic debugging, fix the root cause, rerun local verification, push, and wait again.

- [ ] **Step 5: Promote remote CI evidence after the first real successful run**

Update the focused spec and evidence matrix with the PR URL, workflow name, exact job names, successful conclusion, and run date. Change the four CI rows from `Planned` to `Verified`; do not alter unrelated `Gap`, `Existing`, or `Deferred` rows. Commit:

```bash
git add docs/specs/hardening/p0-01-ci-runtime-baseline.md \
  docs/evidence/engineering-evidence-matrix.md
git commit -m "docs: promote verified P0-01 CI evidence"
git push origin hardening/p0-01-ci-runtime-baseline
```

- [ ] **Step 6: Require all four jobs on the evidence-finalized PR head**

Wait again and verify that the same four jobs succeed on the new head. Re-run `git diff --check` and the Markdown link checker locally against that head.

- [ ] **Step 7: Squash merge without deleting either feature-branch reference**

Use squash merge because the CI-evidence promotion is a second reviewable commit. Supply one detailed final subject/body covering CI, images, runtime, smoke safety, docs, evidence, tests, and behavior-neutral boundaries. Do not request branch deletion.

- [ ] **Step 8: Verify the merged remote tree**

```bash
git fetch origin main
git rev-parse origin/main
git diff --exit-code HEAD origin/main -- .
git status --short
```

Expected: `origin/main` is the merged SHA, the tree diff is empty, and the local worktree is clean. Confirm the PR reports merged and the remote feature branch still exists.

- [ ] **Step 9: Re-review the next workstream assumptions**

Report the exact P0-01 Make targets, Compose services, CI commands, Docker runtime paths, and any remaining limitations that P0-02 and P1-04 must re-read before planning.

- [ ] **Step 10: Complete the goal only after every terminal condition holds**

Call `update_goal(status="complete")` only after the PR is merged, `origin/main` is fetched and tree-equivalent, all required local commands succeeded, all four final-head GitHub jobs succeeded, review findings are resolved, and evidence is honest. The final report must include branch, feature commit SHA, PR URL, remote main SHA, every verification result, evidence changes, unresolved limitations, and the downstream re-review reminder.

## Failure Handling Matrix

| Failure | Required response |
|---|---|
| Ruff reports anything outside the five confirmed findings before implementation | Stop and classify it as baseline drift before changing code. |
| Lockfile/manifests disagree | Keep the install failing; reconcile only through an explicit dependency decision, never automatic lock regeneration. |
| Docker socket is denied inside the sandbox | Request scoped Docker escalation and retry the same acceptance command. |
| Migration or seed fails | Stop API/Web startup, retain the primary exit code, and print project-scoped service state/logs. |
| Provider key is absent | Seeded reads and Web render stay available; live run returns the existing 503 response. |
| Provider key exists in local `.env` during smoke | Script-level empty exports override it; never print Compose config or the value. |
| Smoke cleanup fails after an earlier failure | Report cleanup separately and return the earlier failure code. |
| Smoke cleanup target lacks the guarded prefix | Refuse volume cleanup and fail safely. |
| Default host port is occupied | Normal Compose reports the collision; smoke remains isolated through ephemeral host ports. |
| Any runtime user is root | Fail image acceptance and container-smoke; do not waive the check. |
| A GitHub job fails | Inspect logs, reproduce locally where possible, fix root cause, and require a new successful final-head run. |
| Upstream changes invalidate paths/contracts | Refresh the affected plan and rerun dependent verification before publication. |

## Commit and Evidence Boundaries

1. Ruff cleanup: behavior-neutral baseline only.
2. CI workflow and its deterministic contract test.
3. Dockerfiles, standalone Web configuration, `.dockerignore`, and image assertions.
4. Compose, Make targets, smoke harness, and cleanup/isolation assertions.
5. README, runbook, documentation index, and link checker.
6. Foundational runtime/spec synchronization and locally verified evidence.
7. Review fixes, grouped by root cause with their regression test.
8. Remote CI evidence promotion after an actual successful PR run.
9. GitHub squash merge produces one detailed `main` commit while retaining both local and remote feature branches.

The first six boundaries may be separate feature commits for reviewability. The final merge is a single squash because the remote CI evidence boundary necessarily follows the first pushed CI run.
