# MeterDesk Implementation Roadmap

## Purpose

This roadmap defines the implementation sequence for MeterDesk v1. It is stable project guidance for future AI coding sessions, not a detailed database schema, tool schema, UI design spec, or sprint task list.

The roadmap should be read with:

- `docs/specs/product-scope.md`
- `docs/specs/system-architecture.md`
- `docs/specs/agent-governance.md`
- `docs/specs/eval-strategy.md`

If a milestone needs deeper design, write a focused spec before implementation.

## Implementation Strategy

Use a **Vertical Skeleton** approach.

MeterDesk has one central risk: the product only works if frontend workflow, backend domain state, governed agent behavior, approval gates, audit traces, and eval scoring connect into one credible system. A vertical skeleton exposes integration problems early and keeps every milestone demonstrable.

This is preferred over:

- **Backend First**: technically orderly, but delays product validation and makes the project look abstract for too long.
- **Demo First**: visually fast, but risks creating a polished static UI that is expensive to connect to governance and eval behavior later.

Each milestone should produce a working, reviewable slice. Later milestones may replace static data and scripted behavior with real backend, agent, and eval functionality, but they should preserve the same product shape.

## M0: Project Scaffold

### Goal

Establish a stable full-stack development foundation for future AI coding.

### Deliverables

- Next.js frontend scaffold.
- FastAPI backend scaffold.
- Postgres development setup.
- Shared repo commands for install, dev, test, lint, and seed.
- Environment file examples for local development.
- Basic health checks for frontend and backend.
- README setup instructions updated with real commands.

### Acceptance Criteria

- A developer can start frontend and backend locally from documented commands.
- Backend health check returns a successful response.
- Frontend renders a minimal MeterDesk shell.
- Postgres can be started locally and reached by the backend.
- Test and lint commands exist even if early coverage is minimal.

### Explicit Deferrals

- Do not build the full Ticket Workbench in M0.
- Do not add live LLM calls in M0.
- Do not define detailed tool schemas in M0.
- Do not add real payment, support, or messaging integrations.

## M1: Static Golden Path Workbench

### Goal

Create a clickable Duplicate Charge workbench that demonstrates the intended product flow before backend domain depth is complete.

### Deliverables

- Ticket Workbench route with ticket list and ticket detail.
- Static Duplicate Charge scenario data.
- Billing evidence sections for account, invoices, charges, credits, usage summary, and policy citation.
- Static agent action timeline with tool-like trace entries.
- Draft internal resolution and draft customer reply panels.
- Approval card showing a proposed refund or credit in pending state.
- Navigation entries for Approval Queue and Eval Lab, even if those pages are thin in this milestone.

### Acceptance Criteria

- A reviewer can follow the Duplicate Charge golden path without reading code.
- The UI communicates that the agent is investigating billing evidence, not chatting freely.
- The proposed financial action is visibly approval-gated.
- Customer-facing text is visibly draft-only.
- Static trace entries show permission categories and evidence references.

### Explicit Deferrals

- Do not connect the workbench to Postgres in M1.
- Do not add live agent execution in M1.
- Do not implement final visual design polish in M1.
- Do not build a standalone tool registry editor.

## M2: Backend Domain + Mock Billing

Focused implementation spec: `docs/specs/m2-backend-domain-mock-billing.md`.

### Goal

Replace static workbench data with durable mock domain data and resource APIs.

### Deliverables

- Postgres-backed records for tickets, customer accounts, invoices, charges, usage records, credit ledger entries, policy rules, agent runs, tool traces, approvals, mock mutations, eval cases, and eval results.
- Seed data for Duplicate Charge, Usage Spike, and Credit/Refund Dispute scenarios.
- FastAPI resource APIs for ticket list/detail, billing evidence, approvals, agent run inspection, mock mutations, and eval case/result reads.
- Frontend data loading from FastAPI for the workbench and approval queue.

### Acceptance Criteria

- Ticket Workbench reads seeded Duplicate Charge data from backend APIs.
- Approval Queue reads real approval records from backend APIs.
- Mock billing data is realistic enough to explain amounts, dates, statuses, and policy reasoning.
- Tool traces and mock mutations can be persisted, queried, and linked to tickets.
- Usage Spike and Credit/Refund Dispute seed data exist for later agent and eval work.

### Explicit Deferrals

- Do not add live agent calls in M2.
- Do not create a public external API.
- Do not build large-scale data modeling beyond the v1 domain glossary.
- Do not add pgvector or large-scale RAG.

## M3: Governed Agent Loop

