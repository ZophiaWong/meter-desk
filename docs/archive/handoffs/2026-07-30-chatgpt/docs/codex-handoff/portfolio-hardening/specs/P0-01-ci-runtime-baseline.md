# P0-01: CI and Runtime Baseline

## 1. Status

- Priority: P0
- Detailed design status: Ready for implementation
- Depends on: current `main`
- Blocks: P0-02, P1-04, P0-03, P0-04 and all later hardening work
- Product behavior change: No intended domain behavior change

## 2. Problem

MeterDesk 当前具备本地开发命令，但缺少可公开验证的自动化 build/runtime contract。

静态审阅确认：

- `Makefile` 已提供 backend/frontend install、test、lint、seed 和 DB integration commands；
- `compose.yaml` 只定义 Postgres；
- 未找到 API Dockerfile；
- 未找到 Web Dockerfile；
- 未找到 `.github/workflows`；
- README 只说明 host-based local startup；
- `db_integration_check.py` 可以在没有 provider 配置时验证 seeded resource APIs；
- Web server-side code通过 `API_BASE_URL` 访问 FastAPI。

因此 reviewer 目前无法从仓库直接确认：

- PR 是否自动验证；
- backend/frontend lockfiles 是否可重复安装；
- production builds 是否成功；
- schema migration 和 seed 是否可重复；
- API/Web 是否能在容器网络中通信；
- 无 LLM key 时是否仍能启动 seeded demo；
- fresh environment 是否能完成 smoke test。

## 3. User and Business Impact

### Portfolio reviewer

需要手动安装 Node、Python、uv、Docker，再运行多个命令；任何本地差异都会降低验证意愿。

### Maintainer

后续 auth、state、worker 和 persistence 重构缺少统一 required checks，回归可能在合并后才发现。

### Codex

没有稳定 verification contract，容易只运行局部测试并错误声称完成。

### Future deployment work

没有可用 image 和 compose topology，deployment/observability work 没有稳定边界。

## 4. Goal

建立以下可重复验证能力：

1. backend lint and unit tests；
2. frontend lint, typecheck, unit tests and production build；
3. Postgres migration, seed and integration check；
4. API production container image；
5. Web production container image；
6. seeded full-stack Compose runtime；
7. CI full-stack smoke test；
8. 所有 CI 路径都不依赖真实 LLM key。

## 5. Non-goals

本 workstream 不实现：

- cloud hosting
- container registry push
- deployment workflow
- Kubernetes
- authentication/RBAC
- worker/queue
- OpenTelemetry
- provider resilience redesign
- real external integration
- real payment mutation
- Usage Spike runner
- UI redesign
- database engine lifecycle refactor

Database engine lifecycle 保留给 P1-04。P0-01 只容器化和验证当前行为。

## 6. Current Behavior

### 6.1 Make interface

当前 root `Makefile`：

- `make install-api` -> `uv sync`
- `make install-web` -> `npm install`
- `make test-api` -> `pytest`
- `make test-web` -> `npm test`
- `make lint-api` -> Ruff check and format check
- `make lint-web` -> ESLint and TypeScript
- `make test-db` -> Postgres + migration + seed + integration checker
- `make dev` -> host FastAPI + host Next.js

### 6.2 Compose

当前只运行 `postgres:16-alpine`，带 healthcheck 和 persistent volume。

### 6.3 API runtime

FastAPI command：

```text
uvicorn meterdesk_api.main:app --host 0.0.0.0 --port 8000
```

Readiness endpoints：

```text
GET /health
GET /health/db
```

### 6.4 Web runtime

Next scripts：

```text
npm run build
npm run start
```

Web server side读取：

```text
API_BASE_URL
```

容器内必须指向：

```text
http://api:8000
```

而不是 `http://localhost:8000`。

### 6.5 Seeded integration check

`db_integration_check.py` 验证：

- ticket list
- Duplicate Charge evidence
- Credit/Refund evidence
- seeded approvals
- seeded runs
- 9 eval cases
- missing provider write path

CI 可以使用该 checker，不需要真实 provider key。

## 7. Target Architecture

```text
Developer / GitHub Actions
        |
        v
Docker Compose
  ├── postgres   long-running, healthchecked
  ├── migrate    one-shot, API image
  ├── seed       one-shot, API image
  ├── api        long-running, healthchecked
  └── web        long-running, production Next server
```

### 7.1 API image

Responsibilities:

- install locked production dependencies;
- include migrations and application source;
- run as non-root user;
- expose port 8000;
- start Uvicorn;
- contain no API key;
- support alternate commands for migration and seed.

Build context must be repository root because API package metadata references root README and the image needs
both root and `apps/api` files.

Pinned runtime choices:

- Python 3.12 slim image
- uv 0.11.16
- no dev dependencies in final runtime
- no `latest` tags

### 7.2 Web image

Responsibilities:

- install via `npm ci`;
- execute `npm run build`;
- run production Next server;
- run as non-root user;
- expose port 3000;
- use `API_BASE_URL=http://api:8000` at runtime.

