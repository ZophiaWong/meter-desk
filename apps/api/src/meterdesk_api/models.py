from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSONB, list[str]: JSONB}


class SeededRow:
    seed_marker: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)


class CustomerAccount(SeededRow, Base):
    __tablename__ = "customer_accounts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    plan: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_email: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(160), nullable=False)

    tickets: Mapped[list[Ticket]] = relationship(back_populates="customer_account")


class Ticket(SeededRow, Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_account_id: Mapped[str] = mapped_column(
        ForeignKey("customer_accounts.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    scenario: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(80), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    opened_at_display: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    customer_account: Mapped[CustomerAccount] = relationship(back_populates="tickets")


class Invoice(SeededRow, Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("customer_accounts.id"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    period_display: Mapped[str] = mapped_column(String(80), nullable=False)
    total_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    total_display: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class Charge(SeededRow, Base):
    __tablename__ = "charges"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_display: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    captured_at_display: Mapped[str] = mapped_column(String(80), nullable=False)
    processor_state: Mapped[str] = mapped_column(String(160), nullable=False)


class UsageRecord(SeededRow, Base):
    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("customer_accounts.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)


class CreditLedgerEntry(SeededRow, Base):
    __tablename__ = "credit_ledger_entries"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("customer_accounts.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount_display: Mapped[str | None] = mapped_column(String(32), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    granted_amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    granted_amount_display: Mapped[str | None] = mapped_column(String(32), nullable=True)
    granted_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    consumed_amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consumed_amount_display: Mapped[str | None] = mapped_column(String(32), nullable=True)
    consumed_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    remaining_amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remaining_amount_display: Mapped[str | None] = mapped_column(String(32), nullable=True)
    remaining_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    disputed_amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disputed_amount_display: Mapped[str | None] = mapped_column(String(32), nullable=True)
    disputed_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)


class SubscriptionEvidenceRecord(SeededRow, Base):
    __tablename__ = "subscription_evidence"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("customer_accounts.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(160), nullable=False)
    trial_started_at_display: Mapped[str] = mapped_column(String(80), nullable=False)
    trial_ended_at_display: Mapped[str] = mapped_column(String(80), nullable=False)
    canceled_at_display: Mapped[str | None] = mapped_column(String(80), nullable=True)
    renewal_captured_at_display: Mapped[str | None] = mapped_column(String(80), nullable=True)
    canceled_before_renewal_capture: Mapped[bool] = mapped_column(Boolean, nullable=False)


class PolicyRule(SeededRow, Base):
    __tablename__ = "policy_rules"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    citation: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)


class TicketPolicyLink(SeededRow, Base):
    __tablename__ = "ticket_policy_links"

    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), primary_key=True)
    policy_rule_id: Mapped[str] = mapped_column(ForeignKey("policy_rules.id"), primary_key=True)


class CaseWorkflow(SeededRow, Base):
    __tablename__ = "case_workflows"
    __table_args__ = (
        UniqueConstraint("ticket_id", "cycle_number", name="uq_case_workflows_ticket_cycle"),
        CheckConstraint(
            "status IN ('investigating', 'needs_retry', 'awaiting_approval', "
            "'completed_no_action', 'rejected', 'mock_executed', 'failed', 'cancelled')",
            name="ck_case_workflows_status",
        ),
        CheckConstraint(
            "origin IN ('runtime', 'legacy', 'seed_fixture')",
            name="ck_case_workflows_origin",
        ),
        CheckConstraint("cycle_number >= 1", name="ck_case_workflows_cycle_number"),
        CheckConstraint(
            "version >= 1 AND transition_sequence >= 1",
            name="ck_case_workflows_version",
        ),
        Index(
            "uq_case_workflows_active_ticket",
            "ticket_id",
            unique=True,
            postgresql_where=("status IN ('investigating', 'needs_retry', 'awaiting_approval')"),
        ),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status_reason_code: Mapped[str] = mapped_column(String(120), nullable=False)
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin: Mapped[str] = mapped_column(String(40), nullable=False, default="runtime")
    previous_workflow_id: Mapped[str | None] = mapped_column(
        ForeignKey("case_workflows.id"), nullable=True, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    transition_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    terminal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CaseWorkflowTransition(SeededRow, Base):
    __tablename__ = "case_workflow_transitions"
    __table_args__ = (
        UniqueConstraint("workflow_id", "sequence", name="uq_workflow_transitions_sequence"),
        CheckConstraint(
            "to_status IN ('investigating', 'needs_retry', 'awaiting_approval', "
            "'completed_no_action', 'rejected', 'mock_executed', 'failed', 'cancelled')",
            name="ck_workflow_transitions_to_status",
        ),
        CheckConstraint(
            "from_status IS NULL OR from_status IN ('investigating', 'needs_retry', "
            "'awaiting_approval', 'completed_no_action', 'rejected', 'mock_executed', "
            "'failed', 'cancelled')",
            name="ck_workflow_transitions_from_status",
        ),
        CheckConstraint("sequence >= 1", name="ck_workflow_transitions_sequence"),
    )

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("case_workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(120), nullable=False)
    reason_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_subject: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actor_display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    actor_source: Mapped[str] = mapped_column(String(40), nullable=False)
    request_id: Mapped[str] = mapped_column(String(120), nullable=False)
    agent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    approval_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("approval_requests.id"), nullable=True
    )
    mock_mutation_id: Mapped[str | None] = mapped_column(
        ForeignKey("mock_mutations.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentRun(SeededRow, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'cancelled')",
            name="ck_agent_runs_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("case_workflows.id"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    final_outcome: Mapped[str | None] = mapped_column(String(120), nullable=True)
    internal_resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ToolTrace(SeededRow, Base):
    __tablename__ = "tool_traces"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    risk: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    input_summary: Mapped[str] = mapped_column(Text, nullable=False)
    output_summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    policy_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    approval_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    error_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    governance_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ApprovalRequest(SeededRow, Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        CheckConstraint(
            "decision_actor_source IS NULL OR decision_actor_source IN "
            "('demo_session', 'seed_fixture', 'legacy_unverified')",
            name="ck_approval_actor_source",
        ),
        CheckConstraint(
            "decision_actor_role IS NULL OR decision_actor_role IN "
            "('support_operator', 'approver', 'admin')",
            name="ck_approval_actor_role",
        ),
        CheckConstraint(
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
            name="ck_approval_decision_audit_shape",
        ),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("case_workflows.id"), nullable=False, index=True
    )
    agent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_display: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    blocker: Mapped[str] = mapped_column(String(160), nullable=False)
    policy_citation: Mapped[str] = mapped_column(String(120), nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    action_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    action_fingerprint: Mapped[str] = mapped_column(String(260), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(40), nullable=True)
    decision_actor_subject: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decision_actor_display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decision_actor_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    decision_actor_source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    decision_request_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class MockMutation(SeededRow, Base):
    __tablename__ = "mock_mutations"
    __table_args__ = (CheckConstraint("status = 'mock_executed'", name="ck_mock_mutations_status"),)

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("case_workflows.id"), nullable=False, index=True
    )
    approval_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("approval_requests.id"), nullable=True
    )
    agent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    mutation_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_display: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    action_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    action_fingerprint: Mapped[str] = mapped_column(String(260), nullable=False, index=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    executed_at_display: Mapped[str] = mapped_column(String(80), nullable=False)


Index(
    "uq_agent_runs_workflow_running",
    AgentRun.workflow_id,
    unique=True,
    postgresql_where="status = 'running'",
)
Index("uq_agent_runs_ticket_idempotency", AgentRun.ticket_id, AgentRun.idempotency_key, unique=True)
Index("uq_approval_requests_workflow", ApprovalRequest.workflow_id, unique=True)
Index("uq_mock_mutations_workflow", MockMutation.workflow_id, unique=True)
Index(
    "uq_mock_mutations_executed_fingerprint",
    MockMutation.action_fingerprint,
    unique=True,
    postgresql_where="status = 'mock_executed'",
)


class EvalCase(SeededRow, Base):
    __tablename__ = "eval_cases"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    scenario: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_outcome: Mapped[str] = mapped_column(String(160), nullable=False)
    required_evidence: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    policy_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    expected_approval_routing: Mapped[str] = mapped_column(String(160), nullable=False)
    fixture_ticket_id: Mapped[str | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    grading_criteria: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class EvalResult(SeededRow, Base):
    __tablename__ = "eval_results"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("eval_cases.id"), nullable=False, index=True)
    agent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    dimension_scores: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvalSuiteRun(SeededRow, Base):
    __tablename__ = "eval_suite_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    baseline_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("eval_cases.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvalResultSnapshot(SeededRow, Base):
    __tablename__ = "eval_result_snapshots"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    eval_run_id: Mapped[str] = mapped_column(
        ForeignKey("eval_suite_runs.id"), nullable=False, index=True
    )
    result_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("eval_cases.id"), nullable=False, index=True)
    agent_run_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    snapshot_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    dimension_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    trace_signature: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    version_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    explanations: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
