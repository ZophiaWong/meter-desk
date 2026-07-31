# P0-01 CI and Runtime Baseline

## Status

- Priority: P0.
- Design status: approved; runtime architecture implementation is Implemented on the candidate
  branch.
- Evidence status: API/Web images, seeded runtime, no-provider smoke behavior, and Markdown links
  are locally Verified; final branch-wide quality/database verification is in progress. Remote CI
  verification is pending and all four GitHub jobs remain Planned because no remote run has yet
  occurred.
- Depends on: post-M10 baseline commit `86c737d` and the P0-01 candidate commits.
- Blocks: every later hardening workstream.
- Intended product behavior change: none.

The current implementation plan is
`docs/superpowers/plans/2026-07-31-meterdesk-p0-01-ci-runtime-baseline.md`. Historical plans under
`docs/archive/` remain stale and non-authoritative.

## Problem

The starting repository had local install, lint, test, database, seed, reset, and development
commands but no publicly repeatable build/runtime contract. P0-01 adds that contract without moving
application authority: locked installs, production images, migrations, seed, API/Web networking,
and no-provider-key behavior now share one repository-local command surface. The remaining problem
is evidence closure: no real remote workflow run exists yet, and final candidate-branch
`make lint`, `make test`, and `make test-db` results are not yet available.

## Implementation and Evidence Snapshot

The following evidence was collected locally on 2026-07-31 and 2026-08-01. Counts and tool versions
describe those executions only; they are not performance, availability, or production-readiness
claims.

- The recorded pre-implementation full test snapshot was API `68 passed, 6 skipped` and Web
  `21 passed` under Node 22.22.2. It is not a final candidate-branch `make test` result.
- The five allowed Ruff findings in `apps/api/src/meterdesk_api/eval/regression.py` were fixed;
  focused Ruff check/format and `15` Eval Lab tests passed. A subsequent root format check exposed
  pre-existing drift in `apps/api/src/meterdesk_api/repositories.py`,
  `apps/api/src/meterdesk_api/seed_data.py`, and `apps/api/tests/test_m4_eval_lab.py`. Maintainer
  direction is pending, so backend quality and final `make lint` remain unverified.
- The Markdown checker has `9` focused passing tests. A full current-doc run reported
  `Checked 15 Markdown file(s), 53 local link(s).`
- Real API and Web image builds succeeded. `meterdesk-api:local` runs from
  `/workspace/apps/api`; `meterdesk-web:local` runs from `/app`; both image configs use
  `10001:10001`.
- Multiple unique-project `make container-smoke` runs succeeded, including projects ending in
  `372842`, `379294`, and `388927`. They verified API health, database reachability, seeded
  `TCK-1042` and `TCK-1137`, Web content, empty provider configuration, expected HTTP 503 on a live
  run without a provider, exact non-root image users, project cleanup, and preservation of the
  default `meter-desk_meterdesk-postgres-data` volume.
- The current local runtime snapshot is Docker Engine client/server `28.1.1` and Docker Compose
  `v2.35.1-desktop.1`.
- No final candidate-branch passing result is recorded for `make test` or `make test-db`. No GitHub
  Actions job has a real remote result yet.

P0-01 must establish a clean quality baseline. The narrow Ruff cleanup belongs in this workstream
because new CI would otherwise fail immediately, but it must not change eval or domain behavior.

## Goal

Create one reproducible verification surface that provides:

1. backend lint and tests;
2. frontend lint, typecheck, tests, and production build;
3. Postgres migration, seed, and integration checks;
4. locked non-root API and Web runtime images;
5. a seeded full-stack Compose runtime;
6. a cleanup-safe, no-provider-key smoke harness;
7. concise host and container runbooks;
8. actual CI and local verification evidence.

## Implemented Artifacts and Interfaces

- `.github/workflows/ci.yml`: read-only `backend-quality`, `frontend-quality`,
  `database-integration`, and dependency-gated `container-smoke` jobs.
- `.dockerignore`, `apps/api/Dockerfile`, `apps/web/Dockerfile`, and
  `apps/web/next.config.ts`: frozen production builds and standalone runtimes.
- `compose.yaml`: `postgres`, `migrate`, `seed`, `api`, and `web` with health/completion ordering,
  internal `postgres:5432` and `http://api:8000` interfaces, and a persistent named Postgres volume.
