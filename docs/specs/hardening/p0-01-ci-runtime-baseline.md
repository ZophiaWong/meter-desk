# P0-01 CI and Runtime Baseline

## Status

- Priority: P0.
- Design status: approved for planning; implementation not started.
- Evidence status: Planned.
- Depends on: current post-M10 `main` after documentation integration.
- Blocks: every later hardening workstream.
- Intended product behavior change: none.

No active implementation plan exists for this feature. The archived 2026-07-30 plan is stale and
must not be executed. Generate a fresh plan after this specification and the documentation reorg are
merged, then re-read the referenced files and tool versions.

## Problem

MeterDesk has local install, lint, test, database, seed, reset, and development commands, but lacks a
publicly repeatable build/runtime contract:

- no GitHub Actions workflow is present;
- no API or Web Dockerfile is present;
- no root `.dockerignore` is present;
- Compose starts only Postgres;
- the existing Postgres service has a fixed `container_name`, which defeats Compose project-name
  isolation required by concurrent and cleanup-safe smoke runs;
- the README documents host development but not a containerized seeded application runtime.

Reviewers therefore cannot quickly verify locked installs, production builds, migrations, seeded
runtime behavior, API/Web container networking, or a no-provider-key full-stack smoke path.

## Dated Baseline Observations

The following observations were collected locally on 2026-07-31. They document the starting point;
they are not permanent acceptance values and do not waive any requirement below.

- `make lint` stopped in API Ruff checks with five findings in
  `apps/api/src/meterdesk_api/eval/regression.py`: unsorted imports, two unused imports, and two
  over-length lines.
- API tests completed with `68 passed, 6 skipped`; the skipped tests are Postgres-backed checks.
- `make test` could not reach frontend tests because the local WSL/Node installation reported an
  unsupported or unresolved Node environment. This is an environment limitation, not evidence that
  frontend tests pass or fail.
- Docker was unavailable in the local WSL distribution, so Compose, image, and smoke commands were
  not executed.

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

## Non-Goals

P0-01 does not add cloud hosting, registry publishing, deployment automation, Kubernetes,
authentication/RBAC, worker/queue execution, OpenTelemetry, provider resilience, real integrations,
real payment mutations, Usage Spike execution, UI redesign, or database lifecycle refactoring.

It must not change planning, deterministic decision authority, approval behavior, mutation
idempotency, governance enforcement, trace scoring, eval semantics, seeded scenario expectations, or
the draft-only customer reply boundary.

## Target Runtime

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

Create one pull-request, main-push, and manually dispatchable workflow with read-only repository
permissions and per-ref concurrency cancellation.

Required jobs:

- `backend-quality`: Python 3.12, frozen uv install, Ruff check/format check, pytest.
- `frontend-quality`: Node 22, `npm ci`, ESLint, TypeScript, Vitest, production build.
- `database-integration`: migration, seed, and Postgres-backed checker with unconditional cleanup.
- `container-smoke`: depends on the other jobs and runs the full clean seeded stack.

Versions validated during documentation integration were `actions/checkout@v6`,
`actions/setup-python@v6`, `actions/setup-node@v6`, `astral-sh/setup-uv@v8`, and uv `0.11.16`.
The fresh implementation plan must confirm these choices before pinning them.

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

## Verification Contract

The fresh implementation plan must include and actually run, in a suitable environment:

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
