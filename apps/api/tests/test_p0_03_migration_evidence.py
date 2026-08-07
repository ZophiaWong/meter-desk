from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest
from psycopg.types.json import Jsonb

from p0_03_evidence_helpers import (
    TemporaryPostgresDatabase,
    _database_url_for_psycopg,
    run_alembic,
    temporary_postgres_database,
)

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.p0_03_evidence,
    pytest.mark.skipif(
        os.environ.get("METERDESK_RUN_DB_TESTS") != "1",
        reason="Set METERDESK_RUN_DB_TESTS=1 and run against local Postgres.",
    ),
]

REVISION_0008 = "20260802_0008"
REVISION_0009 = "20260806_0009"
BASE_TIME = datetime(2026, 8, 1, 12, tzinfo=UTC)


@pytest.mark.asyncio
async def test_real_migration_backfills_all_provable_workflow_outcomes() -> None:
    with temporary_postgres_database() as database:
        _upgrade_to_0008(database)
        with psycopg.connect(
            _database_url_for_psycopg(database.url),
            autocommit=True,
        ) as connection:
            _insert_success_fixture(connection)

        upgraded = run_alembic(database.url, REVISION_0009)
        assert upgraded.returncode == 0, upgraded.stderr[-4000:]

        with psycopg.connect(_database_url_for_psycopg(database.url)) as connection:
            revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
            assert revision == (REVISION_0009,)
            rows = connection.execute(
                "SELECT ticket_id, status, status_reason_code, origin, version, "
                "transition_sequence FROM case_workflows ORDER BY ticket_id"
            ).fetchall()
            by_ticket = {row[0]: row[1:] for row in rows}
            assert by_ticket["P003-pending"][:2] == (
                "awaiting_approval",
                "migration.pending_approval",
            )
            assert by_ticket["P003-rejected"][:2] == ("rejected", "migration.rejected_approval")
            assert by_ticket["P003-approved"][:2] == ("mock_executed", "migration.mock_executed")
            assert by_ticket["P003-running"][:2] == (
                "needs_retry",
                "migration.interrupted_run",
            )
            assert by_ticket["P003-failed"][:2] == ("needs_retry", "migration.interrupted_run")
            assert by_ticket["P003-no-action"][:2] == (
                "completed_no_action",
                "migration.completed_no_action",
            )
            assert by_ticket["P003-missing-approval"][:2] == (
                "failed",
                "migration.approval_missing",
            )
            assert by_ticket["P003-legacy"][:2] == ("mock_executed", "migration.mock_executed")
            assert all(row[3:] == (2, 2) for row in by_ticket.values()), by_ticket

            running = connection.execute(
                "SELECT status, error_code, error_state, completed_at FROM agent_runs "
                "WHERE id = 'RUN-P003-running'"
            ).fetchone()
            assert running[0:3] == (
                "failed",
                "migration.interrupted_run",
                "Migration interrupted an unfinished run.",
            )
            assert running[3] is not None
            failed = connection.execute(
                "SELECT status, error_code FROM agent_runs WHERE id = 'RUN-P003-failed'"
            ).fetchone()
            assert failed == ("failed", None)

            legacy = connection.execute(
                "SELECT workflow.origin, transition.agent_run_id, transition.approval_request_id, "
                "transition.mock_mutation_id FROM case_workflows workflow "
                "JOIN case_workflow_transitions transition ON transition.workflow_id = workflow.id "
                "WHERE workflow.id = 'WF-P003-P003-legacy-1' AND transition.sequence = 2"
            ).fetchone()
            assert legacy == ("legacy", None, "APR-P003-legacy", "MM-P003-legacy")
            assert connection.execute(
                "SELECT count(*) FROM tool_traces WHERE agent_run_id IS NULL"
            ).fetchone() == (0,)

            not_null = connection.execute(
                "SELECT table_name, column_name, is_nullable FROM information_schema.columns "
                "WHERE (table_name, column_name) IN "
                "(('agent_runs', 'workflow_id'), ('agent_runs', 'idempotency_key'), "
                "('approval_requests', 'workflow_id'), ('mock_mutations', 'workflow_id')) "
                "ORDER BY table_name, column_name"
            ).fetchall()
            assert not_null == [
                ("agent_runs", "idempotency_key", "NO"),
                ("agent_runs", "workflow_id", "NO"),
                ("approval_requests", "workflow_id", "NO"),
                ("mock_mutations", "workflow_id", "NO"),
            ]
            indexes = {
                row[0]
                for row in connection.execute(
                    "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
                )
            }
            assert {
                "uq_case_workflows_active_ticket",
                "uq_agent_runs_workflow_running",
                "uq_agent_runs_ticket_idempotency",
                "uq_approval_requests_workflow",
                "uq_mock_mutations_workflow",
                "uq_mock_mutations_executed_fingerprint",
            } <= indexes
            constraints = {
                row[0]
                for row in connection.execute(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'approval_requests'::regclass"
                )
            }
            assert "ck_approval_decision_audit_shape" in constraints


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("name", "builder", "message"),
    [
        (
            "approved_missing_mutation",
            lambda connection: _insert_approval(
                connection,
                ticket_id="P003-fail",
                approval_id="APR-P003-fail",
                status="approved",
                fingerprint="fp-approved-missing",
            ),
            "approved approval is missing its mutation",
        ),
        (
            "pending_with_mutation",
            lambda connection: _insert_pending_with_mutation(connection, status="pending"),
            "non-approved approval already has a mutation",
        ),
        (
            "rejected_with_mutation",
            lambda connection: _insert_pending_with_mutation(connection, status="rejected"),
            "non-approved approval already has a mutation",
        ),
        (
            "mutation_without_approval",
            lambda connection: _insert_orphan_mutation(connection),
            "mutation has no approval",
        ),
        (
            "fingerprint_mismatch",
            lambda connection: _insert_mismatched_mutation(connection, mismatch="fingerprint"),
            "approval and mutation audit fields disagree",
        ),
        (
            "ticket_mismatch",
            lambda connection: _insert_mismatched_mutation(connection, mismatch="ticket"),
            "approval and mutation audit fields disagree",
        ),
        (
            "mutation_status_mismatch",
            lambda connection: _insert_mismatched_mutation(connection, mismatch="status"),
            "approval and mutation audit fields disagree",
        ),
        (
            "multiple_running_runs",
            lambda connection: _insert_multiple_runs(connection),
            "multiple active runs for one ticket",
        ),
        (
            "multiple_approvals",
            lambda connection: _insert_multiple_approvals(connection),
            "multiple approval candidates for one ticket",
        ),
        (
            "multiple_mutations",
            lambda connection: _insert_multiple_mutations(connection),
            "multiple mutation candidates for one ticket",
        ),
        (
            "unknown_completed_outcome",
            lambda connection: _insert_run(
                connection,
                run_id="RUN-P003-unknown",
                ticket_id="P003-fail",
                status="completed",
                final_outcome="unprovable-result",
            ),
            "completed run has unknown outcome without approval",
        ),
    ],
)
async def test_migration_rejects_contradictory_legacy_rows(
    name: str,
    builder: Callable[[Any], None],
    message: str,
) -> None:
    del name
    with temporary_postgres_database() as database:
        _upgrade_to_0008(database)
        with psycopg.connect(
            _database_url_for_psycopg(database.url),
            autocommit=True,
        ) as connection:
            _insert_base_ticket(connection, "P003-fail")
            builder(connection)
            before_runs = connection.execute(
                "SELECT id, status, final_outcome, error_state FROM agent_runs "
                "WHERE ticket_id = 'P003-fail' ORDER BY id"
            ).fetchall()
            before_approvals = connection.execute(
                "SELECT id, status, decision, action_fingerprint FROM approval_requests "
                "WHERE ticket_id = 'P003-fail' ORDER BY id"
            ).fetchall()
            before_mutations = connection.execute(
                "SELECT id, approval_request_id, status, action_fingerprint FROM mock_mutations "
                "WHERE ticket_id = 'P003-fail' ORDER BY id"
            ).fetchall()

        failed = run_alembic(database.url, REVISION_0009)
        assert failed.returncode != 0
        assert message in f"{failed.stdout}\n{failed.stderr}"

        with psycopg.connect(_database_url_for_psycopg(database.url)) as connection:
            assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
                REVISION_0008,
            )
            assert connection.execute(
                "SELECT to_regclass('public.case_workflows'), "
                "to_regclass('public.case_workflow_transitions')"
            ).fetchone() == (None, None)
            assert connection.execute(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE (table_name, column_name) IN "
                "(('agent_runs', 'workflow_id'), ('agent_runs', 'idempotency_key'), "
                "('agent_runs', 'error_code'), ('approval_requests', 'workflow_id'), "
                "('mock_mutations', 'workflow_id'))"
            ).fetchone() == (0,)
            assert (
                connection.execute(
                    "SELECT id, status, final_outcome, error_state FROM agent_runs "
                    "WHERE ticket_id = 'P003-fail' ORDER BY id"
                ).fetchall()
                == before_runs
            )
            assert (
                connection.execute(
                    "SELECT id, status, decision, action_fingerprint FROM approval_requests "
                    "WHERE ticket_id = 'P003-fail' ORDER BY id"
                ).fetchall()
                == before_approvals
            )
            assert (
                connection.execute(
                    "SELECT id, approval_request_id, status, action_fingerprint "
                    "FROM mock_mutations "
                    "WHERE ticket_id = 'P003-fail' ORDER BY id"
                ).fetchall()
                == before_mutations
            )
            assert connection.execute(
                "SELECT count(*) FROM pg_constraint "
                "WHERE conname = 'ck_approval_decision_audit_shape'"
            ).fetchone() == (1,)


