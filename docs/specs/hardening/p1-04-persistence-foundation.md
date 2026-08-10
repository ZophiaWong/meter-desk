# P1-04 Persistence Foundation

## Status

- Priority: P1.
- Design status: approved for implementation.
- Implementation status: implemented on the candidate branch.
- Verification status: complete locally; all acceptance commands pass, including the real-Postgres
  suite and isolated container smoke.
- Depends on: P0-01 CI and Runtime Baseline and P0-02 Authentication and Approval RBAC.
- Blocks: P0-03 Workflow State Consistency and later background execution work.
- Product scope change: none.

## Problem

Before P1-04, MeterDesk created and disposed a SQLAlchemy `AsyncEngine` for every request. Its database
readiness function is declared async but performs a blocking socket probe and synchronous psycopg
query. Approval constraints prevent duplicate mock mutations, but two independent database sessions
can still race while deciding the same pending approval because neither decision path locks and
refreshes the approval row before writing a terminal state.

P1-04 establishes one application-lifetime async persistence runtime, a real async readiness query,
and deterministic real-Postgres concurrency evidence. It does not redesign all repositories or
define the workflow state machine that belongs to P0-03.

## Goals

1. Own one async engine and session factory for each FastAPI application lifespan.
2. Create one session per request without creating or disposing an engine per request.
3. Preserve liveness while reporting database readiness through the shared async engine.
4. Make the first successfully committed approval decision immutable under concurrent requests.
5. Keep same-direction approval retries idempotent and opposite decisions conflicting.
6. Prove approve/approve and both approve/reject winner orientations against real Postgres.
7. Consolidate real database checks behind one pytest-based `make test-db` entrypoint.

## Persistence Runtime

### Runtime contract

An internal `DatabaseRuntime` owns:

- one SQLAlchemy `AsyncEngine`;
- one `async_sessionmaker[AsyncSession]` configured with `expire_on_commit=False`.

FastAPI lifespan constructs the runtime without opening a database connection, stores it on
`app.state`, and disposes the engine exactly once during shutdown. Application startup therefore
succeeds while Postgres is temporarily unavailable. Database recovery does not require an API
restart.

The request session dependency must resolve the runtime from the active request's application
state. It yields a new session and closes it after the request. Missing lifespan state is an
application wiring error; the dependency must not fall back to a per-request engine.

Seed and live-reset commands use an explicit short-lived async runtime context manager and always
dispose it. Alembic retains its existing `NullPool` migration engine and does not borrow the
application pool.

### Pool configuration

The following settings are per API process:

| Environment variable | Default | Validation | SQLAlchemy use |
|---|---:|---:|---|
| `DATABASE_POOL_SIZE` | `5` | integer, at least 1 | `pool_size` |
| `DATABASE_MAX_OVERFLOW` | `5` | integer, at least 0 | `max_overflow` |
| `DATABASE_POOL_TIMEOUT_SECONDS` | `5` | positive number | `pool_timeout` |
| `DATABASE_CONNECT_TIMEOUT_SECONDS` | `3` | positive integer | psycopg `connect_timeout` |

`pool_pre_ping=True` is fixed rather than configurable. P1-04 does not expose pool recycle, LIFO,
isolation-level, or retry controls. PostgreSQL retains its default `READ COMMITTED` isolation.

## Health Semantics

- `GET /health` remains a pure process liveness response.
- `GET /health/db` resolves the shared `DatabaseRuntime`, checks out an async connection, and
  executes SQLAlchemy `text("SELECT 1")`.
- The existing success and failure status codes and JSON bodies remain unchanged.
- The synchronous socket connection and synchronous `psycopg.connect` probe are removed.
- Database, pool-checkout, and query failures remain sanitized to the exception class name already
  exposed by the readiness response.

The Compose API healthcheck calls `/health/db` with an eight-second HTTP client timeout and a
ten-second Docker healthcheck timeout. Web startup therefore waits for database-backed API
readiness, while a running API with a transient database outage continues to serve `/health`.

## Concurrent Approval Decisions

### Terminal decision rule

The first transaction to acquire the approval row lock and commit a terminal decision owns the
audit record. HTTP arrival order does not define the winner, and neither approve nor reject has
policy priority.

- approve after approve returns the original approval and mock mutation;
- reject after reject returns the original rejection;
- reject after approve and approve after reject return `409 approval.terminal_conflict`;
- no waiting request may replace the first actor, note, decision timestamp, or request ID;
- at most one mock mutation may exist for the approval and financial action fingerprint.

### Locking and refresh

Both SQLAlchemy decision methods load the approval with `SELECT ... FOR UPDATE`. The locked query
must force ORM refresh with `populate_existing` or an equivalent execution option. This is required
because the governance service reads the approval before entering the repository decision method;
an already populated identity-map object must not hide the terminal state committed while the
request waited for the row lock.

