"""credit refund workflow evidence

Revision ID: 20260626_0006
Revises: 20260622_0005
Create Date: 2026-06-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260626_0006"
down_revision: str | None = "20260622_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def seed_marker_column() -> sa.Column[str]:
    return sa.Column("seed_marker", sa.String(length=32), nullable=True)


def upgrade() -> None:
    op.add_column("credit_ledger_entries", sa.Column("granted_amount_cents", sa.Integer()))
    op.add_column("credit_ledger_entries", sa.Column("granted_amount_display", sa.String(32)))
    op.add_column("credit_ledger_entries", sa.Column("granted_currency", sa.String(3)))
    op.add_column("credit_ledger_entries", sa.Column("consumed_amount_cents", sa.Integer()))
    op.add_column("credit_ledger_entries", sa.Column("consumed_amount_display", sa.String(32)))
    op.add_column("credit_ledger_entries", sa.Column("consumed_currency", sa.String(3)))
    op.add_column("credit_ledger_entries", sa.Column("remaining_amount_cents", sa.Integer()))
    op.add_column("credit_ledger_entries", sa.Column("remaining_amount_display", sa.String(32)))
    op.add_column("credit_ledger_entries", sa.Column("remaining_currency", sa.String(3)))
    op.add_column("credit_ledger_entries", sa.Column("disputed_amount_cents", sa.Integer()))
    op.add_column("credit_ledger_entries", sa.Column("disputed_amount_display", sa.String(32)))
    op.add_column("credit_ledger_entries", sa.Column("disputed_currency", sa.String(3)))

    op.create_table(
        "subscription_evidence",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("ticket_id", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=160), nullable=False),
        sa.Column("trial_started_at_display", sa.String(length=80), nullable=False),
        sa.Column("trial_ended_at_display", sa.String(length=80), nullable=False),
        sa.Column("canceled_at_display", sa.String(length=80), nullable=True),
        sa.Column("renewal_captured_at_display", sa.String(length=80), nullable=True),
        sa.Column("canceled_before_renewal_capture", sa.Boolean(), nullable=False),
        seed_marker_column(),
        sa.ForeignKeyConstraint(["account_id"], ["customer_accounts.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_subscription_evidence_seed_marker", "subscription_evidence", ["seed_marker"]
    )
    op.create_index("ix_subscription_evidence_ticket_id", "subscription_evidence", ["ticket_id"])


def downgrade() -> None:
    op.drop_index("ix_subscription_evidence_ticket_id", table_name="subscription_evidence")
    op.drop_index("ix_subscription_evidence_seed_marker", table_name="subscription_evidence")
    op.drop_table("subscription_evidence")

    op.drop_column("credit_ledger_entries", "disputed_currency")
    op.drop_column("credit_ledger_entries", "disputed_amount_display")
    op.drop_column("credit_ledger_entries", "disputed_amount_cents")
    op.drop_column("credit_ledger_entries", "remaining_currency")
    op.drop_column("credit_ledger_entries", "remaining_amount_display")
    op.drop_column("credit_ledger_entries", "remaining_amount_cents")
    op.drop_column("credit_ledger_entries", "consumed_currency")
    op.drop_column("credit_ledger_entries", "consumed_amount_display")
    op.drop_column("credit_ledger_entries", "consumed_amount_cents")
    op.drop_column("credit_ledger_entries", "granted_currency")
    op.drop_column("credit_ledger_entries", "granted_amount_display")
    op.drop_column("credit_ledger_entries", "granted_amount_cents")