def _upgrade_to_0008(database: TemporaryPostgresDatabase) -> None:
    upgraded = run_alembic(database.url, REVISION_0008)
    assert upgraded.returncode == 0, upgraded.stderr[-4000:]


def _connection_execute(connection, statement: str, **params: Any) -> None:
    connection.execute(statement, params)


def _insert_success_fixture(connection) -> None:
    _insert_base_ticket(connection, "P003-pending")
    _insert_approval(
        connection,
        ticket_id="P003-pending",
        approval_id="APR-P003-pending",
        status="pending",
        fingerprint="fp-pending",
    )

    _insert_base_ticket(connection, "P003-rejected")
    _insert_approval(
        connection,
        ticket_id="P003-rejected",
        approval_id="APR-P003-rejected",
        status="rejected",
        fingerprint="fp-rejected",
    )

    _insert_base_ticket(connection, "P003-approved")
    _insert_run(
        connection,
        run_id="RUN-P003-approved",
        ticket_id="P003-approved",
        status="completed",
        final_outcome="confirmed_duplicate_charge",
        seed_marker="legacy-fixture",
    )
    _insert_approval(
        connection,
        ticket_id="P003-approved",
        approval_id="APR-P003-approved",
        status="approved",
        fingerprint="fp-approved",
        agent_run_id="RUN-P003-approved",
        seed_marker="legacy-fixture",
    )
    _insert_mutation(
        connection,
        mutation_id="MM-P003-approved",
        ticket_id="P003-approved",
        approval_id="APR-P003-approved",
        agent_run_id="RUN-P003-approved",
        fingerprint="fp-approved",
        seed_marker="legacy-fixture",
    )

    _insert_base_ticket(connection, "P003-running")
    _insert_run(
        connection,
        run_id="RUN-P003-running",
        ticket_id="P003-running",
        status="running",
    )
    _insert_base_ticket(connection, "P003-failed")
    _insert_run(
        connection,
        run_id="RUN-P003-failed",
        ticket_id="P003-failed",
        status="failed",
    )
    _insert_base_ticket(connection, "P003-no-action")
    _insert_run(
        connection,
        run_id="RUN-P003-no-action",
        ticket_id="P003-no-action",
        status="completed",
        final_outcome="no_refund_expected_billing_behavior",
    )
    _insert_base_ticket(connection, "P003-missing-approval")
    _insert_run(
        connection,
        run_id="RUN-P003-missing-approval",
        ticket_id="P003-missing-approval",
        status="completed",
        final_outcome="refund_requires_approval",
    )

    _insert_base_ticket(connection, "P003-legacy")
    _insert_approval(
        connection,
        ticket_id="P003-legacy",
        approval_id="APR-P003-legacy",
        status="approved",
        fingerprint="fp-legacy",
    )
    _insert_mutation(
        connection,
        mutation_id="MM-P003-legacy",
        ticket_id="P003-legacy",
        approval_id="APR-P003-legacy",
        fingerprint="fp-legacy",
    )


