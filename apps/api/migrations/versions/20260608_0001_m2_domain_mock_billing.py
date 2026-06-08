"""m2 domain mock billing schema

Revision ID: 20260608_0001
Revises:
Create Date: 2026-06-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260608_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def seed_marker_column() -> sa.Column[str]:
    return sa.Column("seed_marker", sa.String(length=32), nullable=True)


def upgrade() -> None:
    op.create_table(
        "customer_accounts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("plan", sa.String(length=120), nullable=False),
        sa.Column("owner_email", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=160), nullable=False),
        seed_marker_column(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_accounts_seed_marker", "customer_accounts", ["seed_marker"])

    op.create_table(
        "tickets",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("customer_account_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("scenario", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=80), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("opened_at_display", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        seed_marker_column(),
        sa.ForeignKeyConstraint(["customer_account_id"], ["customer_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tickets_customer_account_id", "tickets", ["customer_account_id"])
    op.create_index("ix_tickets_scenario", "tickets", ["scenario"])
    op.create_index("ix_tickets_seed_marker", "tickets", ["seed_marker"])

    op.create_table(
        "policy_rules",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("citation", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        seed_marker_column(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_policy_rules_seed_marker", "policy_rules", ["seed_marker"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("ticket_id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("final_outcome", sa.String(length=120), nullable=False),
        sa.Column("internal_resolution", sa.Text(), nullable=False),
        sa.Column("customer_reply", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=True),
        sa.Column("prompt_version", sa.String(length=80), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        seed_marker_column(),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_seed_marker", "agent_runs", ["seed_marker"])
    op.create_index("ix_agent_runs_ticket_id", "agent_runs", ["ticket_id"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("ticket_id", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("period_display", sa.String(length=80), nullable=False),
        sa.Column("total_amount_cents", sa.Integer(), nullable=False),
        sa.Column("total_display", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        seed_marker_column(),
        sa.ForeignKeyConstraint(["account_id"], ["customer_accounts.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoices_seed_marker", "invoices", ["seed_marker"])
    op.create_index("ix_invoices_ticket_id", "invoices", ["ticket_id"])

    op.create_table(
        "ticket_policy_links",
        sa.Column("ticket_id", sa.String(length=32), nullable=False),
        sa.Column("policy_rule_id", sa.String(length=80), nullable=False),
        seed_marker_column(),
        sa.ForeignKeyConstraint(["policy_rule_id"], ["policy_rules.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("ticket_id", "policy_rule_id"),
    )
    op.create_index("ix_ticket_policy_links_seed_marker", "ticket_policy_links", ["seed_marker"])

    op.create_table(
        "usage_records",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("ticket_id", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        seed_marker_column(),
        sa.ForeignKeyConstraint(["account_id"], ["customer_accounts.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usage_records_seed_marker", "usage_records", ["seed_marker"])
    op.create_index("ix_usage_records_ticket_id", "usage_records", ["ticket_id"])

    op.create_table(
        "credit_ledger_entries",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("ticket_id", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column("amount_display", sa.String(length=32), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        seed_marker_column(),
        sa.ForeignKeyConstraint(["account_id"], ["customer_accounts.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_credit_ledger_entries_seed_marker", "credit_ledger_entries", ["seed_marker"]
    )
    op.create_index("ix_credit_ledger_entries_ticket_id", "credit_ledger_entries", ["ticket_id"])

    op.create_table(
        "charges",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("invoice_id", sa.String(length=64), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("amount_display", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_at_display", sa.String(length=80), nullable=False),
        sa.Column("processor_state", sa.String(length=160), nullable=False),
        seed_marker_column(),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_charges_invoice_id", "charges", ["invoice_id"])
    op.create_index("ix_charges_seed_marker", "charges", ["seed_marker"])

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("ticket_id", sa.String(length=32), nullable=False),
        sa.Column("agent_run_id", sa.String(length=80), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("amount_display", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("blocker", sa.String(length=160), nullable=False),
        sa.Column("policy_citation", sa.String(length=120), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision", sa.String(length=40), nullable=True),
        seed_marker_column(),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_requests_seed_marker", "approval_requests", ["seed_marker"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])
    op.create_index("ix_approval_requests_ticket_id", "approval_requests", ["ticket_id"])

    op.create_table(
        "tool_traces",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("agent_run_id", sa.String(length=80), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("risk", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("output_summary", sa.Text(), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("policy_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("approval_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_state", sa.Text(), nullable=True),
        seed_marker_column(),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tool_traces_agent_run_id", "tool_traces", ["agent_run_id"])
    op.create_index("ix_tool_traces_seed_marker", "tool_traces", ["seed_marker"])

    op.create_table(
        "mock_mutations",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("ticket_id", sa.String(length=32), nullable=False),
        sa.Column("approval_request_id", sa.String(length=80), nullable=True),
        sa.Column("agent_run_id", sa.String(length=80), nullable=True),
        sa.Column("mutation_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("amount_display", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at_display", sa.String(length=80), nullable=False),
        seed_marker_column(),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["approval_request_id"], ["approval_requests.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mock_mutations_seed_marker", "mock_mutations", ["seed_marker"])
    op.create_index("ix_mock_mutations_ticket_id", "mock_mutations", ["ticket_id"])

    op.create_table(
        "eval_cases",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("scenario", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("expected_outcome", sa.String(length=160), nullable=False),
        sa.Column("required_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("policy_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expected_approval_routing", sa.String(length=160), nullable=False),
        sa.Column("grading_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        seed_marker_column(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_cases_scenario", "eval_cases", ["scenario"])
    op.create_index("ix_eval_cases_seed_marker", "eval_cases", ["seed_marker"])

    op.create_table(
        "eval_results",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("case_id", sa.String(length=80), nullable=False),
        sa.Column("agent_run_id", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("dimension_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        seed_marker_column(),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["eval_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_results_case_id", "eval_results", ["case_id"])
    op.create_index("ix_eval_results_seed_marker", "eval_results", ["seed_marker"])


def downgrade() -> None:
    op.drop_index("ix_eval_results_seed_marker", table_name="eval_results")
    op.drop_index("ix_eval_results_case_id", table_name="eval_results")
    op.drop_table("eval_results")
    op.drop_index("ix_eval_cases_seed_marker", table_name="eval_cases")
    op.drop_index("ix_eval_cases_scenario", table_name="eval_cases")
    op.drop_table("eval_cases")
    op.drop_index("ix_mock_mutations_ticket_id", table_name="mock_mutations")
    op.drop_index("ix_mock_mutations_seed_marker", table_name="mock_mutations")
    op.drop_table("mock_mutations")
    op.drop_index("ix_tool_traces_seed_marker", table_name="tool_traces")
    op.drop_index("ix_tool_traces_agent_run_id", table_name="tool_traces")
    op.drop_table("tool_traces")
    op.drop_index("ix_approval_requests_ticket_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_seed_marker", table_name="approval_requests")
    op.drop_table("approval_requests")
    op.drop_index("ix_charges_seed_marker", table_name="charges")
    op.drop_index("ix_charges_invoice_id", table_name="charges")
    op.drop_table("charges")
    op.drop_index("ix_credit_ledger_entries_ticket_id", table_name="credit_ledger_entries")
    op.drop_index("ix_credit_ledger_entries_seed_marker", table_name="credit_ledger_entries")
    op.drop_table("credit_ledger_entries")
    op.drop_index("ix_usage_records_ticket_id", table_name="usage_records")
    op.drop_index("ix_usage_records_seed_marker", table_name="usage_records")
    op.drop_table("usage_records")
    op.drop_index("ix_ticket_policy_links_seed_marker", table_name="ticket_policy_links")
    op.drop_table("ticket_policy_links")
    op.drop_index("ix_invoices_ticket_id", table_name="invoices")
    op.drop_index("ix_invoices_seed_marker", table_name="invoices")
    op.drop_table("invoices")
    op.drop_index("ix_agent_runs_ticket_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_seed_marker", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index("ix_policy_rules_seed_marker", table_name="policy_rules")
    op.drop_table("policy_rules")
    op.drop_index("ix_tickets_seed_marker", table_name="tickets")
    op.drop_index("ix_tickets_scenario", table_name="tickets")
    op.drop_index("ix_tickets_customer_account_id", table_name="tickets")
    op.drop_table("tickets")
    op.drop_index("ix_customer_accounts_seed_marker", table_name="customer_accounts")
    op.drop_table("customer_accounts")
