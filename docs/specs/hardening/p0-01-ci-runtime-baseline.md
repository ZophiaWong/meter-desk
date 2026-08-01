# P0-01 CI and Runtime Baseline

## Status

- Priority: P0.
- Design status: approved; runtime architecture implementation is Implemented on the candidate
  branch.
- Evidence status: API/Web images, seeded runtime, no-provider smoke behavior, host lint/tests/
  database, dependency reachability triage, and Markdown links are locally Verified. All four jobs
  are remotely Verified on the corrected implementation head; the evidence-finalized PR head must
  repeat them before merge.
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
and no-provider-key behavior now share one repository-local command surface. The remaining work is
to commit the first successful remote evidence, require the same four jobs on that final head, and
merge the verified tree.

## Implementation and Evidence Snapshot

The following evidence was collected locally on 2026-07-31 and 2026-08-01. Counts and tool versions
describe those executions only; they are not performance, availability, or production-readiness
claims.

- The recorded pre-implementation full test snapshot was API `68 passed, 6 skipped` and Web
  `21 passed` under Node 22.22.2. The current candidate `make test` run passed with API `77 passed,
  6 skipped` and Web `21 passed`; `make lint` passed Ruff check/format, ESLint, and TypeScript.
- The five allowed Ruff findings in `apps/api/src/meterdesk_api/eval/regression.py` were fixed;
  focused Ruff check/format and `15` Eval Lab tests passed. After explicit maintainer approval, the
  three pre-existing format-only findings in `apps/api/src/meterdesk_api/repositories.py`,
  `apps/api/src/meterdesk_api/seed_data.py`, and `apps/api/tests/test_m4_eval_lab.py` were formatted.
  Their Python AST hashes were unchanged, and the root Ruff format check now reports all `52` files
  formatted.
- The Markdown checker has `9` focused passing tests. A full current-doc run reported
  `Checked 15 Markdown file(s), 53 local link(s).`
- Real API and Web image builds succeeded. `meterdesk-api:local` runs from
  `/workspace/apps/api`; `meterdesk-web:local` runs from `/app`; both image configs use
  `10001:10001`.
- Multiple unique-project `make container-smoke` runs succeeded, including projects ending in
  `372842`, `379294`, `388927`, `462530`, `488082`, `538112`, and final pre-publication run
  `555946`. They
  verified API health, database reachability,
  seeded `TCK-1042` and `TCK-1137`, Web content, the key/model-only provider base-URL default,
  loopback-only ephemeral publications, explicit-empty no-key configuration, expected HTTP 503 on
  a live run without a provider, exact non-root image users, project cleanup, and preservation of
  the default `meter-desk_meterdesk-postgres-data` volume.
- A cold `make test-db` run on the brand-new unique project
  `meterdesk-review-db-fix-escalated-460934` waited for Postgres health before Alembic, applied all
  seven migrations, seeded successfully, and passed the M5 database integration check. Its
  disposable volume was removed; the default MeterDesk volume was present before and after.
- The final dependency-update candidate used unique project `meterdesk-db-9871534-secfix` and the
  confirmed-free loopback port `55439`; it waited for Postgres to report Healthy, completed all
  seven migrations, seed, and the M5 database integration check, then removed only its disposable
  project volume. An initial attempt on `55432` stopped before migration because the existing
  default-project Postgres owned that port; the unique failed-attempt resources were cleaned and
  the existing container and default volume were left untouched.
- The synchronized publication candidate repeated the database contract in unique project
  `meterdesk-db-171156e-final` on loopback port `55439`; all seven migrations, seed, and the M5 check
  passed, and only its disposable project volume was removed.
- A Docker-context contract failed before broader generated-artifact exclusions because
  `apps/web/tsconfig.tsbuildinfo` was present, then passed after `.dockerignore` was aligned with
  local build, coverage, test-report, and database artifacts. Required production image builds
  subsequently passed.