def _insert_base_ticket(connection, ticket_id: str) -> None:
    account_id = f"acct-{ticket_id.lower()}"
    _connection_execute(
        connection,
        "INSERT INTO customer_accounts (id, name, plan, owner_email, status, seed_marker) "
        "VALUES (%(id)s, %(name)s, 'Test', 'test@example.com', 'Active', NULL)",
        id=account_id,
        name=f"Account {ticket_id}",
    )
    _connection_execute(
        connection,
        "INSERT INTO tickets (id, customer_account_id, title, scenario, status, severity, "
        "opened_at, opened_at_display, summary, outcome, sort_order, is_active, seed_marker) "
        "VALUES (%(id)s, %(account_id)s, 'P0-03 fixture', 'duplicate_charge', 'Open', 'Test', "
        "%(opened_at)s, 'Aug 1, 2026', 'Migration fixture', 'Fixture', 1, false, NULL)",
        id=ticket_id,
        account_id=account_id,
        opened_at=BASE_TIME,
    )


def _insert_run(
    connection,
    *,
    run_id: str,
    ticket_id: str,
    status: str,
    final_outcome: str | None = None,
    seed_marker: str | None = None,
) -> None:
    completed_at = BASE_TIME if status in {"completed", "failed"} else None
    _connection_execute(
        connection,
        "INSERT INTO agent_runs (id, ticket_id, status, source, final_outcome, "
        "internal_resolution, customer_reply, model, prompt_version, started_at, completed_at, "
        "seed_marker, error_state) VALUES (%(id)s, %(ticket_id)s, %(status)s, 'legacy-test', "
        "%(final_outcome)s, %(resolution)s, %(reply)s, 'legacy-model', 'legacy-v1', "
        "%(started_at)s, %(completed_at)s, %(seed_marker)s, NULL)",
        id=run_id,
        ticket_id=ticket_id,
        status=status,
        final_outcome=final_outcome,
        resolution="Legacy resolution" if final_outcome is not None else None,
        reply="Draft only" if final_outcome is not None else None,
        started_at=BASE_TIME,
        completed_at=completed_at,
        seed_marker=seed_marker,
    )


