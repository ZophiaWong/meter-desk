# M3 Governed Agent Loop

> **Archive status:** Historical implementation spec from the completed M0-M10 program. It is
> non-authoritative and cannot override `AGENTS.md`, current foundational specs, or an approved
> active workstream spec. Start from the [documentation index](../../README.md).

## Purpose

M3 implements the first real governed agent loop for the Duplicate Charge golden path. FastAPI owns
the workflow, backend-controlled tools, trace persistence, approval gates, and mock mutation
execution. The live OpenAI-compatible provider produces strict structured recommendation and draft
text only; it does not choose tools or decide refund amount.

M3 did not introduce LangGraph, LLM-directed tool choice, real payment mutations, customer message
sending, MCP server runtime, auth, or multi-provider routing. M9 later adds bounded LLM
investigation planning for read and decision-request actions only; deterministic decisions,
approval creation, and mutation safety remain backend-owned.

## Architecture

- `POST /tickets/{ticket_id}/agent-runs` starts a synchronous Duplicate Charge run.
- `AgentRunOrchestrator` creates the run, reads evidence and prior actions, evaluates the
  deterministic duplicate-charge decision, calls the provider for strict structured output, persists
  focused traces, and creates an approval request when a refund is warranted.
- The deterministic decision tool is authoritative for outcome category, refund amount, target
  charge, evidence refs, policy refs, and whether approval is required.
- Provider configuration is required for real runs through `OPENAI_API_KEY` and `OPENAI_MODEL`;
  `OPENAI_BASE_URL` is optional for OpenAI-compatible endpoints.
- Missing provider configuration returns `503` before a run is created. Provider validation failures
  after orchestration starts retry once, persist a failed run with trace context, and create no
  approval request.

## Data And API Contracts

- M3 adds nullable failed-run outputs plus `agent_runs.error_state`.
- Approval requests and mock mutations store `action_metadata` for the invoice, target charge, and
  action basis without over-normalizing payment-specific columns.
- Approval decisions record `decided_by`, `decision_note`, `decision`, and `decided_at` without
  adding authentication.
- `GET /approvals` supports `status=pending|approved|rejected|all` and `ticket_id`.
- `GET /mock-mutations` supports `ticket_id`.
- `POST /approvals/{id}/approve` marks the approval terminal and atomically creates one mock
  mutation. Repeated approve calls return the existing mutation.
- `POST /approvals/{id}/reject` marks the approval terminal and creates no mutation.
- Opposite terminal actions return `409`.

## Seed And UI Behavior

The original M3 seed started `TCK-1042` with durable ticket and billing evidence only. M5 supersedes
this demo seed behavior for portfolio readiness by seeding a completed walkthrough sample and
providing a live reset command. The live governed run behavior itself remains unchanged.

The workbench shows:

- billing evidence before the run.
- run status and focused trace entries after execution.
- draft-only internal and customer-facing output after a successful provider response.
- pending, approved, or rejected approval state.
- mock mutation results only after approval.

Approval Queue defaults to pending approvals and submits approve/reject decisions through Next.js
server actions. Customer-facing text remains draft-only and is never sent.

## Verification

Default API tests use an injected fake provider and require no network credentials. They cover
decision-tool outcomes, run creation, provider validation failure, unsupported scenarios, pending
approval rerun blocking, rejection without mutation, idempotent approval execution, and high-risk
mutation trace persistence.

`make test-db` runs migrations, seeds M3 demo data, and verifies the Postgres-backed M3 seed state.
Live provider behavior is intentionally not part of default tests.
