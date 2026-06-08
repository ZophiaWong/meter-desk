from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

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
    final_outcome: str
    internal_resolution: str
    customer_reply: str
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
    title: str
    status: str
    amount: MoneyAmount
    reason: str
    policy_citation: str
    blocker: str


class MockMutationSummary(BaseModel):
    id: str
    ticket_id: str
    approval_request_id: str | None
    agent_run_id: str | None
    mutation_type: str
    status: str
    amount: MoneyAmount
    reason: str
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


class EvalResultSummary(BaseModel):
    id: str
    case_id: str
    agent_run_id: str | None
    status: str
    summary: str
    dimension_scores: dict[str, str]


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
