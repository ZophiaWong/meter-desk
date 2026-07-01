"""eval regression history

Revision ID: 20260701_0007
Revises: 20260626_0006
Create Date: 2026-07-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260701_0007"
down_revision: str | None = "20260626_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def seed_marker_column() -> sa.Column:
    return sa.Column("seed_marker", sa.String(length=32), nullable=True)


def upgrade() -> None:
    op.create_table(
        "eval_suite_runs",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("run_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("baseline_name", sa.String(length=160), nullable=True),
        sa.Column("case_id", sa.String(length=80), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        seed_marker_column(),
        sa.ForeignKeyConstraint(["case_id"], ["eval_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_suite_runs_run_type", "eval_suite_runs", ["run_type"])
    op.create_index("ix_eval_suite_runs_seed_marker", "eval_suite_runs", ["seed_marker"])

    op.create_table(
        "eval_result_snapshots",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("eval_run_id", sa.String(length=80), nullable=False),
        sa.Column("result_id", sa.String(length=80), nullable=False),
        sa.Column("case_id", sa.String(length=80), nullable=False),
        sa.Column("agent_run_id", sa.String(length=80), nullable=True),
        sa.Column("snapshot_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("dimension_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trace_signature", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explanations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        seed_marker_column(),
        sa.ForeignKeyConstraint(["case_id"], ["eval_cases.id"]),
        sa.ForeignKeyConstraint(["eval_run_id"], ["eval_suite_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_result_snapshots_case_id", "eval_result_snapshots", ["case_id"])
    op.create_index(
        "ix_eval_result_snapshots_eval_run_id",
        "eval_result_snapshots",
        ["eval_run_id"],
    )
    op.create_index("ix_eval_result_snapshots_result_id", "eval_result_snapshots", ["result_id"])
    op.create_index(
        "ix_eval_result_snapshots_snapshot_type",
        "eval_result_snapshots",
        ["snapshot_type"],
    )
    op.create_index(
        "ix_eval_result_snapshots_seed_marker",
        "eval_result_snapshots",
        ["seed_marker"],
    )


def downgrade() -> None:
    op.drop_index("ix_eval_result_snapshots_seed_marker", table_name="eval_result_snapshots")
    op.drop_index("ix_eval_result_snapshots_snapshot_type", table_name="eval_result_snapshots")
    op.drop_index("ix_eval_result_snapshots_result_id", table_name="eval_result_snapshots")
    op.drop_index("ix_eval_result_snapshots_eval_run_id", table_name="eval_result_snapshots")
    op.drop_index("ix_eval_result_snapshots_case_id", table_name="eval_result_snapshots")
    op.drop_table("eval_result_snapshots")
    op.drop_index("ix_eval_suite_runs_seed_marker", table_name="eval_suite_runs")
    op.drop_index("ix_eval_suite_runs_run_type", table_name="eval_suite_runs")
    op.drop_table("eval_suite_runs")
