# M2 Backend Domain + Mock Billing

## Purpose

M2 replaces the M1 static Duplicate Charge workbench data with durable mock billing data in
Postgres and read-only FastAPI resource APIs. It keeps Duplicate Charge as the polished golden path
while seeding Usage Spike and Credit/Refund Dispute as realistic supporting backend fixtures.
Credit/Refund Dispute now uses those fixtures for the second governed workflow; Usage Spike remains
for later agent and eval milestones.

M2 is not a live agent milestone. It does not add approval decisions, mock mutation execution, live
LLM calls, public APIs, real payment integrations, or customer message sending.

## Data Model

M2 adds normalized tables for the v1 domain glossary:

- tickets, customer accounts, invoices, charges, usage records, credit ledger entries, and policy
  rules.
- agent runs and tool traces for audit-ready investigation history.
- approval requests and mock mutations for approval-gated financial action evidence.
- eval cases and eval results for later offline scoring.

Money is stored as integer minor units plus currency. Event times are stored as timezone-aware UTC
timestamps. Billing and usage periods are stored as date ranges. API responses may include display
strings for the current UI.

Core entity relationships stay relational. JSONB is allowed only for semi-structured trace and eval
metadata, such as evidence refs, policy refs, approval refs, grading criteria, and dimension scores.

## APIs

M2 exposes root internal read APIs:

- `GET /tickets`
- `GET /tickets/{ticket_id}`
- `GET /tickets/{ticket_id}/billing-evidence`
- `GET /tickets/{ticket_id}/agent-runs`
- `GET /agent-runs/{agent_run_id}/traces`
- `GET /approvals`
- `GET /mock-mutations`
- `GET /eval-cases`
- `GET /eval-results`

Missing single resources return `404`. Empty collections return `200` with an empty array. M2 does
not register approve, reject, or mutation execution placeholders.

## Seed Data

`make seed` runs migrations and deterministically rebuilds rows marked with the M2 demo seed marker.
It does not wipe unrelated local domain rows.

The seed includes:

- three complete tickets: Duplicate Charge, Usage Spike, and Credit/Refund Dispute.
- one Duplicate Charge preview agent run with final internal and customer draft outputs.
- Duplicate Charge tool traces and one pending approval request.
- one historical read-only Credit/Refund mock mutation on a hidden eval fixture.
- nine eval case definitions, three per scenario family.
- one Duplicate Charge static preview eval result; other cases have no run until M4.

## Frontend

Next.js fetches FastAPI resources server-side with `cache: no-store` and uses page-level adapters to
assemble UI view models. The workbench remains focused on `/` and the Duplicate Charge ticket.
Supporting scenario tickets appear in the API-backed ticket list but are not full selectable detail
flows in M2.

If domain data cannot be loaded, the UI shows explicit unavailable states. It does not silently fall
back to static M1 data.

Approval controls remain visible but disabled. Eval Lab lists all nine seeded cases grouped by
scenario, with only the Duplicate Charge case showing an M2 preview result.

## Verification

Default `make test` remains fast and does not require Docker/Postgres. `make test-db` starts local
Postgres, runs migrations, seeds demo data, and verifies key read APIs against the real database.
