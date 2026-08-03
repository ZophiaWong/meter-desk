from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text
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


class AgentRun(SeededRow, Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    final_outcome: Mapped[str | None] = mapped_column(String(120), nullable=True)
    internal_resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_state: Mapped[str | None] = mapped_column(Text, nullable=True)
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
            name="ck_approval_decision_audit_shape",
        ),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
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

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
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
