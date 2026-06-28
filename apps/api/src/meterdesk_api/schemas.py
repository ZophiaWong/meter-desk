from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Scenario = Literal["duplicate_charge", "usage_spike", "credit_refund_dispute"]
RiskLevel = Literal["Low", "Medium", "High"]
RunComplianceStatus = Literal["passed", "failed", "unsupported"]
DecisionSummaryState = Literal[
    "not_run",
    "running",
    "completed",
    "failed",
    "pending_approval",
    "approved",
    "rejected",
    "mock_executed",
]
DecisionSummaryTileKind = Literal["decision", "evidence", "risk_gate", "draft"]
DecisionSummaryTone = Literal["neutral", "info", "success", "warning", "danger"]


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
    granted_amount: MoneyAmount | None = None
    consumed_amount: MoneyAmount | None = None
    remaining_amount: MoneyAmount | None = None
    disputed_amount: MoneyAmount | None = None


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


class SubscriptionEvidence(BaseModel):
    id: str
    label: str
    status: str
    trial_started_at_display: str
    trial_ended_at_display: str
    canceled_at_display: str | None = None
    renewal_captured_at_display: str | None = None
    canceled_before_renewal_capture: bool = False


class BillingEvidence(BaseModel):
    account: CustomerSummary
    invoice: InvoiceEvidence
    charges: list[ChargeEvidence]
    credits: list[CreditEvidence]
    usage: list[UsageEvidence]
    policy: PolicyEvidence
    policies: list[PolicyEvidence] = Field(default_factory=list)
    subscription: SubscriptionEvidence | None = None


class AgentDecisionSummaryTile(BaseModel):
    kind: DecisionSummaryTileKind
    label: str
    title: str
    body: str
    tone: DecisionSummaryTone
    refs: list[str] = Field(default_factory=list)


class AgentDecisionSummary(BaseModel):
    ticket_id: str
    state: DecisionSummaryState
    decision_label: str
    rationale: str
    run_id: str | None = None
    approval_id: str | None = None
    mutation_id: str | None = None
    policy_citation: str | None = None
    compliance_status: RunComplianceStatus | None = None
    tiles: list[AgentDecisionSummaryTile]


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
    governance_metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceMetadata(BaseModel):
    schema_version: str
    policy_id: str
    policy_version: str
    risk: RiskLevel
    gate: str
    gate_result: str
    enforcement_outcome: str
    required_ref_categories: list[str] = Field(default_factory=list)
    satisfied_ref_categories: list[str] = Field(default_factory=list)
    missing_ref_categories: list[str] = Field(default_factory=list)
    negative_evidence_refs: list[str] = Field(default_factory=list)
    trace_required: bool
    reason_code: str


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
    action_fingerprint: str
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
    action_fingerprint: str
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


class RunComplianceFailure(BaseModel):
    code: str
    message: str
    affected_trace_ids: list[str] = Field(default_factory=list)
    missing_ref_categories: list[str] = Field(default_factory=list)
    approval_ids: list[str] = Field(default_factory=list)
    mutation_ids: list[str] = Field(default_factory=list)
    action_fingerprints: list[str] = Field(default_factory=list)


class RunComplianceResult(BaseModel):
    status: RunComplianceStatus
    checked_at: datetime
    failed_checks: list[RunComplianceFailure] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    affected_trace_ids: list[str] = Field(default_factory=list)
    missing_ref_categories: list[str] = Field(default_factory=list)
    policy_versions_seen: dict[str, str] = Field(default_factory=dict)
    high_risk_gate_count: int
    verified_governed_action_count: int


class ApprovalDecisionRequest(BaseModel):
    decided_by: str = "Demo Operator"
    decision_note: str | None = None


class ApprovalDecisionResponse(BaseModel):
    approval: ApprovalSummary
    mock_mutation: MockMutationSummary | None = None


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
