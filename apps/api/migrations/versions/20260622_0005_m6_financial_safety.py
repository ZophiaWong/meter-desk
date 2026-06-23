"""m6 financial safety

Revision ID: 20260622_0005
Revises: 20260619_0004
Create Date: 2026-06-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260622_0005"
down_revision: str | None = "20260619_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "approval_requests",
        sa.Column("action_fingerprint", sa.String(length=260), nullable=True),
    )
    op.add_column(
        "mock_mutations",
        sa.Column("action_fingerprint", sa.String(length=260), nullable=True),
    )

    op.execute(
        """
        UPDATE approval_requests
        SET action_fingerprint =
            'ticket:' || ticket_id ||
            '|action:' || action_type ||
            '|target:' || COALESCE(
                action_metadata ->> 'target_charge_id',
                action_metadata ->> 'credit_ledger_entry_id',
                action_metadata ->> 'invoice_id',
                id
            ) ||
            '|amount:' || amount_cents::text ||
            '|currency:' || upper(currency)
        WHERE action_fingerprint IS NULL
        """
    )
    op.execute(
        """
        UPDATE mock_mutations
        SET action_fingerprint =
            'ticket:' || ticket_id ||
            '|action:' || mutation_type ||
            '|target:' || COALESCE(
                action_metadata ->> 'target_charge_id',
                action_metadata ->> 'credit_ledger_entry_id',
                action_metadata ->> 'invoice_id',
                id
            ) ||
            '|amount:' || amount_cents::text ||
            '|currency:' || upper(currency)
        WHERE action_fingerprint IS NULL
        """
    )

    op.alter_column("approval_requests", "action_fingerprint", nullable=False)
    op.alter_column("mock_mutations", "action_fingerprint", nullable=False)

    op.create_index(
        "ix_approval_requests_action_fingerprint",
        "approval_requests",
        ["action_fingerprint"],
    )
    op.create_index(
        "ix_mock_mutations_action_fingerprint",
        "mock_mutations",
        ["action_fingerprint"],
    )
    op.create_index(
        "uq_approval_requests_pending_action_fingerprint",
        "approval_requests",
        ["action_fingerprint"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "uq_mock_mutations_executed_action_fingerprint",
        "mock_mutations",
        ["action_fingerprint"],
        unique=True,
        postgresql_where=sa.text("status = 'mock_executed'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_mock_mutations_executed_action_fingerprint",
        table_name="mock_mutations",
    )
    op.drop_index(
        "uq_approval_requests_pending_action_fingerprint",
        table_name="approval_requests",
    )
    op.drop_index("ix_mock_mutations_action_fingerprint", table_name="mock_mutations")
    op.drop_index("ix_approval_requests_action_fingerprint", table_name="approval_requests")
    op.drop_column("mock_mutations", "action_fingerprint")
    op.drop_column("approval_requests", "action_fingerprint")
