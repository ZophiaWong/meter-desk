# MeterDesk

MeterDesk is a billing support workbench for usage-based API and AI platforms. It lets an agent inspect invoices, charges, credits, usage, and policy records through backend-owned tools.

It is not a chat-first support bot. The main screen is a ticket workbench where the agent gathers evidence, explains a billing decision, drafts internal and customer-facing text, and requests approval. Refunds and credits do not execute until a human approves them. In v1, those executions are mock mutations only.

## Core capabilities

- Ticket-first investigation: the Workbench starts from a billing dispute ticket, not an open-ended chat box.
- Backend-owned tools: the agent uses read, decision, draft, approval, and mock mutation boundaries controlled by FastAPI.
- Human approval: refund and credit actions stay blocked until a human approves the specific request.
- Audit records: agent runs, tool calls, policy citations, approval decisions, and mock mutations are stored for review.
- Offline evals: Eval Lab checks both the final answer and the trace path, including evidence coverage and approval routing.

## V1 golden path

The v1 golden path is **Duplicate Charge**:

1. A support operator opens a billing dispute ticket.
2. The agent investigates invoices, charges, account state, credits, usage, and relevant policy.
3. The agent creates a resolution draft with evidence and policy citations.
4. Any refund or credit mutation is routed to human approval.
5. An approved action executes only as a mock mutation.
6. The full run is available as an audit trail and offline eval target.

MeterDesk also includes **Usage Spike** and **Credit/Refund Dispute** as supporting scenarios. Credit/Refund Dispute has a runnable governed workflow for `TCK-1137`. Usage Spike is still a visible coverage gap. Both scenarios reuse the same workbench, trace, approval, and eval model instead of becoming separate product lines.

## System architecture

MeterDesk separates the UI, backend workflow control, agent orchestration, mock systems, and stored audit data.

![System architecture](docs/diagrams/system-architecture.svg)

Mermaid reference: [system-architecture.mmd](docs/diagrams/system-architecture.mmd)

Stack:

- Frontend: Next.js
- Backend: FastAPI
- Database: Postgres
- LLM: OpenAI-compatible interface with one live provider in v1
- Retrieval: no vector search in v1; policy is handled through explicit policy text and eligibility checks
- MCP posture: adapter-ready tool layer, but no required MCP server in v1

## Governed agent run

The model can plan and draft. FastAPI verifies plans, owns tool execution, records traces, and creates approval requests.

![Governed agent run sequence](docs/diagrams/governed-agent-run.svg)

Mermaid reference: [governed-agent-run.mmd](docs/diagrams/governed-agent-run.mmd)

## Approval gate state machine

Refunds and credits are high-risk actions even in a mock system. The agent can propose them, but mutation stays blocked until a human approval decision is recorded.

![Approval gate state machine](docs/diagrams/approval-gate-state-machine.svg)

Mermaid reference: [approval-gate-state-machine.mmd](docs/diagrams/approval-gate-state-machine.mmd)

## Local setup

### Prerequisites

- Node.js and npm.
- Python 3.12.
- `uv` for Python dependency management.
- Docker with Compose support for local Postgres.

### First run

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

The frontend reads health status and governed agent resources from FastAPI.

### Development commands

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
make demo-reset-live TICKET_ID=TCK-1137
make db-down
```

`make seed` runs migrations and rebuilds the demo-owned mock billing rows. It leaves unrelated local rows alone. The seed includes Duplicate Charge, Usage Spike, Credit/Refund Dispute, eval fixtures, historical eval mock mutation data, and completed demo baselines for Duplicate Charge and Credit/Refund. Both visible baselines stop at pending approval, with no visible mock mutation before approval.

`make demo-reset-live` clears only `TCK-1042` runtime state by default so a configured OpenAI-compatible provider can run the live Duplicate Charge agent path from the Workbench. Use `make demo-reset-live TICKET_ID=TCK-1137` to reset the Credit/Refund Dispute path.

`make test-db` starts local Postgres, runs migrations, seeds demo data, and checks the M3 seed and run-preflight APIs against the real database. The default `make test` stays fast and does not require Docker/Postgres.

To run the M3 agent loop locally, configure `OPENAI_API_KEY` and `OPENAI_MODEL` in `.env`. `OPENAI_BASE_URL` defaults to `https://api.openai.com/v1` and can point at another OpenAI-compatible endpoint.

### Health checks

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/health/db
```

`/health` verifies FastAPI liveness. `/health/db` verifies the backend can execute a simple Postgres query.

If `/health/db` returns 503 while Postgres appears healthy in Docker, see [WSL2 Docker Desktop Postgres troubleshooting](docs/troubleshooting/wsl-docker-postgres-health-db.md).

## Demo script

For the no-key seeded baseline, live provider reset path, architecture talking points, and interview walkthrough, see [MeterDesk Interview Demo Walkthrough](intv/meterdesk-demo-walkthrough.md).

## Project docs

Start with these documents before implementation:

- [AGENTS.md](AGENTS.md) - operating rules for AI coding agents
- [Product Scope](docs/specs/product-scope.md) - product thesis, v1 scope, golden path, and exclusions
- [System Architecture](docs/specs/system-architecture.md) - application boundaries, data flow, mock systems, and domain glossary
- [Agent Governance](docs/specs/agent-governance.md) - tool governance, approval gates, trace rules, and policy citation requirements
- [Eval Strategy](docs/specs/eval-strategy.md) - offline eval cases, grading dimensions, and Eval Lab expectations
- [Implementation Roadmap](docs/specs/implementation-roadmap.md) - milestone sequence for building the v1 system
- [M2 Backend Domain + Mock Billing](docs/specs/m2-backend-domain-mock-billing.md) - durable mock billing data, read APIs, seed behavior, and DB checks
- [M3 Governed Agent Loop](docs/specs/m3-governed-agent-loop.md) - constrained agent orchestration, provider boundary, approval writes, and mock mutation execution
- [M4 Eval Lab](docs/specs/m4-eval-lab.md) - deterministic eval runner, Duplicate Charge and Credit/Refund fixtures, and Usage Spike blocked gaps
- [M5 Polish + Portfolio Readiness](docs/specs/m5-polish-portfolio-readiness.md) - seeded demo baseline, live reset, and interview walkthrough expectations
- [M6 Governed Runtime + Financial Safety](docs/specs/m6-governed-runtime-financial-safety.md) - planned upgrade from trace kernel to governed action runtime
- [M7 Eval Contracts + Scenario Unblocking](docs/specs/m7-eval-contracts-scenario-unblocking.md) - planned compliance checks and supporting scenario readiness gates
- [M9 LLM-Planned Tool Plan](docs/specs/m9-llm-planned-tool-plan.md) - LLM investigation planning with backend contract verification
- [M10 Eval Regression History](docs/specs/m10-eval-regression-history.md) - seeded baseline comparison, eval run history, and model/prompt/policy diff snapshots

## Out of scope for v1

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
