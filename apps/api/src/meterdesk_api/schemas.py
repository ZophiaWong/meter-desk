from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Scenario = Literal["duplicate_charge", "usage_spike", "credit_refund_dispute"]
RiskLevel = Literal["Low", "Medium", "High"]


class MoneyAmount(BaseModel):
    amount_cents: int
    currency: str
    display: str


class CustomerSummary(BaseModel):
    id: str
    name: str
    plan: str
    owner: str
    status: str


class TicketSummary(BaseModel):
    id: str
    title: str
    customer: str
    status: str
    summary: str
    scenario: Scenario
    is_active: bool = False


class TicketDetail(BaseModel):
    id: str
    title: str
    scenario: Scenario
    status: str
    severity: str
    opened_at: datetime
    opened_at_display: str
    summary: str
    outcome: str
    customer: CustomerSummary


class InvoiceEvidence(BaseModel):
    id: str
    period_start: date
    period_end: date
    period_display: str
    total: MoneyAmount
    status: str


class ChargeEvidence(BaseModel):
    id: str
    status: str
    amount: MoneyAmount
    captured_at: datetime
    captured_at_display: str
    processor_state: str


class CreditEvidence(BaseModel):
    id: str
    label: str
    detail: str
    amount: MoneyAmount | None = None


class UsageEvidence(BaseModel):
    id: str
    label: str
    detail: str
    period_start: date | None = None
    period_end: date | None = None


class PolicyEvidence(BaseModel):
    id: str
    version: str
    citation: str
    title: str
    reason: str


class BillingEvidence(BaseModel):
    account: CustomerSummary
    invoice: InvoiceEvidence
    charges: list[ChargeEvidence]
    credits: list[CreditEvidence]
    usage: list[UsageEvidence]
    policy: PolicyEvidence


class AgentRunSummary(BaseModel):
    id: str
    ticket_id: str
    status: str
    source: str
    final_outcome: str | None = None
    internal_resolution: str | None = None
    customer_reply: str | None = None
    error_state: str | None = None
    model: str | None = None
    prompt_version: str | None = None


class ToolTraceSummary(BaseModel):
    id: str
    agent_run_id: str
    sequence: int
    category: str
    risk: RiskLevel
    label: str
    input_summary: str
    output_summary: str
    evidence_refs: list[str]
    policy_refs: list[str]
    approval_refs: list[str]
    error_state: str | None = None


class ApprovalSummary(BaseModel):
    id: str
    ticket_id: str
    agent_run_id: str | None = None
    title: str
    status: str
    action_type: str
    amount: MoneyAmount
    reason: str
    policy_citation: str
    blocker: str
    evidence_refs: list[str] = Field(default_factory=list)
    action_metadata: dict[str, Any] = Field(default_factory=dict)
    decided_at: datetime | None = None
    decision: str | None = None
    decided_by: str | None = None
    decision_note: str | None = None


class MockMutationSummary(BaseModel):
    id: str
    ticket_id: str
    approval_request_id: str | None
    agent_run_id: str | None
    mutation_type: str
    status: str
    amount: MoneyAmount
    reason: str
    action_metadata: dict[str, Any] = Field(default_factory=dict)
    executed_at: datetime
    executed_at_display: str


class EvalCaseSummary(BaseModel):
    id: str
    scenario: Scenario
    title: str
    description: str
    expected_outcome: str
    required_evidence: list[str]
    policy_refs: list[str]
    expected_approval_routing: str
    fixture_ticket_id: str | None = None


class EvalResultSummary(BaseModel):
    id: str
    case_id: str
    agent_run_id: str | None
    status: str
    summary: str
    dimension_scores: dict[str, str]
    details: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecisionRequest(BaseModel):
    decided_by: str = "Demo Operator"
    decision_note: str | None = None


class ApprovalDecisionResponse(BaseModel):
    approval: ApprovalSummary
    mock_mutation: MockMutationSummary | None = None


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