Use Next standalone output to avoid copying the complete development dependency tree into runtime image.

Pinned runtime choices:

- Node 22 Alpine
- lockfile-required installation
- no `latest` tags

### 7.3 Compose behavior

`compose.yaml` must:

- preserve existing Postgres service and volume;
- add API image anchor or reusable build definition;
- add one-shot `migrate`;
- add one-shot `seed`;
- add `api`;
- add `web`;
- use internal Postgres hostname `postgres`;
- use internal API hostname `api`;
- expose host ports through existing variables;
- define healthchecks;
- never inject `OPENAI_API_KEY` by default;
- allow local `.env` override without baking secrets into images.

### 7.4 Make interface

Add stable targets:

```text
make container-build
make container-up
make container-seed
make container-smoke
make container-down
```

Semantics:

- `container-build`: build API and Web images.
- `container-up`: start Postgres, run migration, run seed, then start API and Web.
- `container-seed`: rerun migration and idempotent seed using API image.
- `container-smoke`: start from clean volumes, run full seeded stack, verify endpoints, print useful logs on failure,
  then clean up.
- `container-down`: stop services; support volume cleanup through documented explicit command.

Existing `make dev`, `make test`, `make test-db` and `make lint` must remain compatible.

### 7.5 CI topology

Create one workflow:

```text
.github/workflows/ci.yml
```

Triggers:

- pull_request
- push to main
- manual workflow_dispatch

Permissions:

```text
contents: read
```

Concurrency:

- one active run per branch/PR;
- cancel older in-progress run.

Jobs:

#### backend-quality

- checkout
- Python 3.12
- uv 0.11.16
- `uv sync --frozen`
- Ruff check
- Ruff format check
- pytest

#### frontend-quality

- checkout
- Node 22
- `npm ci`
- ESLint
- typecheck
- Vitest
- production build

#### database-integration

- checkout
- Python/uv
- Docker Compose available
- `make test-db`
- always run `docker compose down -v`

#### container-smoke

Depends on all quality jobs.

- checkout
- `make container-smoke`
- no provider secret
- upload or print service logs on failure

Current action major versions selected for the plan:

```text
actions/checkout@v6
actions/setup-python@v6
actions/setup-node@v6
astral-sh/setup-uv@v8
```

## 8. Interfaces

### 8.1 Environment variables

Existing names remain authoritative:

```text
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_DB
POSTGRES_PORT
DATABASE_URL
API_HOST
API_PORT
FRONTEND_ORIGIN
WEB_PORT
API_BASE_URL
OPENAI_API_KEY
OPENAI_MODEL
OPENAI_BASE_URL
```

Compose service defaults:

```text
DATABASE_URL=postgresql+psycopg://meterdesk:meterdesk@postgres:5432/meterdesk
API_BASE_URL=http://api:8000
FRONTEND_ORIGIN=http://localhost:${WEB_PORT:-3000}
```

`OPENAI_API_KEY` and `OPENAI_MODEL` remain unset in CI smoke.

### 8.2 Health contract

API liveness:

```text
GET /health
200
{"service":"meterdesk-api","status":"ok",...}
```

Database readiness:

```text
GET /health/db
200
{"service":"meterdesk-api","status":"ok","database":"reachable"}
```

Web smoke:

```text
GET /
200
body contains "MeterDesk"
```

Seeded resource smoke:

```text
GET /tickets
200
contains TCK-1042 and TCK-1137
```

### 8.3 Image commands

API default command:

```text
uvicorn meterdesk_api.main:app --host 0.0.0.0 --port 8000
```

Migration command:

```text
alembic upgrade head
```

Seed command:

```text
python -m meterdesk_api.seed
```

## 9. Failure Semantics

| Failure | Required behavior |
|---|---|
| lockfile and manifests disagree | CI/install fails; do not regenerate lockfile silently |
| migration fails | API/Web smoke does not proceed |
| seed fails | smoke fails and prints migrate/seed logs |
| Postgres unhealthy | dependent step times out and fails |
| API liveness fails | smoke fails and prints API logs |
| DB readiness fails | smoke fails and prints API/Postgres logs |
| Web cannot reach API | homepage smoke must fail or assert degraded state is not acceptable for seeded stack |
| real provider missing | seeded runtime remains available; live run endpoint may retain current missing-provider behavior |
| cleanup command fails | CI still preserves primary failure and prints cleanup error |
| host port occupied | local command reports Compose error; CI uses isolated runner |
| container process runs as root | acceptance fails |
| secret copied into image | acceptance fails |

## 10. Security Requirements

- Images must not copy `.env`.
- `.dockerignore` must exclude secrets, local virtualenvs, node_modules, `.git`, test artifacts and build output.
- Runtime containers must use non-root users.
- CI permissions must be `contents: read`.
- CI must not receive OpenAI or payment secrets.
- Demo Postgres credentials must be clearly documented as local-only.
- Build must use committed lockfiles.
- No financial mutation behavior may be changed.
- No live provider call may occur in smoke tests.

