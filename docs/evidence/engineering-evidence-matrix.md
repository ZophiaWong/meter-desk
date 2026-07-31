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

`Existing` does not mean the current branch has passed every command. During the 2026-07-31
documentation review, API tests reported 68 passed and 6 skipped, API lint stopped on five existing
Ruff findings, frontend tests were blocked by the local WSL/Node environment, and Docker was not
available in the local WSL distribution.

## Hardening Target Evidence

| Requirement | Current state | Target evidence | Workstream | Status |
|---|---|---|---|---|
| PR backend quality checks | No workflow | `backend-quality` Ruff and pytest job result | P0-01 | Planned |
| PR frontend quality/build checks | No workflow | `frontend-quality` lint, typecheck, Vitest, build result | P0-01 | Planned |
| Automated Postgres integration | Local `make test-db` only | `database-integration` migration, seed, checker logs | P0-01 | Planned |
| Locked non-root API image | No Dockerfile | Image build plus non-root process check | P0-01 | Planned |
| Locked non-root Web image | No Dockerfile | Image build plus non-root process check | P0-01 | Planned |
| Seeded full-stack runtime | Compose starts only Postgres | Project-isolated `make container-smoke` endpoint evidence | P0-01 | Planned |
| CI without provider credentials | No CI evidence | Smoke environment and missing-key assertions | P0-01 | Planned |
| Client cannot choose approver | `decided_by` comes from request body | Forged actor test and persisted server principal | P0-02 | Gap |
| Approval role enforcement | No route role dependency | 401/403/success tests for operator, approver, admin | P0-02 | Gap |
| Approval actor audit | Untrusted actor string | Subject, role, request ID persistence evidence | P0-02 | Gap |
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
