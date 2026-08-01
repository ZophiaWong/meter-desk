# MeterDesk Post-M10 Hardening Roadmap

## Status

- Program status: approved next phase.
- Active workstream: P0-01 CI and Runtime Baseline; runtime implementation is present locally and
  verification/merge is in progress.
- Product scope change: none.
- Interview and demo collateral refresh: deferred until the hardening program is complete; this
  collateral is not authoritative for current workstream sequencing.
- Detailed implementation plans are valid only for the code baseline they reviewed.

## Purpose

This roadmap advances MeterDesk from a working governed-agent portfolio product to a project with
repeatable engineering evidence. It focuses on build reproducibility, trusted approval identity,
explicit workflow semantics, recoverable execution, failure handling, operational telemetry, typed
tool boundaries, auditable context, and deterministic security and resilience checks.

It does not turn MeterDesk into a general agent platform, billing CRM, large-scale RAG system,
multi-provider gateway, real payment processor, or enterprise multi-tenant SaaS product.

## Inherited Product Constraints

Every workstream must preserve these requirements unless the maintainer first approves a conflicting
change to the foundational specs:

- Duplicate Charge remains the v1 golden path.
- Credit/Refund Dispute remains a supporting governed workflow.
- Usage Spike remains an explicit coverage gap until separately specified and implemented.
- The backend owns evidence access, deterministic billing decisions, approval gates, and mutations.
- Customer-facing replies remain draft-only.
- Financial mutations remain mock-only and require explicit human approval.
- The provider boundary supports one live OpenAI-compatible provider; no multi-provider gateway.
- No pgvector, large-scale RAG, generic plugin marketplace, or broad MCP server.
- New behavior requires automated tests; schema changes require Alembic migrations.
- Runtime state must define terminal states, retries, and idempotency.
- External dependencies must define timeout, retry, error mapping, and trace propagation.
- Each workstream updates affected foundational specs and the evidence matrix in the same change.

## Current Baseline

The current repository already demonstrates a ticket-first workbench, backend-owned deterministic
decisions, bounded LLM planning, approval-gated mock financial actions, action fingerprints,
governance traces, compliance checks, and eval regression history.

P0-01 now supplies API/Web runtime images, a seeded five-service Compose path, an isolated no-key
smoke harness, and a four-job GitHub Actions workflow contract. Local image and smoke evidence is
verified, as are final candidate-branch lint, test, and database evidence; public CI evidence
remains open.
The baseline still lacks trusted approval identity, application-lifetime database resources,
explicit workflow state semantics, background execution, provider resilience, operational
telemetry, typed networked tool execution, structured context snapshots, and broad
security/failure/concurrency regression coverage.

## Workstream Sequence

| Order | Workstream | Primary outcome |
|---:|---|---|
| 1 | P0-01 CI and Runtime Baseline | Reproducible quality gates, images, seeded Compose runtime, and smoke evidence |
| 2 | P0-02 Authentication and Approval RBAC | Server-derived actor identity and approval role enforcement |
| 3 | P1-04 Persistence Foundation | Lifespan-managed async persistence and real Postgres concurrency harness |
| 4 | P0-03 Workflow State Consistency | Explicit investigation/workflow states and failure-safe transitions |
| 5 | P0-04 Async Agent Runtime | Recoverable queued execution, progress, cancellation, and replay safety |
| 6 | P1-01 Provider Resilience | Async provider client, timeout taxonomy, retries, deadlines, and usage metadata |
| 7 | P0-05 Observability and Cost | Correlated telemetry for latency, retries, tokens, cost, and approval wait |
| 8 | P0-06 Networked Mock Read Integration and Typed Tool Runtime | Typed tool execution across a repository-local HTTP boundary |
| 9 | P1-03 Context and Evidence Model | Versioned evidence references and auditable context bundles |
| 10 | P1-02 Eval, Security, and Draft Safety Expansion | Focused adversarial, failure, concurrency, and bilingual regression evidence |

## Dependency Model

