# MeterDesk System Architecture

## Architecture Goals

MeterDesk should be a full-stack product with clear boundaries between UI, backend APIs, agent orchestration, mock billing systems, and durable audit state.

The architecture should favor simple, explicit interfaces over broad abstractions. V1 should be easy to understand, seed, demo, test, and evaluate.

## Application Stack

- **Next.js**: frontend application and product UI.
- **FastAPI**: backend API, agent run orchestration, approval handling, eval execution, and mock system access.
- **Postgres**: durable state for tickets, mock billing data, approvals, agent runs, tool traces, mock mutations, and eval results.
- **OpenAI-compatible LLM interface**: provider-agnostic boundary with one live provider in v1.

## P0-01 Runtime Packaging (Implemented)

The application boundaries above now have a repository-local container runtime. This packaging is
implemented on the P0-01 candidate branch; local image and full-stack smoke evidence is verified,
and branch-wide lint, test, and database verification is complete. Corrected implementation-head
CI run `30679673344` completed all four required jobs successfully; the evidence-finalized PR head
must repeat them before merge.

- `apps/api/Dockerfile` builds from the repository root with the committed `apps/api/uv.lock`, keeps
  the source layout at `/workspace/apps/api`, sets `PYTHONPATH=/workspace/apps/api/src`, and runs
  Uvicorn as numeric user `10001:10001`. The same image supplies the Alembic and seed entrypoints.
- `apps/web/Dockerfile` installs from `apps/web/package-lock.json` with `npm ci`, copies the Next.js
  standalone output to `/app`, and runs `node server.js` as numeric user `10001:10001`.
- `.dockerignore` excludes `.env` files, repository metadata, local agent artifacts, dependency
  directories, build output, test artifacts, coverage, and logs from the shared root build context.
- `compose.yaml` defines the dependency chain `postgres` -> `migrate` -> `seed` -> `api` -> `web`.
  `postgres` is Postgres 16 Alpine; `migrate` and `seed` are one-shot API-image services; `api` and
  `web` are health-ordered long-running services.
- Application containers use `postgres:5432` through `CONTAINER_DATABASE_URL` or coupled
  `POSTGRES_*` defaults. The Web server uses `API_BASE_URL=http://api:8000`. Host defaults remain
  Postgres `5432`, API `8000`, and Web `3000`.
- `Makefile` exposes `container-build`, `container-up`, `container-seed`, `container-smoke`, and
  `container-down`. Normal teardown preserves the named Postgres volume.
- `scripts/container-smoke.sh` binds the repository `compose.yaml` explicitly, disables automatic
  dotenv and inherited Compose selectors, uses a unique project with ephemeral host ports, passes
  empty provider configuration, and removes only its project services, network, response artifacts,
  volume, and two exact project-specific image tags.

The runtime adds packaging and orchestration only. FastAPI still owns business and governance
authority; no agent, approval, mutation, trace, or eval contract moved into Compose or the images.

## P0-02 Local Demo Authentication (Implemented on Candidate Branch)

FastAPI now owns a local/demo identity boundary in addition to business authority. A static registry
maps `demo-support-operator`, `demo-approver`, and `demo-admin` to their server-side roles. Public
login issues an eight-hour HS256 JWT containing fixed issuer, audience, subject, issued-at, expiry,
and token-ID claims; role and display name are deliberately absent and are resolved from the
registry on every authenticated request.

Next.js is the browser-facing session boundary. Server actions place the token in an `HttpOnly`,
`SameSite=Lax`, path-wide cookie, add `Secure` for HTTPS, validate it through `GET /auth/me`, and
forward it to FastAPI as a Bearer token. The cookie is shared across tabs, but there is no
server-side session store, refresh flow, user table, or external identity provider.

All business resource routes require authentication. Backend permissions are: all roles may read;
support operator and admin may start Agent runs; approver and admin may decide approvals; only admin
may run Evals. Health, API documentation, demo identity listing, and demo login stay public. Every
response carries `X-Request-ID`; structured API errors repeat the ID in their body.

