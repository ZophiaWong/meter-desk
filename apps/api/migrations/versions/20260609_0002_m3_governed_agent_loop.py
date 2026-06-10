"""m3 governed agent loop schema

Revision ID: 20260609_0002
Revises: 20260608_0001
Create Date: 2026-06-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260609_0002"
down_revision: str | None = "20260608_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "agent_runs",
        "final_outcome",
        existing_type=sa.String(length=120),
        nullable=True,
    )
    op.alter_column("agent_runs", "internal_resolution", existing_type=sa.Text(), nullable=True)
    op.alter_column("agent_runs", "customer_reply", existing_type=sa.Text(), nullable=True)
    op.add_column("agent_runs", sa.Column("error_state", sa.Text(), nullable=True))

    op.add_column(
        "approval_requests",
        sa.Column(
            "action_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "approval_requests",
        sa.Column("decided_by", sa.String(length=120), nullable=True),
    )
    op.add_column("approval_requests", sa.Column("decision_note", sa.Text(), nullable=True))
    op.alter_column("approval_requests", "action_metadata", server_default=None)

    op.add_column(
        "mock_mutations",
        sa.Column(
            "action_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column("mock_mutations", "action_metadata", server_default=None)

    op.create_index(
        "uq_mock_mutations_approval_request_id",
        "mock_mutations",
        ["approval_request_id"],
        unique=True,
        postgresql_where=sa.text("approval_request_id IS NOT NULL"),
    )
    op.create_index(
        "uq_pending_financial_approval_per_ticket_action",
        "approval_requests",
        ["ticket_id", "action_type"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("uq_pending_financial_approval_per_ticket_action", table_name="approval_requests")
    op.drop_index("uq_mock_mutations_approval_request_id", table_name="mock_mutations")
    op.drop_column("mock_mutations", "action_metadata")
    op.drop_column("approval_requests", "decision_note")
    op.drop_column("approval_requests", "decided_by")
    op.drop_column("approval_requests", "action_metadata")
    op.drop_column("agent_runs", "error_state")
    op.alter_column("agent_runs", "customer_reply", existing_type=sa.Text(), nullable=False)
    op.alter_column("agent_runs", "internal_resolution", existing_type=sa.Text(), nullable=False)
    op.alter_column(
        "agent_runs",
        "final_outcome",
        existing_type=sa.String(length=120),
        nullable=False,
    )