Existing unique indexes and audit-shape check constraints remain database backstops. No migration
is required.

### Internal execution result

The repository approve contract returns an internal `ApprovalExecutionResult` containing:

- the terminal approval summary;
- the existing or newly created mock mutation summary;
- `executed_now`, which is true only for the transaction that inserted the mock mutation.

Both in-memory and SQLAlchemy repositories implement this contract. The HTTP
`ApprovalDecisionResponse` is unchanged. Governance writes an executed-mutation trace only when
`executed_now` is true. A concurrent same-direction retry therefore cannot create a duplicate
execution trace. An approve attempt blocked by a winning rejection retains the existing blocked
high-risk trace behavior; P1-04 adds no approval-attempt audit table.

The approval and mock mutation remain atomic within the repository commit. The existing failure
window between that commit and the later governance trace commit is explicitly deferred to P0-03.

## Real Postgres Test Harness

### Canonical entrypoint

Postgres-dependent tests use a registered `postgres` pytest marker and remain skipped unless
`METERDESK_RUN_DB_TESTS=1`. The default test suite stays fast and database-independent.

`make test-db` is the only real database verification entrypoint. It:

1. starts and waits for the repository Postgres service;
2. migrates the database to Alembic head;
3. establishes the seeded baseline through fixtures;
4. runs `METERDESK_RUN_DB_TESTS=1 pytest -m postgres`.

P0-03 adds `make test-p0-03-evidence` as a focused rerun convenience. It starts and seeds the same
local Postgres service, then runs only `pytest -m "postgres and p0_03_evidence"`; it is a subset
entrypoint and does not replace or redefine the canonical `make test-db` gate used by CI.

The authentication, RBAC, approval actor, and idempotency assertions from the standalone
`db_integration_check.py` move into pytest, and the standalone module is removed.

### Isolation and lock choreography

Concurrency tests reuse a seeded ticket but create a unique agent run, approval identifier, and
action fingerprint. Cleanup deletes only those trace, mutation, approval, and run rows in foreign-key
order, including after assertion failures.

Each contender uses an independent session. The deterministic lock helper:

1. acquires the approval row lock in the chosen winner session;
2. records the competitor session's PostgreSQL backend PID;
3. starts the competing service decision;
4. polls `pg_stat_activity` with a bounded deadline until that PID reports a lock wait;
5. commits the chosen winner and awaits the competitor.

The tests do not treat simultaneous coroutine scheduling or repeated stress loops as concurrency
proof.

### Required scenarios

1. **Approve/approve:** both calls return the same terminal approval and mock mutation; exactly one
   result has `executed_now=true`; one mutation and one executed trace are stored.
2. **Approve wins/reject loses:** reject returns the terminal conflict; the approval remains
   approved with the winner's audit, one mutation, and one executed trace.
3. **Reject wins/approve loses:** approve returns the terminal conflict; the approval remains
   rejected with the winner's audit, no mutation, and one blocked high-risk trace.

## Compatibility and Non-Goals

P1-04 changes no external route, response status, response body, database table, or seed schema.
`DATABASE_URL` remains unchanged, and all new settings have defaults. Rollback is a code and
configuration rollback with no data downgrade.

P1-04 does not add:

- a repository-wide Unit of Work abstraction;
- an outbox or distributed transaction;
- automatic transaction retry;
- a database proxy or connection pooler;
- background workers, queues, checkpoints, or cancellation;
- a production capacity or availability claim;
- a new approval-attempt audit model.

## Documentation and Evidence

Implementation updates the foundational architecture and roadmap status, README configuration and
test instructions, container runbook, Compose environment, and
[Engineering Evidence Matrix](../../evidence/engineering-evidence-matrix.md). Evidence rows move to
Verified only after their named commands run successfully with reviewable output.

## Acceptance Criteria

- One engine and session factory exist per FastAPI lifespan and are disposed once at shutdown.
- Every request gets an independent session from that session factory.
- Startup performs no database query and succeeds while Postgres is unavailable.
- `/health/db` uses the shared async engine and preserves its current API contract.
- Compose readiness is database-backed and Web waits for a database-ready API at initial startup.
- Pool settings use the documented defaults and reject invalid values.
- Approval concurrency satisfies all three required real-Postgres scenarios and trace invariants.
- `make test-db` runs the marked pytest suite; the standalone database check module is removed.
- No migration or external API change is introduced.
- The following commands complete with actual results recorded:

```text
make lint
make test
make test-db
make build-web
python scripts/check_markdown_links.py
make container-smoke
```

## References

- [Post-M10 Hardening Roadmap](roadmap.md)
- [P0-02 Authentication and Approval RBAC](p0-02-authentication-approval-rbac.md)
- [System Architecture](../system-architecture.md)
- [Agent Governance](../agent-governance.md)