- `Makefile`: frozen host dependency commands plus `container-build`, `container-up`,
  `container-seed`, `container-smoke`, and volume-preserving `container-down`.
- `scripts/container-smoke.sh`: unique-project, ephemeral-port, no-provider smoke and guarded
  cleanup.
- `README.md`, `docs/runbooks/container-demo.md`, `scripts/check_markdown_links.py`, and
  `apps/api/tests/test_markdown_links.py`: host/container guidance and current-document link checks.

## Non-Goals

P0-01 does not add cloud hosting, registry publishing, deployment automation, Kubernetes,
authentication/RBAC, worker/queue execution, OpenTelemetry, provider resilience, real integrations,
real payment mutations, Usage Spike execution, UI redesign, or database lifecycle refactoring.

It must not change planning, deterministic decision authority, approval behavior, mutation
idempotency, governance enforcement, trace scoring, eval semantics, seeded scenario expectations, or
the draft-only customer reply boundary.

## Implemented Runtime

```text
Developer or GitHub Actions
        |
        v
Docker Compose project
  +-- postgres   long-running, healthchecked
  +-- migrate    one-shot, API image
  +-- seed       one-shot, API image
  +-- api        long-running, healthchecked
  +-- web        long-running, production Next server
```

### API Image

- Build from the repository root so root README/package metadata and API sources are available.
- Install from committed `apps/api/uv.lock` without silently regenerating it.
- Include application source, Alembic configuration, and migrations.
- Exclude development-only dependencies from the final image.
- Run Uvicorn as a non-root user on port 8000.
- Support alternate migration and seed commands using the same image.

### Web Image

- Install from committed `apps/web/package-lock.json` with `npm ci`.
- Build Next.js standalone output and run the production server as a non-root user on port 3000.
- Resolve the server-side backend through runtime `API_BASE_URL=http://api:8000`.

### Compose Isolation

- Preserve Postgres 16, the existing default credentials, host port behavior, and persistent volume
  semantics for normal local development.
- Remove the fixed Postgres `container_name`; every service must use Compose-generated names scoped
  by `COMPOSE_PROJECT_NAME`.
- Reuse one explicit API image contract for migration, seed, and API services.
- Use internal hostnames `postgres:5432` and `http://api:8000`.
- Never inject an OpenAI key by default; `.env` may supply one for explicit live use without baking
  it into an image.

### Command Surface

Add stable root targets:

```text
make container-build
make container-up
make container-seed
make container-smoke
make container-down
```

Existing host commands must retain their current meaning. Volume destruction must remain an explicit
documented command rather than an implicit part of normal `container-down`.

## CI Contract

`.github/workflows/ci.yml` implements one pull-request, main-push, and manually dispatchable
workflow with read-only repository permissions and per-ref concurrency cancellation.

Required jobs:

- `backend-quality`: Python 3.12, frozen uv install, Ruff check/format check, pytest.
- `frontend-quality`: Node 22, `npm ci`, ESLint, TypeScript, Vitest, production build.
- `database-integration`: migration, seed, and Postgres-backed checker with unconditional cleanup.
- `container-smoke`: depends on the other jobs and runs the full clean seeded stack.

The backend job runs frozen Ruff check, Ruff format check, pytest, and the Markdown link checker.
The frontend job runs `npm ci`, ESLint, TypeScript, Vitest, and the production build. The database
job runs frozen installation and `make test-db`, with unconditional project-volume cleanup. The
container job passes all three provider variables as empty and runs `make container-smoke` only
after the other jobs succeed.

Pinned workflow interfaces are `actions/checkout@v6`, `actions/setup-python@v6`,
`actions/setup-node@v6`, `astral-sh/setup-uv@v8`, Python 3.12, Node 22, and uv `0.11.16`.

CI and smoke runs must not receive or require `OPENAI_API_KEY`, `OPENAI_MODEL`, payment secrets, or
support-system credentials.

## Smoke Contract

The smoke harness must:

- use a unique Compose project name and non-default host ports;
- start from clean, project-scoped volumes;
- build API and Web images;
- wait for Postgres health, then run migration and seed;
- start API and Web and wait with bounded retries;
- verify `/health`, `/health/db`, `/tickets`, and `/`;
- verify seeded `TCK-1042` and `TCK-1137` records and visible MeterDesk page content;
- explicitly unset live-provider configuration;
- print relevant Compose state and service logs on failure;
- preserve the primary failure code and always clean its own services and volumes.

