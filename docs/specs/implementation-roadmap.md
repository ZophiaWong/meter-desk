# MeterDesk Implementation Roadmap

## Purpose

This file is the stable entry point for MeterDesk delivery history and the current implementation
phase. Read it with the product scope, system architecture, agent governance, and eval strategy.

Detailed requirements live in focused feature specs. Historical milestone specs preserve design
context but are not current sources of truth.

## Completed V1 Program

MeterDesk used a vertical-skeleton strategy so the workbench, backend domain, governed agent,
approval safety, audit traces, and eval scoring became demonstrable together.

| Milestone | Delivered outcome | Historical context |
|---|---|---|
| M0 | Next.js/FastAPI/Postgres scaffold and shared local commands | Roadmap only |
| M1 | Static Duplicate Charge support workbench | Roadmap only |
| M2 | Durable domain data, realistic mock billing, resource APIs | [Archived spec](../archive/milestones/m2-backend-domain-mock-billing.md) |
| M3 | Governed Duplicate Charge agent loop and approval-gated mock mutation | [Archived spec](../archive/milestones/m3-governed-agent-loop.md) |
| M4 | Offline deterministic Eval Lab | [Archived spec](../archive/milestones/m4-eval-lab.md) |
| M5 | Seeded portfolio demo, reset path, and presentation polish | [Archived spec](../archive/milestones/m5-polish-portfolio-readiness.md) |
| M6 | Governed runtime metadata and financial safety | [Archived spec](../archive/milestones/m6-governed-runtime-financial-safety.md) |
| M7 | Run compliance and Credit/Refund scenario unblocking | [Archived spec](../archive/milestones/m7-eval-contracts-scenario-unblocking.md) |
| M9 | LLM-planned, backend-verified investigation plans | [Archived spec](../archive/milestones/m9-llm-planned-tool-plan.md) |
| M10 | Eval regression history and compact version/trace diffs | [Archived spec](../archive/milestones/m10-eval-regression-history.md) |

M8 was never assigned. The historical files record milestone intent and may be superseded by the
foundational specs and current code.

## Current Phase: Post-M10 Hardening

The active phase is [Post-M10 Hardening](hardening/roadmap.md). Its purpose is to add repeatable
engineering evidence without broadening MeterDesk into a generic platform or real billing system.

The first workstream is
[P0-01 CI and Runtime Baseline](hardening/p0-01-ci-runtime-baseline.md). Its workflow, non-root
images, five-service Compose runtime, smoke harness, Make targets, runbook, and link checker are
implemented on the candidate branch. Real API/Web builds and repeated isolated no-key smoke runs are
locally verified, as are branch-wide lint, test, and database checks. P0-01 remains the active
workstream while the first successful four-job GitHub Actions evidence is promoted, the resulting
final head is reverified, and the PR is merged. Later workstreams cover trusted approval identity,
persistence lifecycle, workflow state, recoverable execution, provider resilience, operational
evidence, a repository-local networked mock tool boundary, auditable context, and focused security
and failure regression checks.

The [Engineering Evidence Matrix](../evidence/engineering-evidence-matrix.md) records whether each
capability is Existing, a Gap, Planned, Verified, or Deferred. It does not define requirements.

## Delivery Protocol

Each hardening workstream follows this sequence:

1. re-read current code and foundational specs;
2. write or refresh one focused feature spec;
3. escalate any scope or contract conflict to the maintainer;
4. obtain design approval;
5. generate a fresh implementation plan from the current baseline;
6. implement one independently reviewable change;
7. run and report the required verification with actual output;
8. update affected foundational specs and the evidence matrix;
9. re-review downstream assumptions before planning the next workstream.

Do not combine authentication, workflow state redesign, async execution, observability, networked
tool boundaries, and eval expansion in one change. A detailed plan becomes stale when its file paths,
public schemas, repository signatures, migration head, services, state names, or prerequisite commits
change.

## Cross-Phase Rules

- Preserve Duplicate Charge as the golden path and keep supporting scenarios on the same workbench.
- Keep customer replies draft-only and financial mutations mock-only and approval-gated.
- Keep frontend, backend, orchestration, mock systems, and audit persistence behind clear interfaces.
- Keep one OpenAI-compatible live provider boundary; do not add provider routing.
- Keep critical governance and eval decisions deterministic.
- Do not add real payment/support writes, enterprise multi-tenancy, pgvector, large-scale RAG, a
  generic tool marketplace, or a broad MCP server.
- P0-06 may prove a network boundary only through a repository-local mock billing HTTP service. A
  real third-party adapter requires a separate product-scope decision.
- Eval Lab retains nine canonical business cases. Later hardening may add 30 or more focused
  engineering regression fixtures/checks without creating new product scenario cards.

## When to Add a Focused Spec

Write and approve a focused spec before changing detailed database schemas, workflow states,
authentication/RBAC, async runtime contracts, provider failure semantics, observability schemas,
typed tool interfaces, context/evidence contracts, detailed UI behavior, real integrations,
deployment, or production monitoring.

The roadmap must not be used to smuggle deferred scope into v1.