def _insert_approval(
    connection,
    *,
    ticket_id: str,
    approval_id: str,
    status: str,
    fingerprint: str,
    agent_run_id: str | None = None,
    seed_marker: str | None = None,
) -> None:
    terminal = status in {"approved", "rejected"}
    _connection_execute(
        connection,
        "INSERT INTO approval_requests (id, ticket_id, agent_run_id, title, status, action_type, "
        "amount_cents, amount_display, currency, reason, blocker, policy_citation, evidence_refs, "
        "created_at, decided_at, decision, seed_marker, action_metadata, "
        "decision_actor_display_name, decision_note, decision_actor_subject, decision_actor_role, "
        "decision_actor_source, decision_request_id, action_fingerprint) VALUES "
        "(%(id)s, %(ticket_id)s, %(agent_run_id)s, 'Legacy approval', %(status)s, %(action_type)s, "
        "100, '$1.00', 'USD', 'Legacy fixture', 'Legacy blocker', 'POLICY-001', %(evidence)s, "
        "%(created_at)s, %(decided_at)s, %(decision)s, %(seed_marker)s, %(metadata)s, NULL, NULL, "
        "NULL, NULL, %(actor_source)s, NULL, %(fingerprint)s)",
        id=approval_id,
        ticket_id=ticket_id,
        agent_run_id=agent_run_id,
        status=status,
        action_type=f"legacy_{approval_id}",
        evidence=Jsonb(["legacy evidence"]),
        created_at=BASE_TIME,
        decided_at=BASE_TIME if terminal else None,
        decision=status if terminal else None,
        seed_marker=seed_marker,
        metadata=Jsonb({}),
        actor_source="legacy_unverified" if terminal else None,
        fingerprint=fingerprint,
    )


