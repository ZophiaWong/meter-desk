# ruff: noqa: E501

"""P0-03 workflow state consistency.

The backfill is intentionally fail-closed.  A legacy row is assigned to one
workflow cycle only when the existing approval/mutation/run combination can be
proven; contradictory combinations abort the migration transaction.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_0009"
down_revision: str | None = "20260802_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


WORKFLOW_STATUSES = (
    "investigating",
    "needs_retry",
    "awaiting_approval",
    "completed_no_action",
    "rejected",
    "mock_executed",
    "failed",
    "cancelled",
)


def upgrade() -> None:
    # Add nullable links first so the existing data can be examined and
    # backfilled before any NOT NULL or foreign-key constraint is enforced.
    op.add_column("agent_runs", sa.Column("workflow_id", sa.String(80), nullable=True))
    op.add_column("agent_runs", sa.Column("idempotency_key", sa.String(160), nullable=True))
    op.add_column("agent_runs", sa.Column("error_code", sa.String(120), nullable=True))
    op.add_column("approval_requests", sa.Column("workflow_id", sa.String(80), nullable=True))
    op.add_column("mock_mutations", sa.Column("workflow_id", sa.String(80), nullable=True))

    op.create_table(
        "case_workflows",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("ticket_id", sa.String(32), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("status_reason_code", sa.String(120), nullable=False),
        sa.Column("status_reason", sa.Text(), nullable=True),
        sa.Column("origin", sa.String(40), nullable=False),
        sa.Column("previous_workflow_id", sa.String(80), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("transition_sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("terminal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("seed_marker", sa.String(32), nullable=True),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.ForeignKeyConstraint(["previous_workflow_id"], ["case_workflows.id"]),
        sa.UniqueConstraint("ticket_id", "cycle_number", name="uq_case_workflows_ticket_cycle"),
        sa.CheckConstraint(
            "status IN ('investigating', 'needs_retry', 'awaiting_approval', "
            "'completed_no_action', 'rejected', 'mock_executed', 'failed', 'cancelled')",
            name="ck_case_workflows_status",
        ),
        sa.CheckConstraint(
            "origin IN ('runtime', 'legacy', 'seed_fixture')",
            name="ck_case_workflows_origin",
        ),
        sa.CheckConstraint("cycle_number >= 1", name="ck_case_workflows_cycle_number"),
        sa.CheckConstraint(
            "version >= 1 AND transition_sequence >= 1", name="ck_case_workflows_version"
        ),
    )
    op.create_index("ix_case_workflows_ticket_id", "case_workflows", ["ticket_id"])
    op.create_index("ix_case_workflows_status", "case_workflows", ["status"])
    op.create_index(
        "ix_case_workflows_previous_workflow_id",
        "case_workflows",
        ["previous_workflow_id"],
    )

    op.create_table(
        "case_workflow_transitions",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("workflow_id", sa.String(80), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(40), nullable=True),
        sa.Column("to_status", sa.String(40), nullable=False),
        sa.Column("reason_code", sa.String(120), nullable=False),
        sa.Column("reason_detail", sa.Text(), nullable=True),
        sa.Column("actor_subject", sa.String(120), nullable=True),
        sa.Column("actor_display_name", sa.String(120), nullable=True),
        sa.Column("actor_role", sa.String(40), nullable=True),
        sa.Column("actor_source", sa.String(40), nullable=False),
        sa.Column("request_id", sa.String(120), nullable=False),
        sa.Column("agent_run_id", sa.String(80), nullable=True),
        sa.Column("approval_request_id", sa.String(80), nullable=True),
        sa.Column("mock_mutation_id", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("seed_marker", sa.String(32), nullable=True),
        sa.ForeignKeyConstraint(["workflow_id"], ["case_workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["approval_request_id"], ["approval_requests.id"]),
        sa.ForeignKeyConstraint(["mock_mutation_id"], ["mock_mutations.id"]),
        sa.UniqueConstraint("workflow_id", "sequence", name="uq_workflow_transitions_sequence"),
        sa.CheckConstraint(
            "to_status IN ('investigating', 'needs_retry', 'awaiting_approval', "
            "'completed_no_action', 'rejected', 'mock_executed', 'failed', 'cancelled')",
            name="ck_workflow_transitions_to_status",
        ),
        sa.CheckConstraint(
            "from_status IS NULL OR from_status IN ('investigating', 'needs_retry', "
            "'awaiting_approval', 'completed_no_action', 'rejected', 'mock_executed', "
            "'failed', 'cancelled')",
            name="ck_workflow_transitions_from_status",
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_workflow_transitions_sequence"),
    )
    op.create_index(
        "ix_case_workflow_transitions_workflow_id",
        "case_workflow_transitions",
        ["workflow_id"],
    )

    # The 0008 check predates withdrawn.  Drop it while the strict backfill is
    # running and recreate the expanded audit shape below.
    op.drop_constraint(
        "ck_approval_decision_audit_shape",
        "approval_requests",
        type_="check",
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            DO $$
            DECLARE
                row_record RECORD;
                workflow_id_value TEXT;
                final_status TEXT;
                final_reason_code TEXT;
                final_reason TEXT;
                latest_run_id TEXT;
                latest_approval_id TEXT;
                latest_mutation_id TEXT;
                run_count INTEGER;
                approval_count INTEGER;
                mutation_count INTEGER;
                seeded_count INTEGER;
                completed_outcome TEXT;
            BEGIN
                -- Fail closed before assigning any links.  We cannot infer a
                -- cycle when multiple live candidates or contradictory audit
                -- records exist.
                IF EXISTS (
                    SELECT 1
                    FROM approval_requests approval
                    LEFT JOIN mock_mutations mutation
                      ON mutation.approval_request_id = approval.id
                    WHERE approval.status = 'approved'
                      AND mutation.id IS NULL
                ) THEN
                    RAISE EXCEPTION 'P0-03 migration: approved approval is missing its mutation';
                END IF;
                IF EXISTS (
                    SELECT 1
                    FROM approval_requests approval
                    JOIN mock_mutations mutation
                      ON mutation.approval_request_id = approval.id
                    WHERE approval.status <> 'approved'
                ) THEN
                    RAISE EXCEPTION 'P0-03 migration: non-approved approval already has a mutation';
                END IF;
                IF EXISTS (
                    SELECT 1
                    FROM approval_requests approval
                    JOIN mock_mutations mutation
                      ON mutation.approval_request_id = approval.id
                    WHERE approval.status = 'approved'
                      AND (
                          mutation.status <> 'mock_executed'
                          OR
                          mutation.ticket_id <> approval.ticket_id
                          OR mutation.action_fingerprint <> approval.action_fingerprint
                      )
                ) THEN
                    RAISE EXCEPTION 'P0-03 migration: approval and mutation audit fields disagree';
                END IF;
                IF EXISTS (
                    SELECT 1
                    FROM mock_mutations mutation
                    LEFT JOIN approval_requests approval
                      ON approval.id = mutation.approval_request_id
                    WHERE approval.id IS NULL
                ) THEN
                    RAISE EXCEPTION 'P0-03 migration: mutation has no approval';
                END IF;
                IF EXISTS (
                    SELECT 1
                    FROM agent_runs
                    WHERE status = 'running'
                      AND ticket_id IN (
                          SELECT ticket_id
                          FROM agent_runs
                          WHERE status = 'running'
                          GROUP BY ticket_id
                          HAVING count(*) > 1
                      )
                ) THEN
                    RAISE EXCEPTION 'P0-03 migration: multiple active runs for one ticket';
                END IF;
                IF EXISTS (
                    SELECT ticket_id
                    FROM approval_requests
                    GROUP BY ticket_id
                    HAVING count(*) > 1
                ) THEN
                    RAISE EXCEPTION 'P0-03 migration: multiple approval candidates for one ticket';
                END IF;
                IF EXISTS (
                    SELECT ticket_id
                    FROM mock_mutations
                    GROUP BY ticket_id
                    HAVING count(*) > 1
                ) THEN
                    RAISE EXCEPTION 'P0-03 migration: multiple mutation candidates for one ticket';
                END IF;
                IF EXISTS (
                    SELECT 1
                    FROM agent_runs run
                    WHERE run.status = 'completed'
                      AND run.final_outcome NOT IN (
                          'no_refund_expected_billing_behavior',
                          'insufficient_evidence_human_review',
                          'duplicate_action_already_executed',
                          'prior_adjustment_already_applied',
                          'confirmed_duplicate_charge',
                          'refund_requires_approval',
                          'goodwill_credit_requires_approval'
                      )
                ) THEN
                    RAISE EXCEPTION 'P0-03 migration: completed run has unknown outcome without approval';
                END IF;

                FOR row_record IN
                    SELECT ticket_id,
                           min(started_at) AS first_started_at,
                           max(coalesce(completed_at, started_at)) AS last_seen_at
                    FROM (
                        SELECT ticket_id, started_at, completed_at FROM agent_runs
                        UNION ALL
                        SELECT ticket_id, created_at, decided_at FROM approval_requests
                        UNION ALL
                        SELECT ticket_id, executed_at, executed_at FROM mock_mutations
                    ) artifacts
                    GROUP BY ticket_id
                LOOP
                    workflow_id_value := 'WF-P003-' || row_record.ticket_id || '-1';
                    SELECT count(*) INTO run_count FROM agent_runs WHERE ticket_id = row_record.ticket_id;
                    SELECT count(*) INTO approval_count FROM approval_requests WHERE ticket_id = row_record.ticket_id;
                    SELECT count(*) INTO mutation_count FROM mock_mutations WHERE ticket_id = row_record.ticket_id;
                    SELECT count(*) INTO seeded_count
                    FROM (
                        SELECT seed_marker FROM agent_runs WHERE ticket_id = row_record.ticket_id
                        UNION ALL
                        SELECT seed_marker FROM approval_requests WHERE ticket_id = row_record.ticket_id
                        UNION ALL
                        SELECT seed_marker FROM mock_mutations WHERE ticket_id = row_record.ticket_id
                    ) seeded
                    WHERE seed_marker IS NOT NULL;
                    SELECT id INTO latest_run_id
                    FROM agent_runs
                    WHERE ticket_id = row_record.ticket_id
                    ORDER BY started_at DESC
                    LIMIT 1;
                    SELECT id INTO latest_approval_id
                    FROM approval_requests
                    WHERE ticket_id = row_record.ticket_id
                    ORDER BY created_at DESC
                    LIMIT 1;
                    SELECT id INTO latest_mutation_id
                    FROM mock_mutations
                    WHERE ticket_id = row_record.ticket_id
                    ORDER BY executed_at DESC
                    LIMIT 1;
                    INSERT INTO case_workflows (
                        id, ticket_id, cycle_number, status, status_reason_code,
                        status_reason, origin, previous_workflow_id, version,
                        transition_sequence, created_at, updated_at, started_at,
                        terminal_at, seed_marker
                    )
                    SELECT workflow_id_value,
                           row_record.ticket_id,
                           1,
                           'investigating',
                           'migration.initializing',
                           'Workflow backfilled from pre-P0-03 records.',
                           CASE WHEN seeded_count > 0 THEN 'seed_fixture' ELSE 'legacy' END,
                           NULL,
                           1,
                           1,
                           coalesce(row_record.first_started_at, now()),
                           coalesce(row_record.last_seen_at, now()),
                           coalesce(row_record.first_started_at, now()),
                           NULL,
                           CASE WHEN run_count > 0 THEN 'p0-03-backfill' ELSE 'legacy-backfill' END
                    WHERE NOT EXISTS (
                        SELECT 1 FROM case_workflows WHERE id = workflow_id_value
                    );

                    UPDATE agent_runs
                    SET workflow_id = workflow_id_value,
                        idempotency_key = coalesce(idempotency_key, 'legacy:' || id)
                    WHERE ticket_id = row_record.ticket_id;
                    UPDATE approval_requests
                    SET workflow_id = workflow_id_value
                    WHERE ticket_id = row_record.ticket_id;
                    UPDATE mock_mutations
                    SET workflow_id = workflow_id_value
                    WHERE ticket_id = row_record.ticket_id;

                    IF mutation_count = 1 THEN
                        final_status := 'mock_executed';
                        final_reason_code := 'migration.mock_executed';
                        final_reason := 'Historical approval and mock mutation were both present.';
                    ELSIF approval_count = 1 AND EXISTS (
                        SELECT 1 FROM approval_requests
                        WHERE ticket_id = row_record.ticket_id AND status = 'pending'
                    ) THEN
                        final_status := 'awaiting_approval';
                        final_reason_code := 'migration.pending_approval';
                        final_reason := 'Historical approval was pending at migration time.';
                    ELSIF approval_count = 1 AND EXISTS (
                        SELECT 1 FROM approval_requests
                        WHERE ticket_id = row_record.ticket_id AND status = 'rejected'
                    ) THEN
                        final_status := 'rejected';
                        final_reason_code := 'migration.rejected_approval';
                        final_reason := 'Historical approval was rejected.';
                    ELSIF approval_count = 1 AND EXISTS (
                        SELECT 1 FROM approval_requests
                        WHERE ticket_id = row_record.ticket_id AND status = 'withdrawn'
                    ) THEN
                        final_status := 'cancelled';
                        final_reason_code := 'migration.withdrawn_approval';
                        final_reason := 'Historical approval was withdrawn before execution.';
                    ELSE
                        SELECT run.final_outcome INTO completed_outcome
                        FROM agent_runs run
                        WHERE run.ticket_id = row_record.ticket_id
                        ORDER BY run.started_at DESC
                        LIMIT 1;
                        IF EXISTS (
                            SELECT 1 FROM agent_runs
                            WHERE ticket_id = row_record.ticket_id AND status IN ('running', 'failed')
                        ) THEN
                            UPDATE agent_runs
                            SET status = 'failed',
                                error_code = 'migration.interrupted_run',
                                error_state = 'Migration interrupted an unfinished run.',
                                completed_at = coalesce(completed_at, now())
                            WHERE ticket_id = row_record.ticket_id AND status = 'running';
                            final_status := 'needs_retry';
                            final_reason_code := 'migration.interrupted_run';
                            final_reason := 'The historical run was unfinished when P0-03 was introduced.';
                        ELSIF completed_outcome IN (
                            'no_refund_expected_billing_behavior',
                            'insufficient_evidence_human_review',
                            'duplicate_action_already_executed',
                            'prior_adjustment_already_applied'
                        ) THEN
                            final_status := 'completed_no_action';
                            final_reason_code := 'migration.completed_no_action';
                            final_reason := 'Historical run recorded a valid no-action conclusion.';
                        ELSIF completed_outcome IN (
                            'confirmed_duplicate_charge',
                            'refund_requires_approval',
                            'goodwill_credit_requires_approval'
                        ) THEN
                            final_status := 'failed';
                            final_reason_code := 'migration.approval_missing';
                            final_reason := 'Historical run required approval but no approval was present.';
                        ELSE
                            final_status := 'failed';
                            final_reason_code := 'migration.unproven_history';
                            final_reason := 'Historical result could not be proven safe to continue.';
                        END IF;
                    END IF;

                    UPDATE case_workflows
                    SET status = final_status,
                        status_reason_code = final_reason_code,
                        status_reason = final_reason,
                        version = CASE WHEN final_status = 'investigating' THEN 1 ELSE 2 END,
                        transition_sequence = CASE WHEN final_status = 'investigating' THEN 1 ELSE 2 END,
                        updated_at = coalesce(row_record.last_seen_at, now()),
                        terminal_at = CASE
                            WHEN final_status IN ('completed_no_action', 'rejected', 'mock_executed', 'failed', 'cancelled')
                            THEN coalesce(row_record.last_seen_at, now())
                            ELSE NULL
                        END
                    WHERE id = workflow_id_value;

                    INSERT INTO case_workflow_transitions (
                        id, workflow_id, sequence, from_status, to_status, reason_code,
                        reason_detail, actor_source, request_id, created_at, seed_marker
                    ) VALUES (
                        workflow_id_value || '-T1', workflow_id_value, 1, NULL,
                        'investigating', 'migration.initializing',
                        'Workflow created from pre-P0-03 records.', 'legacy_unverified',
                        'migration.p0_03', coalesce(row_record.first_started_at, now()),
                        'p0-03-backfill'
                    );
                    IF final_status <> 'investigating' THEN
                        INSERT INTO case_workflow_transitions (
                            id, workflow_id, sequence, from_status, to_status, reason_code,
                            reason_detail, actor_source, request_id, agent_run_id,
                            approval_request_id, mock_mutation_id, created_at, seed_marker
                        ) VALUES (
                            workflow_id_value || '-T2', workflow_id_value, 2, 'investigating',
                            final_status, final_reason_code, final_reason,
                            'legacy_unverified', 'migration.p0_03', latest_run_id,
                            CASE WHEN approval_count = 1 THEN latest_approval_id ELSE NULL END,
                            CASE WHEN mutation_count = 1 THEN latest_mutation_id ELSE NULL END,
                            coalesce(row_record.last_seen_at, now()), 'p0-03-backfill'
                        );
                    END IF;
                END LOOP;
            END $$;
            """
        )
    )

    # Recreate audit shape after backfill.  Legacy rows remain explicitly
    # unverified; runtime decisions must carry a trusted actor and request id.
    op.create_check_constraint(
        "ck_approval_decision_audit_shape",
        "approval_requests",
        "(status = 'pending' AND decided_at IS NULL AND decision IS NULL "
        "AND decision_actor_subject IS NULL AND decision_actor_display_name IS NULL "
        "AND decision_actor_role IS NULL AND decision_actor_source IS NULL "
        "AND decision_request_id IS NULL) OR "
        "(status IN ('approved', 'rejected', 'withdrawn') AND decided_at IS NOT NULL "
        "AND decision = status AND decision_actor_source = 'legacy_unverified' "
        "AND decision_actor_subject IS NULL AND decision_actor_display_name IS NULL "
        "AND decision_actor_role IS NULL "
        "AND decision_request_id IS NULL) OR "
        "(status IN ('approved', 'rejected') AND decided_at IS NOT NULL "
        "AND decision = status AND decision_actor_source IN ('demo_session', 'seed_fixture') "
        "AND decision_actor_subject IS NOT NULL "
        "AND decision_actor_display_name IS NOT NULL "
        "AND decision_actor_role IN ('approver', 'admin') "
        "AND decision_request_id IS NOT NULL) OR "
        "(status = 'withdrawn' AND decided_at IS NOT NULL "
        "AND decision = 'withdrawn' AND decision_actor_source IN "
        "('demo_session', 'seed_fixture') "
        "AND decision_actor_subject IS NOT NULL "
        "AND decision_actor_display_name IS NOT NULL "
        "AND decision_actor_role IN ('support_operator', 'admin') "
        "AND decision_request_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_agent_runs_status",
        "agent_runs",
        "status IN ('running', 'completed', 'failed', 'cancelled')",
    )
    op.create_check_constraint(
        "ck_mock_mutations_status",
        "mock_mutations",
        "status = 'mock_executed'",
    )
    op.create_foreign_key(
        "fk_agent_runs_workflow_id",
        "agent_runs",
        "case_workflows",
        ["workflow_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_approval_requests_workflow_id",
        "approval_requests",
        "case_workflows",
        ["workflow_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_mock_mutations_workflow_id",
        "mock_mutations",
        "case_workflows",
        ["workflow_id"],
        ["id"],
    )
    op.alter_column("agent_runs", "workflow_id", nullable=False)
    op.alter_column("agent_runs", "idempotency_key", nullable=False)
    op.alter_column("approval_requests", "workflow_id", nullable=False)
    op.alter_column("mock_mutations", "workflow_id", nullable=False)

    op.create_index(
        "uq_case_workflows_active_ticket",
        "case_workflows",
        ["ticket_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('investigating', 'needs_retry', 'awaiting_approval')"),
    )
    op.create_index(
        "uq_agent_runs_workflow_running",
        "agent_runs",
        ["workflow_id"],
        unique=True,
        postgresql_where=sa.text("status = 'running'"),
    )
    op.create_index(
        "uq_agent_runs_ticket_idempotency",
        "agent_runs",
        ["ticket_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "uq_approval_requests_workflow", "approval_requests", ["workflow_id"], unique=True
    )
    op.create_index("uq_mock_mutations_workflow", "mock_mutations", ["workflow_id"], unique=True)
    op.create_index(
        "uq_mock_mutations_executed_fingerprint",
        "mock_mutations",
        ["action_fingerprint"],
        unique=True,
        postgresql_where=sa.text("status = 'mock_executed'"),
    )


def downgrade() -> None:
    op.drop_index("uq_mock_mutations_executed_fingerprint", table_name="mock_mutations")
    op.drop_index("uq_mock_mutations_workflow", table_name="mock_mutations")
    op.drop_index("uq_approval_requests_workflow", table_name="approval_requests")
    op.drop_index("uq_agent_runs_ticket_idempotency", table_name="agent_runs")
    op.drop_index("uq_agent_runs_workflow_running", table_name="agent_runs")
    op.drop_index("uq_case_workflows_active_ticket", table_name="case_workflows")
    op.alter_column("mock_mutations", "workflow_id", nullable=True)
    op.alter_column("approval_requests", "workflow_id", nullable=True)
    op.alter_column("agent_runs", "idempotency_key", nullable=True)
    op.alter_column("agent_runs", "workflow_id", nullable=True)
    op.drop_constraint("fk_mock_mutations_workflow_id", "mock_mutations", type_="foreignkey")
    op.drop_constraint("fk_approval_requests_workflow_id", "approval_requests", type_="foreignkey")
    op.drop_constraint("fk_agent_runs_workflow_id", "agent_runs", type_="foreignkey")
    op.drop_constraint("ck_mock_mutations_status", "mock_mutations", type_="check")
    op.drop_constraint("ck_agent_runs_status", "agent_runs", type_="check")
    op.drop_constraint("ck_approval_decision_audit_shape", "approval_requests", type_="check")
    op.create_check_constraint(
        "ck_approval_decision_audit_shape",
        "approval_requests",
        "(status = 'pending' AND decided_at IS NULL AND decision IS NULL "
        "AND decision_actor_subject IS NULL AND decision_actor_display_name IS NULL "
        "AND decision_actor_role IS NULL AND decision_actor_source IS NULL "
        "AND decision_request_id IS NULL) OR "
        "(status IN ('approved', 'rejected') AND decided_at IS NOT NULL "
        "AND decision = status AND decision_actor_source = 'legacy_unverified' "
        "AND decision_actor_subject IS NULL AND decision_actor_role IS NULL "
        "AND decision_request_id IS NULL) OR "
        "(status IN ('approved', 'rejected') AND decided_at IS NOT NULL "
        "AND decision = status AND decision_actor_source IN ('demo_session', 'seed_fixture') "
        "AND decision_actor_subject IS NOT NULL AND decision_actor_display_name IS NOT NULL "
        "AND decision_actor_role IN ('approver', 'admin') AND decision_request_id IS NOT NULL)",
    )
    op.drop_index(
        "ix_case_workflow_transitions_workflow_id", table_name="case_workflow_transitions"
    )
    op.drop_table("case_workflow_transitions")
    op.drop_index("ix_case_workflows_previous_workflow_id", table_name="case_workflows")
    op.drop_index("ix_case_workflows_status", table_name="case_workflows")
    op.drop_index("ix_case_workflows_ticket_id", table_name="case_workflows")
    op.drop_table("case_workflows")
    op.drop_column("mock_mutations", "workflow_id")
    op.drop_column("approval_requests", "workflow_id")
    op.drop_column("agent_runs", "error_code")
    op.drop_column("agent_runs", "idempotency_key")
    op.drop_column("agent_runs", "workflow_id")
