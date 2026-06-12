"""m4 eval lab

Revision ID: 20260611_0003
Revises: 20260609_0002
Create Date: 2026-06-11 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260611_0003"
down_revision: str | None = "20260609_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "eval_cases",
        sa.Column("fixture_ticket_id", sa.String(length=32), nullable=True),
    )
    op.create_foreign_key(
        "fk_eval_cases_fixture_ticket_id_tickets",
        "eval_cases",
        "tickets",
        ["fixture_ticket_id"],
        ["id"],
    )
    op.add_column(
        "eval_results",
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column("eval_results", "details", server_default=None)


def downgrade() -> None:
    op.drop_column("eval_results", "details")
    op.drop_constraint(
        "fk_eval_cases_fixture_ticket_id_tickets",
        "eval_cases",
        type_="foreignkey",
    )
    op.drop_column("eval_cases", "fixture_ticket_id")