Approval decisions no longer accept a caller-selected actor. Postgres stores the verified actor
subject, display name, role, source, and decision request ID. Seed-owned terminal history is marked
`seed_fixture`; unknown migrated external history is marked `legacy_unverified`. The demo
authentication configuration fails closed when the application environment is production.

## P1-04 Persistence Foundation (Implemented on Candidate Branch)

Each FastAPI process now constructs one `DatabaseRuntime` during application lifespan. The runtime
owns one SQLAlchemy `AsyncEngine` and one `async_sessionmaker`; requests create independent sessions
from that factory, while shutdown disposes the engine once. Missing lifespan state is an error rather
than a fallback to a request-scoped engine. Alembic retains `NullPool`, and seed/reset commands use
explicit short-lived runtimes.

The runtime has bounded per-process pool settings (size `5`, overflow `5`, checkout timeout `5s`,
connect timeout `3s`) and always enables pre-ping. `/health` remains a liveness check. `/health/db`
runs async `SELECT 1` through the shared engine, and Compose uses it as API readiness before starting
Web.

Approval approve/reject writes acquire `SELECT ... FOR UPDATE` and refresh cached ORM state before
choosing a terminal transition. The first lock holder that commits wins; a same-direction approve is
idempotent, an opposite terminal decision returns `409`, and the original actor/request audit remains
unchanged. P0-03 extends this lock discipline to a `CaseWorkflow` aggregate and closes the
mutation-to-trace window: finalization and approve-and-execute persist their run/workflow, approval,
mutation, and governance-trace writes in one transaction. Postgres remains at `READ COMMITTED`,
with narrow repository commands and no outbox or general Unit of Work.

## P0-03 Workflow State Consistency (Implemented on Candidate Branch)

`CaseWorkflow` owns the durable state of one ticket-processing cycle; `AgentRun` records one
investigation attempt inside that cycle. The authoritative state vocabulary is `investigating`,
`needs_retry`, `awaiting_approval`, `completed_no_action`, `rejected`, `mock_executed`, `failed`,
and `cancelled`. A partial unique index permits one active cycle per ticket, while a self-reference
links a terminal cycle to the next cycle. `CaseWorkflowTransition` is append-only and records every
legal change with reason code, request/actor provenance, and artifact references.

The transition rules and atomic commands are centralized in
`apps/api/src/meterdesk_api/workflows.py` and the repository boundary. Start requires an
`Idempotency-Key`; same-key requests replay, `needs_retry` retries reuse the cycle, and different
keys conflict with running or awaiting work. Finalization commits the run output, final traces,
approval (when required), approval trace, and Workflow transition together. Approve-and-execute
locks Workflow then Approval and commits trusted approval audit, mock mutation, mutation trace, and
`mock_executed` together. Cancellation withdraws pending approval and is limited to Support/Admin.
Migration `20260806_0009` backfills legacy rows fail-closed and refuses unprovable combinations.

P0-03 is still synchronous. Queue/worker execution, leases, checkpoints, stale detection, and crash
recovery remain P0-04 responsibilities.

## Boundary Rules

- Next.js owns presentation, client-side interaction, the `HttpOnly` demo cookie, and server-side
  Bearer forwarding.
- FastAPI owns token issuance/verification, role enforcement, business workflows, data validation,
  agent orchestration, tool execution, approval rules, and eval execution.
- Postgres owns durable state and audit history.
- Mock external systems are internal modules or seeded tables, not real provider integrations.
- Agent tools access data through backend-controlled interfaces, not directly from frontend components.
- Customer reply drafts are generated and stored as drafts only; sending is not implemented in v1.

## Core Data Flow

The Duplicate Charge golden path should follow this flow:

1. The frontend opens a ticket and requests current ticket context from FastAPI.
2. FastAPI reads ticket, account, invoice, charge, credit, and policy data from Postgres-backed mock systems.
3. An authenticated support operator or admin starts an idempotent Agent run inside a new or
   retryable Case Workflow.
4. The agent uses permission-scoped backend tools.
5. Each tool call writes a trace envelope with input summary, output summary, permission metadata, and evidence references.
6. The agent returns a recommendation, internal resolution draft, and customer reply draft.
7. If the recommendation includes a refund or credit, one transaction finalizes the run, final
   traces, approval request, and Workflow `awaiting_approval` transition.