Focused implementation spec: `docs/specs/m3-governed-agent-loop.md`.

### Goal

Implement the first real agent-governed investigation loop for the Duplicate Charge golden path.

### Deliverables

- OpenAI-compatible provider boundary with one live provider.
- Backend-controlled tool layer using the existing tool permission categories.
- Trace envelope persistence for each agent run and tool call.
- Policy citation handling through explicit policy records and eligibility checks.
- Agent output for recommendation, internal resolution draft, and customer reply draft.
- Approval request creation for proposed refund or credit actions.
- Mock refund or credit mutation execution only after approval.

### Acceptance Criteria

- Running the agent on the Duplicate Charge ticket produces a persisted agent run.
- Tool calls are recorded with permission category, input summary, output summary, evidence references, and errors when applicable.
- A refund or credit proposal creates an approval request instead of mutating immediately.
- Rejected approval requests do not create mock mutations.
- Approved approval requests create at most one mock mutation.
- Customer reply output remains draft-only and avoids promising unapproved financial action.

### Explicit Deferrals

- Do not implement multi-provider model routing.
- Do not require a real MCP server.
- Do not expose agent tools directly to the frontend.
- Do not send customer messages.
- Do not add real payment mutations.

## M4: Eval Lab

### Goal

Add offline evals that score agent outcome quality and trace behavior.

### Deliverables

- 9 offline eval cases: 3 Duplicate Charge, 3 Usage Spike, and 3 Credit/Refund Dispute.
- Deterministic graders for outcome correctness, required evidence, policy citation, and approval routing.
- Limited LLM-as-judge evaluation for draft clarity, tone, and unsupported promises.
- Eval result persistence linked to agent runs and traces.
- Eval Lab page showing cases, latest results, dimension scores, failed checks, missing evidence, and trace links.

### Acceptance Criteria

- Duplicate Charge eval cases pass deterministic checks for required evidence, policy compliance, and approval routing.
- Supporting scenario eval failures are visible and actionable.
- Any mutation-before-approval behavior is treated as a blocking failure.
- Eval Lab shows both final output scores and trace/evidence scores.
- Eval results include model, prompt, and policy version references when available.

### Explicit Deferrals

- Do not build full trace replay or trace diffing.
- Do not build large eval datasets.
- Do not add online production monitoring.
- Do not build pairwise multi-provider eval dashboards.

## M5: Polish + Portfolio Readiness

### Goal

Turn the working system into a coherent portfolio-ready project.

### Deliverables

- Focused unit and integration tests for core backend workflows.
- Frontend tests for the golden path, approval queue, and eval lab basics.
- Empty, loading, error, rejected approval, and missing evidence states.
- Demo seed command and reset command.
- README walkthrough updated with exact local setup, demo flow, and eval commands.
- UI polish for Support Workbench information hierarchy, trace readability, and approval clarity.

### Acceptance Criteria

- A fresh checkout can run the demo using documented commands.
- The Duplicate Charge golden path is stable enough for a live walkthrough.
- Approval-gated mock mutation behavior is test-covered.
- Eval commands produce readable output and stored results.
- README explains what to inspect and why it matters.

### Explicit Deferrals

- Do not add enterprise multi-tenancy.
- Do not add deployment and production monitoring unless a later deployment spec is approved.
- Do not add security incident or SLA incident workflows.
- Do not expand beyond the confirmed v1 product surfaces.

## Cross-Milestone Rules

- Preserve Duplicate Charge as the v1 golden path.
- Preserve Usage Spike and Credit/Refund Dispute as supporting scenarios.
- Keep customer replies draft-only.
- Keep high-risk refund and credit mutations approval-gated.
- Keep all external systems mock-only in v1.
- Preserve traceability for agent runs, tool calls, policy citations, approvals, and mock mutations.
- Keep evals aligned with both final outcome quality and trace behavior.
- Keep MCP adapter readiness at the tool-layer boundary without requiring a real MCP server.
- Avoid pgvector, large-scale RAG, multi-provider gateways, and enterprise multi-tenancy unless a later approved spec changes scope.

## When To Add More Specs

Add a focused spec before implementing any of these:

- Detailed UI layout, interaction, visual design, or component system.
- Detailed database schema and migrations beyond the minimal v1 domain.
- Detailed agent tool names, JSON schemas, and payload contracts.
- Real MCP server implementation.
- Deployment, production monitoring, or hosted demo infrastructure.
- Real payment, support, messaging, or accounting integrations.
- Security incident, SLA incident, or API key leak workflows.

This roadmap should guide sequencing. It should not be used to smuggle deferred product scope into v1.