def _insert_mutation(
    connection,
    *,
    mutation_id: str,
    ticket_id: str,
    approval_id: str | None,
    fingerprint: str,
    agent_run_id: str | None = None,
    status: str = "mock_executed",
    seed_marker: str | None = None,
) -> None:
    _connection_execute(
        connection,
        "INSERT INTO mock_mutations (id, ticket_id, approval_request_id, agent_run_id, "
        "mutation_type, status, amount_cents, amount_display, currency, reason, executed_at, "
        "executed_at_display, seed_marker, action_metadata, action_fingerprint) VALUES "
        "(%(id)s, %(ticket_id)s, %(approval_id)s, %(agent_run_id)s, 'original_refund', %(status)s, "
        "100, '$1.00', 'USD', 'Legacy mutation', %(executed_at)s, 'Aug 1, 2026', %(seed_marker)s, "
        "%(metadata)s, %(fingerprint)s)",
        id=mutation_id,
        ticket_id=ticket_id,
        approval_id=approval_id,
        agent_run_id=agent_run_id,
        status=status,
        executed_at=BASE_TIME,
        seed_marker=seed_marker,
        metadata=Jsonb({}),
        fingerprint=fingerprint,
    )


def _insert_pending_with_mutation(connection, *, status: str) -> None:
    _insert_approval(
        connection,
        ticket_id="P003-fail",
        approval_id="APR-P003-fail",
        status=status,
        fingerprint="fp-pending-mutation",
    )
    _insert_mutation(
        connection,
        mutation_id="MM-P003-pending-mutation",
        ticket_id="P003-fail",
        approval_id="APR-P003-fail",
        fingerprint="fp-pending-mutation",
    )


def _insert_orphan_mutation(connection) -> None:
    _insert_mutation(
        connection,
        mutation_id="MM-P003-orphan",
        ticket_id="P003-fail",
        approval_id=None,
        fingerprint="fp-orphan",
    )


def _insert_mismatched_mutation(connection, *, mismatch: str) -> None:
    _insert_approval(
        connection,
        ticket_id="P003-fail",
        approval_id="APR-P003-mismatch",
        status="approved",
        fingerprint="fp-approval",
    )
    mutation_ticket = "P003-other" if mismatch == "ticket" else "P003-fail"
    if mismatch == "ticket":
        _insert_base_ticket(connection, mutation_ticket)
    _insert_mutation(
        connection,
        mutation_id="MM-P003-mismatch",
        ticket_id=mutation_ticket,
        approval_id="APR-P003-mismatch",
        fingerprint="fp-mutation" if mismatch == "fingerprint" else "fp-approval",
        status="pending" if mismatch == "status" else "mock_executed",
    )


def _insert_multiple_runs(connection) -> None:
    _insert_run(connection, run_id="RUN-P003-a", ticket_id="P003-fail", status="running")
    _insert_run(connection, run_id="RUN-P003-b", ticket_id="P003-fail", status="running")


def _insert_multiple_approvals(connection) -> None:
    _insert_approval(
        connection,
        ticket_id="P003-fail",
        approval_id="APR-P003-a",
        status="pending",
        fingerprint="fp-a",
    )
    _insert_approval(
        connection,
        ticket_id="P003-fail",
        approval_id="APR-P003-b",
        status="pending",
        fingerprint="fp-b",
    )


def _insert_multiple_mutations(connection) -> None:
    _insert_approval(
        connection,
        ticket_id="P003-fail",
        approval_id="APR-P003-a",
        status="approved",
        fingerprint="fp-a",
    )
    _insert_approval(
        connection,
        ticket_id="P003-fail",
        approval_id="APR-P003-b",
        status="approved",
        fingerprint="fp-b",
    )
    _insert_mutation(
        connection,
        mutation_id="MM-P003-a",
        ticket_id="P003-fail",
        approval_id="APR-P003-a",
        fingerprint="fp-a",
    )
    _insert_mutation(
        connection,
        mutation_id="MM-P003-b",
        ticket_id="P003-fail",
        approval_id="APR-P003-b",
        fingerprint="fp-b",
    )
