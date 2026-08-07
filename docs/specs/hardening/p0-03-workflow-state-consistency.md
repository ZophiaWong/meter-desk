# P0-03 Workflow State Consistency

## Status

- Priority: P0.
- Design status: approved for implementation.
- Implementation status: implemented on the P0-03 evidence-closure branch; no production behavior
  or Alembic `20260806_0009` changes are part of the closure work.
- Verification status: Verified on the implementation head. The evidence-finalization head records
  the complete local gate, 12 injected rollback points, 12 real migration databases, and the
  successful four-job implementation-head CI run; the final documentation head must still pass the
  same CI gate before merge.
- Depends on: P1-04 Persistence Foundation, Alembic head `20260802_0008`.
- Blocks: P0-04 Async Agent Runtime.
- Product scope change: none. Mutations remain mock-only, approval-gated, and never customer-facing.

## Decision

`CaseWorkflow` is the aggregate that owns the state of one ticket-processing cycle. `AgentRun` is
only one investigation attempt inside that cycle. A retry after a recoverable failure creates a new
run in the same workflow; a rerun after a terminal cycle creates a new workflow with
`previous_workflow_id`.

The state vocabulary is deliberately separate from approval row vocabulary:

```text
investigating | needs_retry | awaiting_approval | completed_no_action
rejected | mock_executed | failed | cancelled
```

`approved` is never a Workflow state. Approval approval and mock execution are one atomic command,
so `awaiting_approval` moves directly to `mock_executed`.

## State machine

| From | Allowed destinations | Meaning |
|---|---|---|
| initial | `investigating` | A new cycle has accepted an investigation attempt. |
| `investigating` | `needs_retry`, `awaiting_approval`, `completed_no_action`, `failed`, `cancelled` | The attempt produced a recoverable result, a governed decision, an explicit no-action outcome, an unrecoverable failure, or cancellation. |
| `needs_retry` | `investigating`, `failed`, `cancelled` | A subsequent attempt may reuse this cycle. |
| `awaiting_approval` | `mock_executed`, `rejected`, `cancelled` | A trusted human decision closes the financial gate. Pending approval is withdrawn on cancellation. |
| terminal states | none | Terminal cycles cannot be reopened. |

Provider, planner/verifier, and evidence failures during the active run use `needs_retry` with a
stable reason code. `failed` is reserved for an explicitly unrecoverable condition, exhausted
retry policy, or a migration-discovered missing approval. A valid business conclusion such as
`insufficient_evidence_human_review` is `completed_no_action`, not a technical failure.

Each workflow stores cycle number, ticket, status, stable reason code/detail, version, transition
sequence, origin, predecessor, and lifecycle timestamps. A partial unique index permits at most one
non-terminal workflow for a ticket. Every transition is append-only and stores from/to status,
reason, trusted actor/request provenance, and optional run/approval/mutation references. Version and
transition sequence increase together.

## Atomic repository commands

`CaseWorkflowService` in `apps/api/src/meterdesk_api/workflows.py` is the single transition rule
source. Repositories expose narrow commands rather than a general Unit of Work, outbox, or event
sourcing layer:

- `start_or_replay_run`: requires `Idempotency-Key`; same ticket/key replays the original run with
  `200`, a new operation returns `201`, a different key conflicts with running/awaiting work, and a
  `needs_retry` workflow receives a new run in the same cycle.
- `finalize_run`: one transaction writes run output, final governance traces, approval (when
  required), and the Workflow transition.
- `fail_run`: records a failed attempt and moves the Workflow to `needs_retry` or `failed`.
- `cancel_workflow`: Support/Admin-only; cancels a running attempt, withdraws a pending approval,
  and records the cancellation transition.
- `approve_and_execute`: locks Workflow then Approval, and in one transaction writes trusted
  approval audit, mock mutation, mutation trace, and `mock_executed`.
- `reject_approval`: locks Workflow then Approval, records trusted rejection and `rejected`.

Competing commands are linearized by the locked Workflow row and must be equivalent to one legal
serial order. Where both commands are terminal, the first committed command wins and the loser
returns `409`; a successful `awaiting_approval` finalization may be followed by a valid cancellation,
which withdraws its pending approval. A globally unique executed action fingerprint continues to
forbid repeated mutations. A rejected or withdrawn fingerprint may be proposed again in a new
workflow, but it must receive a fresh approval.

## Migration and compatibility

