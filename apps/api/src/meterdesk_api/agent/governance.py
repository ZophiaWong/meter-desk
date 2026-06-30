from __future__ import annotations

from pydantic import BaseModel

from meterdesk_api.errors import MeterDeskAPIError
from meterdesk_api.financial_actions import build_action_fingerprint
from meterdesk_api.repositories import MeterDeskRepository
from meterdesk_api.schemas import (
    ApprovalDecisionResponse,
    ApprovalSummary,
    GovernanceMetadata,
    RiskLevel,
)

GOVERNANCE_POLICY_VERSION = "1.0.0"
GOVERNANCE_METADATA_SCHEMA_VERSION = "1.0.0"


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
    version: str = GOVERNANCE_POLICY_VERSION


TOOL_POLICIES: tuple[ToolPolicy, ...] = (
    ToolPolicy(
        id="plan.investigation",
        label="Plan governed investigation",
        category="plan",
        risk="Low",
        executor="provider_planner",
        gate="Provider structured plan; backend verifier required before execution",
        required_evidence_refs=["ticket"],
        eval_dimensions=["tool_planning"],
    ),
    ToolPolicy(
        id="plan.verify",
        label="Verify investigation plan contract",
        category="plan",
        risk="Low",
        executor="backend_plan_verifier",
        gate="Backend contract verifier accepts or blocks planned actions",
        required_evidence_refs=["ticket"],
        eval_dimensions=["tool_planning"],
    ),
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
        id="read.credit_refund_evidence",
        label="Collect credit/refund dispute evidence",
        category="read",
        risk="Low",
        executor="backend_read_tool",
        gate="Always allowed; trace required",
        required_evidence_refs=["invoice", "charge", "credit", "subscription"],
        requires_policy_refs=True,
        eval_dimensions=["required_evidence", "policy_compliance"],
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
        id="decision.credit_refund_eligibility",
        label="Evaluate credit/refund dispute eligibility",
        category="decision",
        risk="Medium",
        executor="backend_decision_tool",
        gate="Backend deterministic decision; trace required",
        required_evidence_refs=["invoice", "credit", "subscription"],
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
        required_evidence_refs=["invoice"],
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
        required_evidence_refs=["invoice"],
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
    ToolPolicy(
        id="mutation.mock_credit_or_refund",
        label="Execute approved mock credit or refund",
        category="mutation",
        risk="High",
        executor="backend_mutation_service",
        gate="Requires approved approval request",
        required_evidence_refs=["invoice"],
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
    negative_evidence_refs: list[str] | None = None,
) -> dict[str, object]:
    policy = get_tool_policy(policy_id)
    if policy is None:
        raise GovernanceViolation(
            status_code=409,
            code="governance.unknown_policy",
            message=f"Unknown tool policy: {policy_id}",
            details={"policy_id": policy_id},
        )
    return _build_governance_metadata(
        policy=policy,
        evidence_refs=evidence_refs,
        policy_refs=policy_refs,
        approval_refs=approval_refs,
        negative_evidence_refs=negative_evidence_refs or [],
    )


class GovernanceViolation(MeterDeskAPIError):
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
        negative_evidence_refs: list[str] | None = None,
        error_state: str | None = None,
        governance_metadata_extra: dict[str, object] | None = None,
    ):
        policy = get_tool_policy(policy_id)
        if policy is None:
            error = GovernanceViolation(
                status_code=409,
                code="governance.unknown_policy",
                message=f"Unknown tool policy: {policy_id}",
                details={"policy_id": policy_id},
            )
            await self._record_blocked_trace(
                agent_run_id=agent_run_id,
                policy=None,
                policy_id=policy_id,
                label=label,
                input_summary=input_summary,
                output_summary=output_summary,
                evidence_refs=evidence_refs,
                policy_refs=policy_refs,
                approval_refs=approval_refs,
                negative_evidence_refs=negative_evidence_refs or [],
                error=error,
            )
            raise error

        metadata = build_governance_metadata_for_trace(
            policy_id=policy.id,
            evidence_refs=evidence_refs,
            policy_refs=policy_refs,
            approval_refs=approval_refs,
            negative_evidence_refs=negative_evidence_refs or [],
        )
        if governance_metadata_extra:
            metadata = {**metadata, **governance_metadata_extra}
        if metadata["missing_ref_categories"]:
            error = GovernanceViolation(
                status_code=409,
                code="governance.missing_required_ref",
                message=(
                    "Missing required governance refs: "
                    + ", ".join(metadata["missing_ref_categories"])
                ),
                details={"missing_ref_categories": metadata["missing_ref_categories"]},
            )
            await self._record_trace(
                agent_run_id=agent_run_id,
                policy=policy,
                label=label,
                input_summary=input_summary,
                output_summary=output_summary,
                evidence_refs=evidence_refs,
                policy_refs=policy_refs,
                approval_refs=approval_refs,
                governance_metadata=_blocked_metadata(metadata, error.code),
                error_state=error.code,
            )
            raise error
        if policy.risk == "High":
            try:
                await self._enforce_high_risk_approval(approval_refs)
            except GovernanceViolation as error:
                await self._record_trace(
                    agent_run_id=agent_run_id,
                    policy=policy,
                    label=label,
                    input_summary=input_summary,
                    output_summary=output_summary,
                    evidence_refs=evidence_refs,
                    policy_refs=policy_refs,
                    approval_refs=approval_refs,
                    governance_metadata=_blocked_metadata(metadata, error.code),
                    error_state=error.code,
                )
                raise

        return await self._record_trace(
            agent_run_id=agent_run_id,
            policy=policy,
            label=label,
            input_summary=input_summary,
            output_summary=output_summary,
            evidence_refs=evidence_refs,
            policy_refs=policy_refs,
            approval_refs=approval_refs,
            governance_metadata=metadata,
            error_state=error_state,
        )

    async def create_approval_request(
        self,
        *,
        ticket_id: str,
        agent_run_id: str,
        title: str,
        action_type: str,
        amount_cents: int,
        amount_display: str,
        currency: str,
        reason: str,
        blocker: str,
        policy_citation: str,
        evidence_refs: list[str],
        policy_refs: list[str],
        action_metadata: dict[str, object],
        label: str,
        input_summary: str,
        output_summary: str,
    ) -> ApprovalSummary:
        action_fingerprint = build_action_fingerprint(
            ticket_id=ticket_id,
            action_type=action_type,
            amount_cents=amount_cents,
            currency=currency,
            action_metadata=action_metadata,
        )
        pending = await self._repository.get_pending_approval_by_fingerprint(action_fingerprint)
        if pending is not None:
            error = GovernanceViolation(
                status_code=409,
                code="approval.pending_duplicate",
                message="A pending financial approval already exists for this action.",
                details={"action_fingerprint": action_fingerprint},
            )
            await self._record_financial_block(
                agent_run_id=agent_run_id,
                policy_id="approval.create_request",
                label=label,
                input_summary=input_summary,
                output_summary=output_summary,
                evidence_refs=evidence_refs,
                policy_refs=policy_refs,
                approval_refs=[pending.id],
                error=error,
            )
            raise error
        executed = await self._repository.get_executed_mock_mutation_by_fingerprint(
            action_fingerprint
        )
        if executed is not None:
            error = GovernanceViolation(
                status_code=409,
                code="mutation.duplicate_action",
                message="This financial action has already been executed.",
                details={"action_fingerprint": action_fingerprint},
            )
            await self._record_financial_block(
                agent_run_id=agent_run_id,
                policy_id="approval.create_request",
                label=label,
                input_summary=input_summary,
                output_summary=output_summary,
                evidence_refs=evidence_refs,
                policy_refs=policy_refs,
                approval_refs=[],
                error=error,
            )
            raise error

        approval = await self._repository.create_approval_request(
            ticket_id=ticket_id,
            agent_run_id=agent_run_id,
            title=title,
            action_type=action_type,
            amount_cents=amount_cents,
            amount_display=amount_display,
            currency=currency,
            reason=reason,
            blocker=blocker,
            policy_citation=policy_citation,
            evidence_refs=evidence_refs,
            action_metadata=action_metadata,
            action_fingerprint=action_fingerprint,
        )
        await self.record_action(
            agent_run_id=agent_run_id,
            policy_id="approval.create_request",
            label=label,
            input_summary=input_summary,
            output_summary=output_summary,
            evidence_refs=evidence_refs,
            policy_refs=policy_refs,
            approval_refs=[approval.id],
        )
        return approval

    async def execute_approved_mock_refund(
        self,
        approval_id: str,
        *,
        decided_by: str,
        decision_note: str | None,
    ) -> ApprovalDecisionResponse:
        return await self.execute_approved_mock_financial_action(
            approval_id=approval_id,
            decided_by=decided_by,
            decision_note=decision_note,
        )

    async def execute_approved_mock_financial_action(
        self,
        approval_id: str,
        *,
        decided_by: str,
        decision_note: str | None,
    ) -> ApprovalDecisionResponse:
        approval = await self._repository.get_approval(approval_id)
        if approval is None:
            raise MeterDeskAPIError(
                status_code=404,
                code="approval.not_found",
                message="Approval request not found.",
            )
        if approval.status == "rejected":
            raise MeterDeskAPIError(
                status_code=409,
                code="approval.rejected_terminal",
                message="Rejected approval requests cannot be approved.",
            )
        if approval.status == "approved":
            mutation = await self._repository.get_mock_mutation_by_approval(approval_id)
            return ApprovalDecisionResponse(approval=approval, mock_mutation=mutation)

        existing_mutation = await self._repository.get_mock_mutation_by_approval(approval_id)
        mutation_policy_id = _mutation_policy_id(approval.action_type)
        try:
            approval, mutation = await self._repository.approve_request(
                approval_id=approval_id,
                decided_by=decided_by,
                decision_note=decision_note,
            )
        except MeterDeskAPIError as error:
            if approval.agent_run_id is not None:
                await self._record_financial_block(
                    agent_run_id=approval.agent_run_id,
                    policy_id=mutation_policy_id,
                    label="Blocked duplicate mock financial mutation",
                    input_summary=f"Attempted to execute approved request {approval.id}.",
                    output_summary=error.message,
                    evidence_refs=approval.evidence_refs,
                    policy_refs=[approval.policy_citation],
                    approval_refs=[approval.id],
                    error=error,
                )
            raise
        if existing_mutation is None and approval.agent_run_id is not None:
            await self.record_action(
                agent_run_id=approval.agent_run_id,
                policy_id=mutation_policy_id,
                label="Executed approved mock financial mutation",
                input_summary=f"Executed approved request {approval.id}.",
                output_summary=f"Created mock mutation {mutation.id}.",
                evidence_refs=approval.evidence_refs,
                policy_refs=[approval.policy_citation],
                approval_refs=[approval.id],
            )
        return ApprovalDecisionResponse(approval=approval, mock_mutation=mutation)

    async def _record_financial_block(
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
        error: MeterDeskAPIError,
    ) -> None:
        policy = get_tool_policy(policy_id)
        if policy is None:
            return
        metadata = _build_governance_metadata(
            policy=policy,
            evidence_refs=evidence_refs,
            policy_refs=policy_refs,
            approval_refs=approval_refs,
            negative_evidence_refs=[],
            reason_code=error.code,
        )
        await self._record_trace(
            agent_run_id=agent_run_id,
            policy=policy,
            label=label,
            input_summary=input_summary,
            output_summary=output_summary,
            evidence_refs=evidence_refs,
            policy_refs=policy_refs,
            approval_refs=approval_refs,
            governance_metadata=_blocked_metadata(metadata, error.code),
            error_state=error.code,
        )

    async def _record_trace(
        self,
        *,
        agent_run_id: str,
        policy: ToolPolicy,
        label: str,
        input_summary: str,
        output_summary: str,
        evidence_refs: list[str],
        policy_refs: list[str],
        approval_refs: list[str],
        governance_metadata: dict[str, object],
        error_state: str | None = None,
    ):
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
            governance_metadata=governance_metadata,
        )

    async def _record_blocked_trace(
        self,
        *,
        agent_run_id: str,
        policy: ToolPolicy | None,
        policy_id: str,
        label: str,
        input_summary: str,
        output_summary: str,
        evidence_refs: list[str],
        policy_refs: list[str],
        approval_refs: list[str],
        negative_evidence_refs: list[str],
        error: GovernanceViolation,
    ) -> None:
        traces = await self._repository.list_traces(agent_run_id)
        if traces is None:
            return
        metadata = (
            _build_governance_metadata(
                policy=policy,
                evidence_refs=evidence_refs,
                policy_refs=policy_refs,
                approval_refs=approval_refs,
                negative_evidence_refs=negative_evidence_refs,
                reason_code=error.code,
            )
            if policy is not None
            else _unknown_policy_metadata(policy_id, error.code)
        )
        await self._repository.add_tool_trace(
            agent_run_id=agent_run_id,
            category=policy.id if policy is not None else policy_id,
            risk=policy.risk if policy is not None else "Low",
            label=label,
            input_summary=input_summary,
            output_summary=output_summary,
            evidence_refs=evidence_refs,
            policy_refs=policy_refs,
            approval_refs=approval_refs,
            error_state=error.code,
            governance_metadata=_blocked_metadata(metadata, error.code),
        )

    async def _enforce_high_risk_approval(self, approval_refs: list[str]) -> None:
        if not approval_refs:
            raise GovernanceViolation(
                status_code=409,
                code="governance.approval_gate_blocked",
                message="High-risk action requires an approval reference",
            )
        for approval_ref in approval_refs:
            approval = await self._repository.get_approval(approval_ref)
            if approval is None:
                raise GovernanceViolation(
                    status_code=409,
                    code="governance.approval_gate_blocked",
                    message=f"Approval request not found: {approval_ref}",
                    details={"approval_id": approval_ref},
                )
            if approval.status != "approved":
                raise GovernanceViolation(
                    status_code=409,
                    code="governance.approval_gate_blocked",
                    message=f"High-risk action requires approved approval: {approval_ref}",
                    details={"approval_id": approval_ref, "approval_status": approval.status},
                )


