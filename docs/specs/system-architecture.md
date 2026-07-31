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
while branch-wide quality/database verification remains in progress. The first remote GitHub
Actions run has not yet occurred, so remote CI verification is pending.

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
  and volume.

The runtime adds packaging and orchestration only. FastAPI still owns business and governance
authority; no agent, approval, mutation, trace, or eval contract moved into Compose or the images.

## Boundary Rules

- Next.js owns presentation, client-side interaction, and API consumption.
- FastAPI owns business workflows, data validation, agent orchestration, tool execution, approval rules, and eval execution.
- Postgres owns durable state and audit history.
- Mock external systems are internal modules or seeded tables, not real provider integrations.
- Agent tools access data through backend-controlled interfaces, not directly from frontend components.
- Customer reply drafts are generated and stored as drafts only; sending is not implemented in v1.

## Core Data Flow

The Duplicate Charge golden path should follow this flow:

1. The frontend opens a ticket and requests current ticket context from FastAPI.
2. FastAPI reads ticket, account, invoice, charge, credit, and policy data from Postgres-backed mock systems.
3. The operator starts an agent run.
4. The agent uses permission-scoped backend tools.
5. Each tool call writes a trace envelope with input summary, output summary, permission metadata, and evidence references.
6. The agent returns a recommendation, internal resolution draft, and customer reply draft.
7. If the recommendation includes a refund or credit, FastAPI creates an approval request.
8. A human approval decision updates approval state.
9. Approved actions create mock mutations and audit records.
10. Eval runs reuse stored cases and inspect both final outcome and trace behavior.

## Minimal Domain Glossary

- **Ticket**: a support case for a billing dispute.
- **Customer Account**: the billing identity connected to tickets, subscriptions, invoices, usage, credits, and prior adjustments.
- **Invoice**: a billing document with line items, status, totals, and related charges.
- **Charge or Payment**: a payment attempt or captured amount associated with an invoice or account.
- **Usage Record**: metered usage data used to explain billed amounts.
- **Credit Ledger Entry**: granted credits, consumed credits, remaining balances, and prior adjustments.
- **Policy Rule**: a versioned refund, credit, cancellation, or usage policy used to justify a recommendation.
- **Agent Run**: one investigation attempt by the agent for a ticket.
- **Tool Trace**: a structured record of a tool call, permission level, inputs, outputs, evidence, and errors.
- **Approval Request**: a human decision gate for high-risk refund or credit actions.
- **Mock Mutation**: a simulated refund or credit action created only after approval.
- **Eval Case**: an offline scenario with expected outcome, required evidence, and grading criteria.
- **Eval Result**: recorded scores, failures, and trace links for an eval run.

## API Expectations

V1 APIs should be resource-oriented and boring:

- ticket list and detail APIs for the workbench.
- agent run APIs for starting and inspecting investigations.
- approval APIs for queue, approve, and reject actions.
- eval APIs for listing cases, running cases, and reading results.
- mock data APIs only where the UI needs direct read access.

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

P0-01 implemented the runtime packaging described above. The remaining active hardening roadmap
proposes these later architecture changes; they are target directions, not claims about the current
implementation:

- derive approval identity from a server-verified local/demo principal with role enforcement.
- manage the async database engine and session factory through FastAPI lifespan.
- separate case workflow state from HTTP request lifetime with explicit transitions, retries,
  cancellation, checkpoints, and idempotency.
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
