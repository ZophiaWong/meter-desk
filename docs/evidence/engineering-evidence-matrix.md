# MeterDesk Engineering Evidence Matrix

## Purpose

This matrix maps engineering claims to reviewable evidence. It is not a backlog, product spec, or
marketing document. Requirements come from the foundational specs, active roadmap, and approved
workstream specs.

## Status Definitions

- **Existing:** static code or product evidence is present, but may not have been rerun during the
  current workstream.
- **Gap:** sufficient implementation or evidence has not been found, and no approved focused
  workstream spec yet commits to the exact target and acceptance evidence.
- **Planned:** an approved focused workstream spec defines the target and acceptance evidence, but
  implementation or verification is incomplete.
- **Verified:** the named command or runtime check was actually run successfully and its result is
  available for review.
- **Deferred:** explicitly outside the current program.

Do not promote a row to **Verified** from code inspection, an unexecuted command, a seeded claim, or
an implementation plan. Record exact checks and runtime artifacts when promotion occurs.

Statuses are mutually exclusive. Apply them in this order: **Deferred** for explicitly out-of-scope
work, **Verified** for current reviewable execution evidence, **Existing** for present implementation
or product artifacts without current verification, **Planned** for targets in an approved focused
workstream spec, and **Gap** for all other missing implementation or evidence. A target appearing in
the program roadmap alone remains a **Gap** until its focused spec is approved.

## Existing Product Evidence

| Capability | Current evidence | Automated evidence | Runtime evidence | Status |
|---|---|---|---|---|
| Ticket-first governed product | README, Workbench, resource APIs | Frontend route/component tests | Seeded demo screenshots | Existing |
| Backend deterministic outcome authority | Decision tools and orchestrator | Decision/orchestrator tests | Decision and trace surfaces | Existing |
| Bounded LLM planning | Scenario plan contracts and verifier | Plan verifier tests | Planning and verification traces | Existing |
| Approval gate | Governance kernel and approval service | Approval/mutation tests | Approval Queue | Existing |
| Financial action idempotency | Action fingerprint and DB constraints | API/repository safety tests | Mutation audit records | Existing |
| Trace-aware eval | Eval runner, compliance, snapshots | Eval/compliance tests | Eval Lab | Existing |
| Usage Spike scope honesty | Explicit blocked coverage gap | Blocked-case tests | Eval Lab coverage gap | Existing |

`Existing` does not mean the current branch has passed every command. The recorded
pre-implementation full test snapshot was API `68 passed, 6 skipped` and Web `21 passed` under
Node 22.22.2. P0-01 focused checks later reported `15` passing Eval Lab tests and `9` passing
Markdown-link tests. The current candidate `make test` run passed with API `77 passed, 6 skipped`
and Web `21 passed`; `make lint` passed Ruff check/format over `52` files, ESLint, and TypeScript.
Current and cold unique-project `make test-db` runs passed after Postgres health waiting, migrations,
seed, and the M5 integration check. The five allowed Ruff findings were fixed; after explicit
maintainer approval, three pre-existing format-only files were formatted with unchanged Python AST
hashes. The locally verified container environment was Docker Engine `28.1.1` and Docker Compose
`v2.35.1-desktop.1`. These counts and versions are execution context, not product performance
claims.

On the P0-02 candidate, the current non-container rerun passed API `98 passed, 6 skipped` (the six
real-Postgres cases remain dependency-gated) and Web `61 passed`. Ruff check and format over `59`
Python files, ESLint, TypeScript, the optimized Next.js build, `bash -n` for the smoke harness,
Compose configuration parsing, and the Markdown link checker (`16` files, `58` links) passed. The
P0-02 Alembic range `20260701_0007:20260802_0008` generated 44 lines of PostgreSQL SQL offline.
Docker Desktop's Linux engine was unavailable in this environment and its Windows service could not
be started without administrator access, so the updated real-Postgres and container smoke checks
are not recorded as passed.

## Hardening Target Evidence