`20260806_0009_p0_03_workflow_state_consistency.py` adds nullable links and tables first, runs a
transactional preflight/backfill, then adds foreign keys, checks, non-null constraints, and unique
indexes. The backfill is fail-closed:

- pending approval -> `awaiting_approval`;
- rejected approval -> `rejected`;
- approved approval with its unique mutation -> `mock_executed`;
- running/failed attempt -> `needs_retry`; an interrupted running attempt is marked failed with
  `migration.interrupted_run`;
- known no-action outcomes -> `completed_no_action`;
- known approval-required outcome without approval -> `failed` with `migration.approval_missing`;
- a legal historical approval/mutation without a run gets a `legacy` Workflow without invented run,
  actor, or trace provenance.

Contradictory or unprovable combinations (missing mutation, mutation without approval,
pending/rejected approval with mutation, multiple active candidates, or unknown completed outcome)
abort the migration and roll back all changes. Fresh seed data explicitly inserts workflows and
transitions. Demo reset, Eval reset, and cleanup delete transitions before their referenced
artifacts, then workflows.

## API and UI contract

The API exposes:

- `GET /tickets/{ticket_id}/workflows`;
- `GET /workflows/{workflow_id}`;
- `GET /workflows/{workflow_id}/transitions`;
- `POST /workflows/{workflow_id}/cancel` (Support/Admin, reason required).

`AgentDecisionSummary.state` is `not_started` or one of the eight Workflow statuses and includes
workflow ID/version/reason. The Workbench shows the current cycle and append-only timeline, offers a
retry action for `needs_retry`, and links `awaiting_approval` to Approval Queue. Approval Queue has
a `withdrawn` filter and retains one existing page.

## P0-04 boundary

P0-03 remains synchronous. It does not add a queue, worker, lease, checkpoint, stale detection,
automatic timeout, crash recovery, or a generic workflow platform. A process crash after a start
commit may leave a Workflow `investigating`; Support/Admin can cancel it. P0-04 owns asynchronous
execution and recovery on top of these state and command contracts.

## Acceptance evidence

The implementation includes transition-matrix tests, command tests for replay/retry/finalization,
approval/rejection/cancellation, frontend workflow mapping/timeline coverage, and migration SQL
generation from `20260802_0008` to `20260806_0009`. Evidence closure adds
`tests/p0_03_evidence_helpers.py`, `tests/test_p0_03_postgres_atomicity.py`,
`tests/test_p0_03_postgres_concurrency.py`, and `tests/test_p0_03_migration_evidence.py`. The
control transactions observed five DML statements for `finalize_run` and five for
`approve_and_execute`; each command was replayed with an exception before every ordinal and once
from `after_flush_postexec` (10 ordinal points plus 2 post-flush points, 12 injected rollback
points total). The migration matrix used twelve unique temporary Postgres databases: one successful
backfill fixture and eleven independent fail-closed contradiction fixtures. The focused target
passed 29 tests and the canonical `make test-db` passed 36 tests; the full local gate also passed
lint, the 138-pass/36-skip API suite, the 61-pass Web suite, the optimized Web build, Markdown
link checking (18 files/71 local links), container smoke, and `git diff --check`.

The implementation-head CI evidence is [run 31188218525](https://github.com/ZophiaWong/meter-desk/actions/runs/31188218525):
[backend-quality](https://github.com/ZophiaWong/meter-desk/actions/runs/31188218525/job/92898091631),
[frontend-quality](https://github.com/ZophiaWong/meter-desk/actions/runs/31188218525/job/92898091323),
[database-integration](https://github.com/ZophiaWong/meter-desk/actions/runs/31188218525/job/92898091292),
and [container-smoke](https://github.com/ZophiaWong/meter-desk/actions/runs/31188218525/job/92899098973),
all successful. `make test-p0-03-evidence` remains a focused rerun convenience; `make test-db`
remains the canonical database gate. The complete verification set remains:

```text
make lint
make test
make test-db
make build-web
python scripts/check_markdown_links.py
make container-smoke
```

Real-Postgres lock-wait and failure-injection evidence promoted the six P0-03 rows to Verified in
the engineering evidence matrix. The acknowledged-result boundary after a successful commit
remains explicitly deferred to P0-04.

## References

- [System Architecture](../system-architecture.md)
- [Agent Governance](../agent-governance.md)
- [Eval Strategy](../eval-strategy.md)
- [Post-M10 Hardening Roadmap](roadmap.md)
- [P1-04 Persistence Foundation](p1-04-persistence-foundation.md)