```text
P0-01 CI and Runtime Baseline
    +-- P0-02 Authentication and Approval RBAC
    +-- P1-04 Persistence Foundation
            +-- P0-03 Workflow State Consistency
                    +-- P0-04 Async Agent Runtime
                            +-- P1-01 Provider Resilience
                            +-- P0-05 Observability and Cost

P0-03 Workflow State Consistency
    +-- P0-06 Networked Mock Read Integration and Typed Tool Runtime
            +-- P1-03 Context and Evidence Model

P0-02 Authentication and Approval RBAC
    +-- P0-04 Async Agent Runtime
    +-- P0-05 Observability and Cost
    +-- P0-06 Networked Mock Read Integration and Typed Tool Runtime

All completed foundations
    +-- P1-02 Eval, Security, and Draft Safety Expansion
```

## Workstream Contracts

### P0-01 — CI and Runtime Baseline

Implemented artifacts are `.github/workflows/ci.yml`, `.dockerignore`, the API and Web Dockerfiles,
`compose.yaml`, `scripts/container-smoke.sh`, the five `container-*` Make targets, the container
runbook, and the Markdown link checker. Compose runs `postgres`, `migrate`, `seed`, `api`, and `web`;
both application images run as `10001:10001`, with the API repository layout preserved at
`/workspace/apps/api`. Local image builds, isolated seeded runtime, no-provider 503 behavior, and
cleanup/default-volume preservation are verified. All four GitHub jobs remain Planned until a real
remote run succeeds; local branch-wide quality/database verification is complete. No agent,
approval, mutation, governance, trace, or eval behavior changed.

Detailed requirements: [P0-01 CI and Runtime Baseline](p0-01-ci-runtime-baseline.md).

### P0-02 — Authentication and Approval RBAC

Replace client-supplied approval identity with a server-verified local/demo principal. Define
`support_operator`, `approver`, and `admin` roles; enforce 401/403 behavior; and persist auditable
actor subject, role, and request correlation. Do not add enterprise identity administration, SCIM,
social login, or multi-tenancy.

### P1-04 — Persistence Foundation

Move `AsyncEngine` and `async_sessionmaker` into FastAPI lifespan, replace synchronous readiness
probes with an async database query, define pool configuration, and establish reusable real-Postgres
concurrency tests for approve/approve and approve/reject behavior. Do not redesign every repository
or introduce distributed transactions.

### P0-03 — Workflow State Consistency

Define whether `AgentRun` remains an investigation attempt with a separate case workflow aggregate,
or becomes the complete workflow state machine. Specify states, terminal semantics, approval linkage,
partial-failure behavior, transaction/outbox choice, migration, API/UI mapping, and transition tests
before implementation. The architecture glossary currently favors a separate workflow aggregate,
but the focused spec must make the final decision.

### P0-04 — Async Agent Runtime

Separate execution from the HTTP lifecycle with a fast accepted response, queue/worker boundary,
progress events, checkpoints, stale-job detection, cancellation, retry/replay, idempotent enqueue, and
crash-recovery evidence. Do not build an arbitrary workflow platform or multi-agent scheduler.

### P1-01 — Provider Resilience

Replace the thread-wrapped blocking provider call with an async client contract. Define connect,
read, write, and total timeouts; retryable error classes; bounded backoff and jitter; an overall
deadline; cancellation propagation; provider request IDs; sanitized failures; and structured usage
metadata. Do not add provider routing or automatic fallback.

### P0-05 — Observability and Cost

Correlate request, trace, run, and approval identifiers across API, worker, planner, tools, provider,
and approval operations. Record or emit latency, retries, tokens, estimated cost, queue delay, and
approval wait without logging sensitive prompts or billing evidence by default. A local collector or
dashboard is evidence, not a commitment to a production SRE platform.

### P0-06 — Networked Mock Read Integration and Typed Tool Runtime

Introduce a repository-local mock billing HTTP service and a typed `ToolSpec`/registry/executor
boundary. Prove service authentication, timeout, retry, rate-limit, schema-error, error-sanitization,
and trace-propagation behavior without calling Stripe or any other real external provider. External
writes, payment mutations, customer messaging, planner-driven approval/mutation, and a generic tool
marketplace remain impossible.

This scope is an explicit maintainer decision resolving the original handoff's conflict with the v1
mock-system boundary. A real third-party read adapter requires a separate product-scope decision.

### P1-03 — Context and Evidence Model

Build typed, versioned `EvidenceRef` and `ContextBundle` contracts on the P0-06 tool output boundary.
Capture selected and excluded evidence, selection reasons, redactions, trust classification, token
budget, source version/digest, context hash, and an eval-compatible snapshot. Do not add long-term
memory, vector memory, or large-scale RAG.