| Requirement | Current state | Target evidence | Workstream | Status |
|---|---|---|---|---|
| PR backend quality checks | `.github/workflows/ci.yml` runs frozen Ruff check/format, pytest, and Markdown links; setup-uv uses verified tag `v8.3.2` | [`backend-quality`](https://github.com/ZophiaWong/meter-desk/actions/runs/30679673344/job/91314054456) succeeded in CI run `30679673344` on 2026-08-01 | P0-01 | Verified |
| PR frontend quality/build checks | `.github/workflows/ci.yml` runs `npm ci`, lint, typecheck, Vitest, and build with Next.js `15.5.21` | [`frontend-quality`](https://github.com/ZophiaWong/meter-desk/actions/runs/30679673344/job/91314054485) succeeded in CI run `30679673344` on 2026-08-01 | P0-01 | Verified |
| Automated Postgres integration | `.github/workflows/ci.yml` runs `make test-db` with unique project/port and unconditional project-volume cleanup | [`database-integration`](https://github.com/ZophiaWong/meter-desk/actions/runs/30679673344/job/91314054440) succeeded in CI run `30679673344` on 2026-08-01 | P0-01 | Verified |
| CI container smoke | Dependency-gated `container-smoke` runs the five-service no-key path with empty provider variables | [`container-smoke`](https://github.com/ZophiaWong/meter-desk/actions/runs/30679673344/job/91314171178) succeeded in CI run `30679673344` on 2026-08-01 | P0-01 | Verified |
| Locked non-root API image | `apps/api/Dockerfile`, `.dockerignore`; `meterdesk-api:local`, workdir `/workspace/apps/api` | Current `make container-build`; image and process checks returned `10001:10001`; Alembic/seed entrypoints and repository root `/workspace` resolved; Docker-context exclusion contract passed | P0-01 | Verified |
| Locked non-root Web image | `apps/web/Dockerfile`, `apps/web/next.config.ts`, `.dockerignore`; `meterdesk-web:local`, workdir `/app` | Current `make container-build`; image and process checks returned `10001:10001`; `node server.js` standalone runtime contains Next.js `15.5.21`; generated `tsconfig.tsbuildinfo` was excluded from context | P0-01 | Verified |
| Seeded full-stack runtime | `compose.yaml`, `Makefile`, and `scripts/container-smoke.sh` implement `postgres`, `migrate`, `seed`, `api`, `web` | Multiple unique-project `make container-smoke` runs, including final pre-publication project ending `555946`, verified `/health`, `/health/db`, tickets `TCK-1042`/`TCK-1137`, Web content, loopback ports, project cleanup, and default-volume preservation | P0-01 | Verified |
| No-provider-key smoke behavior | Smoke pins empty key/model/base URL and isolates dotenv/Compose selectors | `make container-smoke` verified empty provider environment, expected HTTP 503 `OpenAI-compatible provider is not configured.`, and removal of its exact project image tags without exposing configuration values | P0-01 | Verified |
| Current-document link integrity | `scripts/check_markdown_links.py` and `apps/api/tests/test_markdown_links.py` | `9` focused tests passed; `python3 scripts/check_markdown_links.py` reported 15 Markdown files and 53 local links | P0-01 | Verified |
| Production dependency reachability triage | `apps/web/package.json` and lock pin Next.js `15.5.21`; no current attacker-controlled CSS/source-map or untrusted image-processing path | `npm ci`; `npm ls next postcss sharp --omit=dev`; Web lint/typecheck/test/build; standalone image version check; `npm audit --omit=dev --json` exited `1` with direct Next Server Actions advisories removed and accepted PostCSS `8.4.31`/Sharp `0.34.5` limitations plus explicit re-evaluation triggers recorded in the focused spec | P0-01 | Verified |
| Demo authentication boundary | Static FastAPI principal registry, fixed-claim HS256 JWT issue/verify, protected resource router, production fail-closed settings | Current backend suite passed `test_auth.py`, `test_rbac.py`, and settings coverage within `98 passed, 6 skipped` | P0-02 | Verified |
| Client cannot choose approver | Approval decision input accepts only optional `decision_note`; backend derives actor from the authenticated principal | Forged `decided_by` request stays `422` and leaves approval/mutation state unchanged in the passing backend suite | P0-02 | Verified |
| Approval role enforcement | FastAPI permission dependencies implement read/Agent/approval/Eval matrix; Web keeps disallowed controls visible and disabled | Backend role-matrix tests plus Web operator/approver/admin route/component tests passed | P0-02 | Verified |
| Demo browser session boundary | Next.js server actions and session DAL use one API-synchronized `HttpOnly`, `SameSite=Lax`, path-wide cookie, HTTPS `Secure`, safe return paths, and Bearer forwarding | Web `61 passed`, ESLint, TypeScript, and optimized Next.js build passed; no local-storage token path exists | P0-02 | Verified |
| Request correlation | FastAPI middleware emits `req_<uuid>` in every response header and structured API error; approval decisions persist the first request ID | Request-ID, structured-error, and immutable retry tests passed in the backend suite | P0-02 | Verified |
| Approval actor audit | Alembic `20260802_0008`, repository mapping, and seed fixture implement subject/display/role/source/request persistence and legacy provenance | Backend repository/API tests passed and offline PostgreSQL SQL compiled; real `make test-db` migration/seed persistence rerun remains required | P0-02 | Planned |
| P0-02 container authentication smoke | Compose carries explicit demo-only auth settings; smoke asserts anonymous `401`, role denial, approver persistence, Web login, and authenticated no-provider `503` | `bash -n` and Compose config parsing passed; Docker Linux engine was unavailable, so `make container-smoke` remains required | P0-02 | Planned |
| Application-lifetime DB engine | Engine created/disposed per request | Lifespan lifecycle tests | P1-04 | Gap |
| Async DB readiness | Sync socket/psycopg inside async function | Async query health tests | P1-04 | Gap |
| Concurrent approval safety | Constraints exist; concurrent DB proof missing | Real Postgres approve/approve and approve/reject tests | P1-04 | Gap |
| Explicit workflow completion semantics | Run may complete before approval creation | State-transition contract and tests | P0-03 | Gap |
| Approval-write failure safety | Partial-state risk exists | Injected failure and persisted-state evidence | P0-03 | Gap |
| Non-blocking run start | Execution waits inside request | Accepted response plus worker test and latency evidence | P0-04 | Gap |
| Worker recovery | No worker/checkpoint | Crash/restart and duplicate-delivery tests | P0-04 | Gap |
| Cancellation | No cancellation contract | Cancel transition and provider propagation tests | P0-04/P1-01 | Gap |
| Provider timeout taxonomy | Fixed timeout mapping | Connect/read/write/total timeout tests | P1-01 | Gap |
| Controlled provider retry | Limited fixed retry | 429/5xx classification, backoff, deadline tests | P1-01 | Gap |
| Provider usage metadata | Usage not persisted | Response mapping and stored token/cost evidence | P1-01/P0-05 | Gap |
| Correlated runtime latency | Domain audit trace only | Instrumentation tests and trace/dashboard evidence | P0-05 | Gap |
| Queue delay and approval wait | Timestamps not operational metrics | Calculation tests and metrics evidence | P0-05 | Gap |
| Typed networked read boundary | In-process mock data only | Repository-local mock billing HTTP contract/failure tests | P0-06 | Gap |
| Structured evidence references | String-prefix convention | `EvidenceRef` serialization and eval tests | P1-03 | Gap |
| Auditable context selection | Provider input assembled in orchestrator | Context selection/redaction/hash snapshot tests | P1-03 | Gap |
| Prompt-injection regression | Allowlist offers partial protection | Focused stable reason-code fixtures | P1-02 | Gap |
| Bilingual draft safety | English-oriented checks | Chinese/English safety fixtures | P1-02 | Gap |
| Indirect promise detection | Limited phrase coverage | Paraphrase fixtures and deterministic/judge evidence | P1-02 | Gap |
| Failure/concurrency regression | Localized unit tests | 30+ focused cross-system fixtures/checks | P1-02 | Gap |
| Nine canonical business eval cases | Three cases per v1 scenario | Existing Eval Lab cases remain canonical | Global constraint | Existing |
| Real payment or support writes | Explicitly prohibited | Governance regression proving writes remain impossible | Global constraint | Deferred |
| Real third-party billing read adapter | Conflicts with v1 mock boundary | Requires separate product-scope approval | Global constraint | Deferred |
| Multi-agent product runtime | No product requirement | Remains unimplemented | Global constraint | Deferred |
| Multi-provider gateway | Explicitly out of scope | Remains unimplemented | Global constraint | Deferred |

## Update Protocol

Before a workstream is declared complete:

1. merge the implementation and promote its affected foundational-spec labels from **Planned** to
   **Implemented** in the same pull request;
2. replace target descriptions with actual files and interfaces;
3. name the exact automated checks and commands;
4. record actual exit status and relevant output;
5. link runtime artifacts or screenshots when required;
6. use **Verified** only when evidence is current and reviewable;
7. leave incomplete criteria as **Planned** or **Gap** and record limitations explicitly.

Foundational-spec labels and matrix evidence statuses answer different questions: **Implemented**
means the architecture or governance invariant has landed, while **Verified** means the named check
was actually run and its evidence is reviewable. Neither promotion implies the other automatically.

Only **Verified** rows should be converted into unqualified resume claims. Claims such as
"production-ready", "high availability", "low latency", "scalable", "cost optimized", or
"secure multi-tenant" require separate quantitative evidence and are not implied by this roadmap.