- The Web dependency baseline now pins Next.js `15.5.21`. Frozen `npm ci`, Web lint/typecheck,
  `21` tests, production build, `make container-build`, `make container-smoke`, and an inspection of
  the standalone image all confirmed that version. This removes the directly reachable Server
  Actions advisories [GHSA-m99w-x7hq-7vfj](https://github.com/advisories/GHSA-m99w-x7hq-7vfj)
  and [GHSA-955p-x3mx-jcvp](https://github.com/advisories/GHSA-955p-x3mx-jcvp) from the production
  audit result.
- `npm audit --omit=dev --json` completed on 2026-08-01 with exit `1` and three High aggregate
  package entries: Next remains listed only through nested PostCSS `8.4.31` and optional Sharp
  `0.34.5`. The current application does not accept attacker-controlled CSS/source maps and does
  not use `next/image`, an image proxy/upload path, or untrusted GIF/TIFF/VIPS processing. P0-01
  therefore records the PostCSS advisories
  [GHSA-qx2v-qp2m-jg93](https://github.com/advisories/GHSA-qx2v-qp2m-jg93),
  [GHSA-6g55-p6wh-862q](https://github.com/advisories/GHSA-6g55-p6wh-862q), and
  [GHSA-r28c-9q8g-f849](https://github.com/advisories/GHSA-r28c-9q8g-f849), plus Sharp
  [GHSA-f88m-g3jw-g9cj](https://github.com/advisories/GHSA-f88m-g3jw-g9cj), as accepted known
  limitations rather than overriding dependency ranges that Next does not declare compatible.
  Re-evaluate before any non-loopback deployment, attacker-controlled CSS/source-map ingestion,
  `next/image`/image-proxy/upload feature, untrusted image processing, or compatible upstream fix.
- The current local runtime snapshot is Docker Engine client/server `28.1.1` and Docker Compose
  `v2.35.1-desktop.1`.
- Final candidate-branch `make lint`, `make test`, and isolated `make test-db` runs are recorded
  above. PR [run 30679074517](https://github.com/ZophiaWong/meter-desk/actions/runs/30679074517)
  produced a successful `frontend-quality` job; `backend-quality` and `database-integration` failed
  during setup because setup-uv publishes versioned v8 tags but no `v8` alias, and
  `container-smoke` was skipped by its dependency gate. The workflow now uses verified tag
  `astral-sh/setup-uv@v8.3.2`.
- Corrected implementation-head workflow `CI`
  [run 30679673344](https://github.com/ZophiaWong/meter-desk/actions/runs/30679673344)
  succeeded on 2026-08-01: [`backend-quality`](https://github.com/ZophiaWong/meter-desk/actions/runs/30679673344/job/91314054456)
  in `21s`, [`database-integration`](https://github.com/ZophiaWong/meter-desk/actions/runs/30679673344/job/91314054440)
  in `31s`, [`frontend-quality`](https://github.com/ZophiaWong/meter-desk/actions/runs/30679673344/job/91314054485)
  in `1m11s`, and [`container-smoke`](https://github.com/ZophiaWong/meter-desk/actions/runs/30679673344/job/91314171178)
  in `1m26s`. These are the first actual remote evidence results for
  [PR #4](https://github.com/ZophiaWong/meter-desk/pull/4).

P0-01 must establish a clean quality baseline. The narrow Ruff cleanup belongs in this workstream
because new CI would otherwise fail immediately, but it must not change eval or domain behavior.
The production dependency audit is a reachability and disclosure baseline, not a zero-finding or
production-readiness claim.

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
  internal `postgres:5432` and `http://api:8000` interfaces, loopback-default host publications,
  provider-default preservation, and a persistent named Postgres volume.
- `Makefile`: frozen host dependency commands plus `container-build`, `container-up`,
  `container-seed`, `container-smoke`, and volume-preserving `container-down`; host `db-up` waits
  for Postgres health with the bounded container wait timeout.
- `scripts/container-smoke.sh`: unique-project, ephemeral-port, no-provider smoke and guarded
  cleanup, including rendered provider-default and actual loopback-binding checks.
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

- Preserve Postgres 16, the existing default credentials, host port numbers, and persistent volume
  semantics for normal local development.
- Bind default host publications to `127.0.0.1`; use one explicit `CONTAINER_BIND_ADDRESS` override
  when an operator deliberately opts in to remote access.
- Remove the fixed Postgres `container_name`; every service must use Compose-generated names scoped
  by `COMPOSE_PROJECT_NAME`.
- Reuse one explicit API image contract for migration, seed, and API services.
- Use internal hostnames `postgres:5432` and `http://api:8000`.
- Never inject an OpenAI key by default; `.env` may supply one for explicit live use without baking
  it into an image.
- Preserve the application OpenAI base-URL default when the variable is unset, and preserve an
  explicit empty value when the no-key smoke harness clears it.

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
`db-up` must wait for the existing Postgres healthcheck with `CONTAINER_WAIT_TIMEOUT` before a
dependent migration or seed command starts.

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
`actions/setup-node@v6`, `astral-sh/setup-uv@v8.3.2`, Python 3.12, Node 22, and uv `0.11.16`.

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
- verify a key/model-only rendered configuration retains the application OpenAI base URL;
- explicitly unset live-provider configuration;
- verify its ephemeral Postgres, API, and Web publications are loopback-only;
- print relevant Compose state and service logs on failure;
- preserve the primary failure code and always clean its own services, volume, project-specific
  image tags, and temporary artifacts.

Seeded audit history is not a live provider run. Documentation must continue to distinguish seeded
replay from an explicitly configured live agent execution.

## Failure and Security Requirements

| Failure | Required behavior |
|---|---|
| Lockfile/manifests disagree | Installation fails; do not regenerate lockfiles silently |
| Migration or seed fails | API/Web smoke stops and prints relevant logs |
| Cold host Postgres is not ready | `db-up` waits on the existing healthcheck with a bounded timeout before Alembic starts |
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
  Promote the four CI rows after all four jobs succeed on a corrected implementation head, then
  require the same four jobs to repeat on the evidence-finalized PR head before merge.

## Acceptance Criteria

- API and Web images build from committed lockfiles and run as non-root users.
- Compose defines `postgres`, `migrate`, `seed`, `api`, and `web` without fixed container names.
- Internal database and API hostnames resolve correctly.
- Default published ports bind to loopback, with remote binding available only through the explicit
  shared opt-in variable.
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
| API/Web images and users | Verified locally | Real locked builds; both image configs and running processes are `10001:10001`; API workdir is `/workspace/apps/api`; standalone Web contains Next.js `15.5.21` |
| Five-service seeded runtime | Verified locally | Repeated unique-project `make container-smoke` runs exercised `postgres`, `migrate`, `seed`, `api`, and `web` |
| No-provider behavior and cleanup | Verified locally | Empty key/model/base URL, expected live-run HTTP 503, project-volume and exact smoke-image-tag cleanup, and default-volume preservation |
| README/runbook and links | Verified locally | Commands match the Make/Compose interfaces; current link check reports 15 files and 53 local links |
| Candidate branch quality/database | Verified locally | `make lint` passed all Ruff/ESLint/TypeScript checks; `make test` passed with API `77 passed, 6 skipped` and Web `21 passed`; isolated `make test-db` passed all migrations, seed, and the M5 check |
| Production dependency reachability | Verified with accepted limitations | Next.js `15.5.21` removed the reachable Server Actions advisories; production audit still exits `1` for nested PostCSS `8.4.31` and optional Sharp `0.34.5`, whose required attacker-controlled inputs are absent from current P0-01 |
| GitHub Actions | Verified remotely | Corrected implementation-head run `30679673344` completed all four exact jobs successfully; the evidence-finalized PR head must repeat them before merge |

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
- Current `make lint` exited 0 with Ruff check/format over `52` files, ESLint, and TypeScript;
  `make test` exited 0 with API `77 passed, 6 skipped` and Web `21 passed`.
- Cold unique-project and final isolated `make test-db` runs exited 0 after health wait, migrations,
  seed, and the M5 integration check.
- Frozen install and runtime checks resolved Next.js `15.5.21`. The production-only audit exited
  `1` because the accepted PostCSS/Sharp limitations above remain; it is not recorded as audit-clean.
- Corrected implementation-head run `30679673344` Verified `backend-quality`, `frontend-quality`,
  `database-integration`, and `container-smoke`. The evidence-finalized PR head must repeat the same
  four jobs before merge.