def _build_governance_metadata(
    *,
    policy: ToolPolicy,
    evidence_refs: list[str],
    policy_refs: list[str],
    approval_refs: list[str],
    negative_evidence_refs: list[str],
    reason_code: str | None = None,
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
    resolved_reason_code = reason_code or (
        "governance.missing_required_ref" if missing else "governance.allowed"
    )
    return GovernanceMetadata(
        schema_version=GOVERNANCE_METADATA_SCHEMA_VERSION,
        policy_id=policy.id,
        policy_version=policy.version,
        risk=policy.risk,
        gate=policy.gate,
        gate_result="allowed" if not missing else "blocked",
        enforcement_outcome="trace_recorded" if not missing else "blocked_before_execution",
        required_ref_categories=required,
        satisfied_ref_categories=[category for category in required if category in satisfied],
        missing_ref_categories=missing,
        negative_evidence_refs=negative_evidence_refs,
        trace_required=policy.trace_required,
        reason_code=resolved_reason_code,
    ).model_dump()


def _blocked_metadata(
    metadata: dict[str, object],
    reason_code: str,
) -> dict[str, object]:
    return {
        **metadata,
        "gate_result": "blocked",
        "enforcement_outcome": "blocked_before_execution",
        "reason_code": reason_code,
    }


def _unknown_policy_metadata(policy_id: str, reason_code: str) -> dict[str, object]:
    return GovernanceMetadata(
        schema_version=GOVERNANCE_METADATA_SCHEMA_VERSION,
        policy_id=policy_id,
        policy_version="unknown",
        risk="Low",
        gate="Unknown governance policy",
        gate_result="blocked",
        enforcement_outcome="blocked_before_execution",
        required_ref_categories=[],
        satisfied_ref_categories=[],
        missing_ref_categories=[],
        negative_evidence_refs=[],
        trace_required=True,
        reason_code=reason_code,
    ).model_dump()


def _mutation_policy_id(action_type: str) -> str:
    if action_type == "original_refund":
        return "mutation.mock_refund"
    return "mutation.mock_credit_or_refund"


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
        if normalized.startswith("subscription "):
            categories.add("subscription")
        if normalized.startswith("prior_adjustment "):
            categories.add("prior_adjustment")
        if normalized.startswith("ticket "):
            categories.add("ticket")
        if normalized.startswith("policy "):
            categories.add("policy")
    return categories
