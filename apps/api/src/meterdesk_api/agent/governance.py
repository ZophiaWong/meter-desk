from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from meterdesk_api.repositories import MeterDeskRepository
from meterdesk_api.schemas import RiskLevel

GOVERNANCE_POLICY_VERSION = "governance-kernel-v1"


class ToolPolicy(BaseModel):
    id: str
    label: str
    category: str
    risk: RiskLevel
    executor: str
    gate: str
    required_evidence_refs: list[str]
    requires_policy_refs: bool = False
    requires_approval_ref: bool = False
    trace_required: bool = True
    eval_dimensions: list[str]
    version: Literal["governance-kernel-v1"] = GOVERNANCE_POLICY_VERSION


TOOL_POLICIES: tuple[ToolPolicy, ...] = (
    ToolPolicy(
        id="read.billing_evidence",
        label="Collect billing evidence",
        category="read",
        risk="Low",
        executor="backend_read_tool",
        gate="Always allowed; trace required",
        required_evidence_refs=["invoice", "charge", "credit", "usage"],
        requires_policy_refs=True,
        eval_dimensions=["required_evidence", "policy_compliance"],
    ),
    ToolPolicy(
        id="read.prior_financial_actions",
        label="Check prior approvals and mock mutations",
        category="read",
        risk="Low",
        executor="backend_read_tool",
        gate="Always allowed; trace required",
        required_evidence_refs=["ticket"],
        eval_dimensions=["mutation_safety", "approval_routing"],
    ),
    ToolPolicy(
        id="decision.refund_eligibility",
        label="Evaluate duplicate-charge refund eligibility",
        category="decision",
        risk="Medium",
        executor="backend_decision_tool",
        gate="Backend deterministic decision; trace required",
        required_evidence_refs=["invoice", "charge"],
        requires_policy_refs=True,
        eval_dimensions=["outcome_correctness", "policy_compliance", "approval_routing"],
    ),
    ToolPolicy(
        id="draft.resolution",
        label="Draft governed resolution",
        category="draft",
        risk="Low",
        executor="provider_draft_tool",
        gate="Provider output validation; draft-only",
        required_evidence_refs=["invoice", "charge"],
        requires_policy_refs=True,
        eval_dimensions=["draft_safety", "draft_quality"],
    ),
    ToolPolicy(
        id="approval.create_request",
        label="Create financial action approval request",
        category="approval",
        risk="Medium",
        executor="backend_approval_service",
        gate="Creates human approval gate; no mutation",
        required_evidence_refs=["invoice", "charge"],
        requires_policy_refs=True,
        requires_approval_ref=True,
        eval_dimensions=["approval_routing", "mutation_safety"],
    ),
    ToolPolicy(
        id="mutation.mock_refund",
        label="Execute approved mock refund",
        category="mutation",
        risk="High",
        executor="backend_mutation_service",
        gate="Requires approved approval request",
        required_evidence_refs=["invoice", "charge"],
        requires_policy_refs=True,
        requires_approval_ref=True,
        eval_dimensions=["approval_routing", "mutation_safety"],
    ),
)

TOOL_POLICY_BY_ID = {policy.id: policy for policy in TOOL_POLICIES}


def get_tool_policy(policy_id: str) -> ToolPolicy | None:
    return TOOL_POLICY_BY_ID.get(policy_id)


def list_tool_policy_summaries() -> list[ToolPolicy]:
    return list(TOOL_POLICIES)


def build_governance_metadata_for_trace(
    *,
    policy_id: str,
    evidence_refs: list[str],
    policy_refs: list[str],
    approval_refs: list[str],
) -> dict[str, object]:
    policy = get_tool_policy(policy_id)
    if policy is None:
        raise GovernanceViolation(f"Unknown tool policy: {policy_id}")
    return _build_governance_metadata(
        policy=policy,
        evidence_refs=evidence_refs,
        policy_refs=policy_refs,
        approval_refs=approval_refs,
    )


class GovernanceViolation(Exception):
    pass


class GovernanceKernel:
    def __init__(self, repository: MeterDeskRepository) -> None:
        self._repository = repository

    async def record_action(
        self,
        *,
        agent_run_id: str,
        policy_id: str,
        label: str,
        input_summary: str,
        output_summary: str,
        evidence_refs: list[str],
        policy_refs: list[str],
        approval_refs: list[str],
        error_state: str | None = None,
    ):
        policy = get_tool_policy(policy_id)
        if policy is None:
            raise GovernanceViolation(f"Unknown tool policy: {policy_id}")

        metadata = build_governance_metadata_for_trace(
            policy_id=policy.id,
            evidence_refs=evidence_refs,
            policy_refs=policy_refs,
            approval_refs=approval_refs,
        )
        if metadata["missing_ref_categories"]:
            raise GovernanceViolation(
                "Missing required governance refs: " + ", ".join(metadata["missing_ref_categories"])
            )
        if policy.risk == "High":
            await self._enforce_high_risk_approval(approval_refs)

        return await self._repository.add_tool_trace(
            agent_run_id=agent_run_id,
            category=policy.id,
            risk=policy.risk,
            label=label,
            input_summary=input_summary,
            output_summary=output_summary,
            evidence_refs=evidence_refs,
            policy_refs=policy_refs,
            approval_refs=approval_refs,
            error_state=error_state,
            governance_metadata=metadata,
        )

    async def _enforce_high_risk_approval(self, approval_refs: list[str]) -> None:
        if not approval_refs:
            raise GovernanceViolation("High-risk action requires an approval reference")
        for approval_ref in approval_refs:
            approval = await self._repository.get_approval(approval_ref)
            if approval is None:
                raise GovernanceViolation(f"Approval request not found: {approval_ref}")
            if approval.status != "approved":
                raise GovernanceViolation(
                    f"High-risk action requires approved approval: {approval_ref}"
                )


def _build_governance_metadata(
    *,
    policy: ToolPolicy,
    evidence_refs: list[str],
    policy_refs: list[str],
    approval_refs: list[str],
) -> dict[str, object]:
    satisfied = _evidence_ref_categories(evidence_refs)
    required = list(policy.required_evidence_refs)
    if policy.requires_policy_refs:
        required.append("policy")
        if policy_refs:
            satisfied.add("policy")
    if policy.requires_approval_ref:
        required.append("approval")
        if approval_refs:
            satisfied.add("approval")

    missing = [category for category in required if category not in satisfied]
    return {
        "policy_id": policy.id,
        "policy_version": policy.version,
        "risk": policy.risk,
        "gate": policy.gate,
        "gate_result": "allowed" if not missing else "blocked",
        "enforcement_outcome": "trace_recorded" if not missing else "blocked_before_trace",
        "required_ref_categories": required,
        "satisfied_ref_categories": [category for category in required if category in satisfied],
        "missing_ref_categories": missing,
        "trace_required": policy.trace_required,
    }


def _evidence_ref_categories(evidence_refs: list[str]) -> set[str]:
    categories: set[str] = set()
    for evidence_ref in evidence_refs:
        normalized = evidence_ref.lower()
        if normalized.startswith("invoice "):
            categories.add("invoice")
        if normalized.startswith("charge "):
            categories.add("charge")
        if normalized.startswith("credit "):
            categories.add("credit")
        if normalized.startswith("usage "):
            categories.add("usage")
        if normalized.startswith("ticket "):
            categories.add("ticket")
        if normalized.startswith("policy "):
            categories.add("policy")
    return categories