### P1-02 — Eval, Security, and Draft Safety Expansion

Keep the nine canonical business scenario cases in Eval Lab. Add at least 30 focused regression
fixtures/checks across prompt injection, policy spoofing, PII leakage, malformed provider output,
timeouts, retry exhaustion, concurrent approval, duplicate delivery, worker recovery, Chinese and
English drafts, indirect financial promises, and latency/cost thresholds. These fixtures are
engineering regression evidence, not 30 new product scenario cards.

This split is an explicit maintainer decision resolving the original handoff's ambiguity with the
v1 nine-case eval contract. Critical deterministic checks run in CI; any broader suite may remain an
explicit optional target.

## Required Gates

### Gate A — Reproducible Verification

P0-01 must provide automated backend quality, frontend quality/build, Postgres integration, image
build, and seeded full-stack smoke evidence without a real provider key.

Status: implementation and local lint, test, database, and runtime evidence are present. The gate
remains open only for successful remote results from `backend-quality`, `frontend-quality`,
`database-integration`, and `container-smoke`.

### Gate B — Trusted Actor

P0-02 must ensure the request body cannot choose the approver, role enforcement is server-side, and
persisted audit identity is traceable before approval events enter later runtime or telemetry work.

### Gate C — Persistence Foundation

P1-04 must provide application-lifetime async persistence, async readiness, and stable Postgres
transaction/concurrency tests before background workers write workflow tables.

### Gate D — Explicit Workflow Semantics

P0-03 must define ownership of workflow state, valid transitions, terminal states, approval-write
failure semantics, migrations, and retry/replay idempotency before the orchestrator moves to a worker.

### Gate E — Recoverable Runtime

P0-04 must provide non-blocking start, observable progress, cancellation, checkpoints/recovery, and
duplicate-delivery safety.

### Gate F — Operational Evidence

P1-01 and P0-05 must distinguish timeout/retry/deadline/cancellation and correlate provider/tool
latency, tokens/cost, queue delay, and approval wait with domain IDs.

### Gate G — Networked Mock Boundary

P0-06 must add exactly one repository-local read-only HTTP boundary with typed contracts and tested
auth, timeout, retry, rate-limit, schema-error, sanitization, and trace propagation behavior.

## Parallelization Rules

- After P0-01, P0-02 and P1-04 feature specs may be prepared in parallel, but their implementations
  should remain independently reviewable.
- P0-03 and P0-04 must not be implemented in parallel because queue payloads, event schemas,
  checkpoints, and resume semantics depend on the final state model.
- P0-04 and P0-06 must not be implemented together because both change the failure surface.
- P1-02 is not a substitute for tests in earlier workstreams; every workstream owns its regressions.
- Default delivery is one focused spec, one fresh implementation plan, and one reviewable change.

## Re-Review Points

After each listed workstream, re-read current code and refresh downstream assumptions:

- **P0-01:** Make targets, Compose services, CI commands, Docker runtime paths.
- **P0-02:** approval request schema, route dependencies, frontend request boundary, actor fields.
- **P1-04:** engine/session lifecycle, transactions, test fixtures, concurrency helpers.
- **P0-03:** run/workflow models, response status, approval linkage, migrations, transitions.
- **P0-04:** worker framework, event/checkpoint model, retries, cancellation, deployment topology.
- **P1-01/P0-05:** provider interface, telemetry field names, usage and correlation metadata.
- **P0-06:** tool contracts, adapter output, structured evidence, network failure mapping.
- **P1-03:** context schema, redaction, evidence versioning, eval compatibility.

A detailed implementation plan is stale if files move, public schemas or repository signatures
change, the migration head changes, service/state names change, test commands change, or prerequisite
work has not merged.

## Evidence and Specification Sync

Each workstream is complete only when:

1. its acceptance criteria have implementation and automated evidence;
2. every planned verification command has been run and reported with actual output;
3. migrations, environment documentation, runbooks, and foundational specs are updated as needed;
4. seeded replay and live-provider behavior remain honestly distinguished;
5. the engineering evidence matrix names the actual files, checks, and runtime artifacts;
6. unresolved limitations are recorded without weakening scope or assertions.
