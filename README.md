# MeterDesk

MeterDesk is an agent-governed billing support console for usage-based API and AI platforms. It helps support and billing teams investigate metered billing disputes with permission-scoped AI agents, policy-grounded evidence, human approval gates, and auditable traces.

MeterDesk is not a generic customer support chatbot. The product thesis is that billing support for usage-based platforms needs controlled investigation and accountable action, not autonomous customer messaging.

## V1 Focus

The v1 golden path is **Duplicate Charge**:

1. A support operator opens a billing dispute ticket.
2. The agent investigates invoices, charges, account state, credits, usage, and relevant policy.
3. The agent produces an evidence-backed resolution draft.
4. Any refund or credit mutation is routed to human approval.
5. An approved action executes only as a mock mutation.
6. The full run is available as an audit trail and offline eval target.

Supporting scenarios are **Usage Spike** and **Credit/Refund Dispute**. They reuse the same workbench, governance, trace, approval, and eval patterns without becoming separate product lines in v1.

## Key Signals

- Permission-scoped agent tools with structured traces.
- Human approval gates for high-risk refund and credit actions.
- Draft-only customer replies; MeterDesk never auto-sends customer messages in v1.
- Mock billing and payment systems that look realistic without touching real providers.
- Offline evals that score both final outcomes and agent trace behavior.
- A Support Workbench-style UI direction for billing investigation.

## Planned Stack

- Frontend: Next.js
- Backend: FastAPI
- Database: Postgres
- LLM: OpenAI-compatible interface with one live provider in v1
- Retrieval: no vector search in v1; policy is handled through explicit policy text and eligibility checks
- MCP posture: adapter-ready tool layer, but no required MCP server in v1

## Project Docs

Start with these documents before implementation:

- [AGENTS.md](AGENTS.md) - operating rules for AI coding agents
- [Product Scope](docs/specs/product-scope.md) - product thesis, v1 scope, golden path, and exclusions
- [System Architecture](docs/specs/system-architecture.md) - application boundaries, data flow, mock systems, and domain glossary
- [Agent Governance](docs/specs/agent-governance.md) - tool governance, approval gates, trace rules, and policy citation requirements
- [Eval Strategy](docs/specs/eval-strategy.md) - offline eval cases, grading dimensions, and Eval Lab expectations
- [Implementation Roadmap](docs/specs/implementation-roadmap.md) - milestone sequence for building the v1 system
- [M2 Backend Domain + Mock Billing](docs/specs/m2-backend-domain-mock-billing.md) - durable mock billing data, read APIs, seed behavior, and DB checks
- [M3 Governed Agent Loop](docs/specs/m3-governed-agent-loop.md) - constrained agent orchestration, provider boundary, approval writes, and mock mutation execution

## Local Setup

### Prerequisites

- Node.js and npm.
- Python 3.12.
- `uv` for Python dependency management.
- Docker with Compose support for local Postgres.

### First Run

```bash
cp .env.example .env
make install
make db-up
make dev
```

The default local services are:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Postgres: `localhost:5432`

The frontend reads API/database status plus M3 governed agent loop resources from FastAPI.

### Development Commands

```bash
make install
make db-up
make dev
make dev-api
make dev-web
make health
make test
make test-db
make lint
make seed
make demo-reset-live
make db-down
```

`make seed` runs migrations and resets the demo-owned mock billing rows. It preserves unrelated local domain rows, rebuilds the Duplicate Charge, Usage Spike, Credit/Refund Dispute, historical mock mutation, eval case fixtures, and a completed Duplicate Charge portfolio baseline with a pending approval and no mock mutation.

`make demo-reset-live` clears only `TCK-1042` runtime state so a configured OpenAI-compatible provider can run the live Duplicate Charge agent path from the Workbench.

`make test-db` starts local Postgres, runs migrations, seeds demo data, and verifies key M3 seed and run-preflight APIs against the real database. The default `make test` remains fast and does not require Docker/Postgres.

To run the M3 agent loop locally, configure `OPENAI_API_KEY` and `OPENAI_MODEL` in `.env`. `OPENAI_BASE_URL` defaults to `https://api.openai.com/v1` and can point at another OpenAI-compatible endpoint.

### Health Checks

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/health/db
```

`/health` verifies FastAPI liveness. `/health/db` verifies the backend can execute a simple Postgres query.

If `/health/db` returns 503 while Postgres appears healthy in Docker, see [WSL2 Docker Desktop Postgres troubleshooting](docs/troubleshooting/wsl-docker-postgres-health-db.md).

## Demo Walkthrough

The interview demo centers on the Duplicate Charge golden path. The short flow is:

1. Open a duplicate charge ticket in the Ticket Workbench.
2. Inspect billing evidence, policy citations, the seeded agent run, and the trace timeline.
3. Review the draft-only internal resolution and customer reply.
4. Approve or reject the proposed refund.
5. Inspect the mock mutation and audit trace.
6. Run Eval Lab and review Duplicate Charge scores plus supporting scenario coverage gaps.

For the full interview script, including the no-key baseline, live provider reset path, architecture talking points, and likely interview questions, see [MeterDesk Interview Demo Walkthrough](intv/meterdesk-demo-walkthrough.md).

## Out of Scope for V1

- Real payment provider integrations.
- Real Zendesk, Slack, Feishu, or enterprise messaging integrations.
- Automatic customer replies.
- Complex workflow builders.
- A standalone tool registry editor.
- Required MCP server implementation.
- pgvector or large-scale RAG.
- Multi-provider model gateway.
- Enterprise multi-tenant permission systems.
- Security incident or SLA incident workflows.