Seeded audit history is not a live provider run. Documentation must continue to distinguish seeded
replay from an explicitly configured live agent execution.

## Failure and Security Requirements

| Failure | Required behavior |
|---|---|
| Lockfile/manifests disagree | Installation fails; do not regenerate lockfiles silently |
| Migration or seed fails | API/Web smoke stops and prints relevant logs |
| Service never becomes healthy | Bounded wait fails with endpoint and service diagnostics |
| Provider key is missing | Seeded runtime remains available; live run keeps current missing-provider behavior |
| Cleanup fails | Preserve the primary failure and report cleanup failure separately |
| Host port is occupied | Local command reports a clear Compose error; smoke uses non-default ports |
| Runtime user is root | Image acceptance fails |
| Secret or `.env` enters build context/image | Security acceptance fails |

The root Docker build context must exclude `.env*` except examples, `.git`, local agent artifacts,
virtual environments, caches, node modules, Next output, tests artifacts, coverage, and logs. Runtime
containers must be non-root. Demo database credentials must be documented as local-only.

## Documentation Requirements

- Preserve the host-development path in the root README.
- Add a concise containerized seeded-demo path.
- Add `docs/runbooks/container-demo.md` with prerequisites, quick start, URLs, seed/reset semantics,
  no-key behavior, live-provider behavior, health/log/cleanup commands, troubleshooting, and security
  notes.
- State that financial mutations remain mock-only and customer replies remain drafts.
- Update the engineering evidence matrix with exact files, check names, commands, and artifacts.
  Keep CI rows `Planned` until an actual workflow run is available.

## Acceptance Criteria

- API and Web images build from committed lockfiles and run as non-root users.
- Compose defines `postgres`, `migrate`, `seed`, `api`, and `web` without fixed container names.
- Internal database and API hostnames resolve correctly.
- Migration succeeds and seed can be rerun under the documented demo reset contract.
- `make lint`, `make test`, and `make test-db` pass in a suitable environment.
- `make container-build` and `make container-smoke` pass with no provider credentials.
- Smoke verifies API liveness, DB readiness, seeded tickets, and the Web page, then cleans up.
- GitHub Actions exposes the four required successful jobs after push.
- README/runbook commands match the implemented Make and Compose interfaces.
- No agent, approval, mutation, governance, trace, eval, or product-scope behavior changes.
- Completion reporting includes actual commands, exit status, relevant output, deviations, and
  remaining limitations.

Current acceptance status:

| Evidence group | Status | Current evidence or limitation |
|---|---|---|
| API/Web images and users | Verified locally | Real locked builds; both image configs and running processes are `10001:10001`; API workdir is `/workspace/apps/api` |
| Five-service seeded runtime | Verified locally | Repeated unique-project `make container-smoke` runs exercised `postgres`, `migrate`, `seed`, `api`, and `web` |
| No-provider behavior and cleanup | Verified locally | Empty key/model/base URL, expected live-run HTTP 503, project-volume cleanup, and default-volume preservation |
| README/runbook and links | Verified locally | Commands match the Make/Compose interfaces; current link check reports 15 files and 53 local links |
| Candidate branch quality/database | In progress | Final `make lint`, `make test`, and `make test-db` results are pending; root Ruff format drift requires maintainer direction |
| GitHub Actions | Planned | Workflow and all four job contracts exist, but no real remote job has succeeded yet |

## Verification Contract

The implementation plan requires these commands in a suitable environment:

```bash
make lint
make test
make test-db
make container-build
make container-smoke
git diff --check
git status --short
```

It must also verify both image process users and the actual GitHub Actions results. Local inability to
run Docker is a blocker to local evidence, not permission to claim the container work complete.

Current execution status:

- `make container-build` and repeated `make container-smoke` runs exited 0 with the runtime evidence
  recorded above.
- Image config and process-user checks confirmed API and Web are exactly `10001:10001`; the API
  source import resolves from `/workspace/apps/api/src` with repository root `/workspace`.
- `python3 scripts/check_markdown_links.py` exited 0 with 15 current Markdown files and 53 local
  links.
- No final candidate-branch passing result is recorded for `make lint`, `make test`, or
  `make test-db`.
- `backend-quality`, `frontend-quality`, `database-integration`, and `container-smoke` remain
  Planned until actual GitHub job results are available.
