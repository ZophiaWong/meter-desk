"""P0-02 authentication and approval RBAC

Revision ID: 20260802_0008
Revises: 20260701_0007
Create Date: 2026-08-02 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260802_0008"
down_revision: str | None = "20260701_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "approval_requests",
        "decided_by",
        existing_type=sa.String(length=120),
        new_column_name="decision_actor_display_name",
        existing_nullable=True,
    )
    op.add_column(
        "approval_requests",
        sa.Column("decision_actor_subject", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "approval_requests",
        sa.Column("decision_actor_role", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "approval_requests",
        sa.Column("decision_actor_source", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "approval_requests",
        sa.Column("decision_request_id", sa.String(length=80), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE approval_requests
            SET decision_actor_display_name = NULL
            WHERE status = 'pending'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE approval_requests
            SET decision_actor_source = 'legacy_unverified',
                decision_actor_subject = NULL,
                decision_actor_role = NULL,
                decision_request_id = NULL
            WHERE status IN ('approved', 'rejected')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE approval_requests
            SET decision_actor_subject = 'demo-approver',
                decision_actor_display_name = 'Demo Approver',
                decision_actor_role = 'approver',
                decision_actor_source = 'seed_fixture',
                decision_request_id = 'req_seed_eval_cr_003_hist'
            WHERE id = 'APR-EVAL-CR-003-HIST'
              AND status = 'approved'
            """
        )
    )

    op.create_check_constraint(
        "ck_approval_actor_source",
        "approval_requests",
        "decision_actor_source IS NULL OR decision_actor_source IN "
        "('demo_session', 'seed_fixture', 'legacy_unverified')",
    )
    op.create_check_constraint(
        "ck_approval_actor_role",
        "approval_requests",
        "decision_actor_role IS NULL OR decision_actor_role IN "
        "('support_operator', 'approver', 'admin')",
    )
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
        "AND decision_actor_subject IS NOT NULL "
        "AND decision_actor_display_name IS NOT NULL "
        "AND decision_actor_role IN ('approver', 'admin') "
        "AND decision_request_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_approval_decision_audit_shape",
        "approval_requests",
        type_="check",
    )
    op.drop_constraint("ck_approval_actor_role", "approval_requests", type_="check")
    op.drop_constraint("ck_approval_actor_source", "approval_requests", type_="check")
    op.drop_column("approval_requests", "decision_request_id")
    op.drop_column("approval_requests", "decision_actor_source")
    op.drop_column("approval_requests", "decision_actor_role")
    op.drop_column("approval_requests", "decision_actor_subject")
    op.alter_column(
        "approval_requests",
        "decision_actor_display_name",
        existing_type=sa.String(length=120),
        new_column_name="decided_by",
        existing_nullable=True,
    )