## 11. Observability Requirements

P0-01 不引入 OpenTelemetry，但 failure output 必须可诊断：

- smoke script在失败时打印 `docker compose ps`;
- 打印 Postgres/API/Web logs；
- CI job显示具体失败 endpoint；
- container logs使用 stdout/stderr；
- 不吞掉 migration/seed exit code。

## 12. Migration and Compatibility

- 不新增 database migration。
- 现有 Alembic head 必须在 container migration job 中运行。
- 现有 seed 数据必须保持。
- 现有 host-based development commands 必须保持。
- 现有 `.env.example` 变量名称必须保持。
- Compose service additions不能改变本地 Postgres default port 和 volume semantics。
- README 应同时保留 host-based 和 container-based workflows。

## 13. Testing Requirements

### 13.1 Backend quality

```text
make lint-api
make test-api
```

### 13.2 Frontend quality

```text
make lint-web
make test-web
cd apps/web && npm run build
```

### 13.3 Database integration

```text
make test-db
```

### 13.4 Image build

```text
docker build -f apps/api/Dockerfile .
docker build -f apps/web/Dockerfile .
```

或通过：

```text
make container-build
```

### 13.5 Full-stack smoke

从 clean volume 开始验证：

1. Postgres healthy；
2. migration success；
3. seed success；
4. API liveness；
5. API DB readiness；
6. `/tickets` 有 seeded records；
7. Web homepage 200；
8. homepage包含 MeterDesk；
9. 不配置 provider key；
10. cleanup 成功。

## 14. Documentation Changes

Update:

- root `README.md`
- `Makefile` help
- `.env.example` comments only when required
- create `docs/runbooks/container-demo.md`
- this evidence matrix after implementation

README 应明确区分：

```text
Host development
Containerized seeded demo
Live provider path
```

## 15. Acceptance Criteria

- [ ] `.github/workflows/ci.yml` 存在。
- [ ] backend quality job运行 Ruff 和 pytest。
- [ ] frontend quality job运行 ESLint、typecheck、Vitest 和 production build。
- [ ] database integration job运行 migration、seed 和 DB checker。
- [ ] container smoke job在 clean volume 中启动 seeded stack。
- [ ] CI 不需要 `OPENAI_API_KEY`。
- [ ] `apps/api/Dockerfile` 存在并使用 pinned Python/uv versions。
- [ ] API runtime image不包含 dev dependencies。
- [ ] API runtime process使用 non-root user。
- [ ] `apps/web/Dockerfile` 存在并使用 Node 22。
- [ ] Web build使用 `npm ci`。
- [ ] Web runtime process使用 non-root user。
- [ ] `compose.yaml` 定义 postgres、migrate、seed、api 和 web。
- [ ] `API_BASE_URL` 在 Web container 中指向 `http://api:8000`。
- [ ] API container通过内部 hostname访问 Postgres。
- [ ] `make container-build` 成功。
- [ ] `make container-up` 启动 seeded demo。
- [ ] `make container-seed` 可重复运行。
- [ ] `make container-smoke` 验证 API、DB、seeded tickets 和 Web。
- [ ] smoke failure打印 service logs。
- [ ] smoke 无论成功失败都清理 CI resources。
- [ ] existing `make dev`、`make test`、`make test-db`、`make lint` 语义保持。
- [ ] README 和 runbook 已更新。
- [ ] 没有修改 Agent decision、approval、mutation 或 eval semantics。
- [ ] Codex 返回所有 verification commands 的实际结果。

## 16. Verification Commands

```bash
make lint
make test
make test-db
make container-build
make container-smoke
git diff --check
git status --short
```

在 CI workflow 本身完成后，还必须确认 GitHub Actions 中四个 jobs 均成功：

```text
backend-quality
frontend-quality
database-integration
container-smoke
```

## 17. Completion Evidence

Codex 完成时必须返回：

1. created/modified files；
2. exact image base tags；
3. exact GitHub Action major tags；
4. new Make targets；
5. `docker compose config` result；
6. `make lint` result；
7. `make test` result；
8. `make test-db` result；
9. `make container-build` result；
10. `make container-smoke` result；
11. smoke endpoint results；
12. confirmation that no provider secret was used；
13. image process users；
14. deviations from this spec；
15. remaining limitations。

## 18. Source Files Reviewed

- `AGENTS.md`
- `README.md`
- `Makefile`
- `compose.yaml`
- `.env.example`
- `apps/api/pyproject.toml`
- `apps/api/src/meterdesk_api/main.py`
- `apps/api/src/meterdesk_api/settings.py`
- `apps/api/src/meterdesk_api/routers/health.py`
- `apps/api/src/meterdesk_api/db_integration_check.py`
- `apps/web/package.json`
- `apps/web/next.config.ts`
- `apps/web/src/app/page.tsx`
- `apps/web/src/lib/status.ts`
- `docs/specs/system-architecture.md`
- `docs/specs/agent-governance.md`
- `docs/specs/eval-strategy.md`
