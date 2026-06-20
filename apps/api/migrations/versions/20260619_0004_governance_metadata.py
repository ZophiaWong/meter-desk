"""governance metadata

Revision ID: 20260619_0004
Revises: 20260611_0003
Create Date: 2026-06-19 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260619_0004"
down_revision: str | None = "20260611_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tool_traces",
        sa.Column(
            "governance_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column("tool_traces", "governance_metadata", server_default=None)


def downgrade() -> None:
    op.drop_column("tool_traces", "governance_metadata")