8. An authenticated approver or admin records a decision; FastAPI persists the verified actor and
   request ID, mock mutation, mutation trace, and `mock_executed` transition atomically.
9. Support/Admin can cancel an active cycle; pending approval is withdrawn and late decisions lose
   with `409`.
10. Eval runs reuse stored cases and inspect both Workflow terminal state and trace behavior.

## Minimal Domain Glossary

- **Ticket**: a support case for a billing dispute.
- **Customer Account**: the billing identity connected to tickets, subscriptions, invoices, usage, credits, and prior adjustments.
- **Invoice**: a billing document with line items, status, totals, and related charges.
- **Charge or Payment**: a payment attempt or captured amount associated with an invoice or account.
- **Usage Record**: metered usage data used to explain billed amounts.
- **Credit Ledger Entry**: granted credits, consumed credits, remaining balances, and prior adjustments.
- **Policy Rule**: a versioned refund, credit, cancellation, or usage policy used to justify a recommendation.
- **Case Workflow**: the durable state aggregate for one ticket-processing cycle; terminal cycles
  cannot be reopened and a later cycle points to its predecessor.
- **Agent Run**: one investigation attempt by the agent inside a Case Workflow.
- **Workflow Transition**: an append-only, actor/request-correlated status change for a Case
  Workflow.
- **Tool Trace**: a structured record of a tool call, permission level, inputs, outputs, evidence, and errors.
- **Approval Request**: a human decision gate for high-risk refund or credit actions.
- **Mock Mutation**: a simulated refund or credit action created only after approval.
- **Eval Case**: an offline scenario with expected outcome, required evidence, and grading criteria.
- **Eval Result**: recorded scores, failures, and trace links for an eval run.

## API Expectations

V1 APIs should be resource-oriented and boring:

- ticket list and detail APIs for the workbench.
- agent run APIs for starting and inspecting investigations with idempotent replay semantics.
- workflow APIs for cycle state, transition history, and Support/Admin cancellation.
- approval APIs for queue, approve, and reject actions.
- eval APIs for listing cases, running cases, and reading results.
- mock data APIs only where the UI needs direct read access.
- public demo identity/login APIs and an authenticated current-principal API.
- consistent `401` authentication and `403` authorization errors with request correlation.

Do not design a public external API in v1. Internal API shape should serve the app and remain easy to change while the product is still forming.

## Mock External Systems

Mock systems should be realistic enough to support credible investigation:

- invoices and charges should include dates, amounts, statuses, and identifiers.
- usage records should explain billed usage and spikes.
- credit ledger entries should show granted, consumed, and remaining credit.
- policy rules should have stable identifiers and versions.
- mock mutations should be idempotent enough to avoid duplicate simulated refunds or credits.

Mock systems must not call real Stripe, payment, support, messaging, or accounting APIs in v1.

## Post-M10 Hardening Direction

P0-01 implemented the runtime packaging described above, P0-02 implemented the local demo
authentication boundary, P1-04 implemented the persistence foundation, and P0-03 implemented the
explicit workflow state contract described above. The remaining active hardening roadmap proposes
these later architecture changes; they are target directions, not claims about the current
implementation:

- move synchronous workflow commands behind an async queue/worker boundary with checkpoints,
  leases, stale detection, and crash recovery (P0-04).
- replace blocking provider I/O with an async resilience contract and structured usage metadata.
- correlate domain audit identifiers with operational logs, traces, metrics, latency, and cost.
- prove typed tool execution through one repository-local, read-only mock billing HTTP service with
  tested authentication and failure behavior.
- introduce versioned evidence references and auditable context snapshots without vector memory or
  large-scale RAG.

The networked mock service does not relax the prohibition on real Stripe, payment, support,
messaging, or accounting integrations. Detailed interfaces require focused, approved workstream
specs before implementation.

## Deferred Architecture Work

- Detailed database schema.
- Detailed tool schemas.
- Detailed UI component architecture.
- Real MCP server implementation.
- Real provider integrations.
- Cloud deployment and production SRE operations.
