from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from meterdesk_api.agent.governance import get_tool_policy
from meterdesk_api.schemas import TicketDetail

PlanStatus = Literal["accepted", "blocked"]

FORBIDDEN_PLANNED_ACTIONS = {
    "approval.create_request",
    "draft.resolution",
    "mutation.mock_refund",
    "mutation.mock_credit_or_refund",
}


class InvestigationPlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    action_id: str
    evidence_targets: list[str]
    rationale: str
    depends_on: list[str]


class InvestigationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: str
    plan_summary: str
    steps: list[InvestigationPlanStep]
    evidence_gaps: list[str]
    stop_conditions: list[str]


class PlanVerifierFeedbackItem(BaseModel):
    reason_code: str
    action_id: str | None = None
    missing_targets: list[str] = Field(default_factory=list)


class VerifiedInvestigationPlan(BaseModel):
    status: PlanStatus
    reason_codes: list[str] = Field(default_factory=list)
    normalized_action_ids: list[str] = Field(default_factory=list)
    required_targets_seen: list[str] = Field(default_factory=list)
    feedback_items: list[PlanVerifierFeedbackItem] = Field(default_factory=list)


class InvestigationPlannerInput(BaseModel):
    ticket_id: str
    title: str
    summary: str
    scenario: str
    allowed_action_ids: list[str]
    evidence_target_vocabulary: list[str]
    required_action_ids: list[str]
    required_targets: list[str]
    required_targets_by_action: dict[str, list[str]]


@dataclass(frozen=True)
class ScenarioPlanContract:
    scenario: str
    action_order: tuple[str, ...]
    required_targets: tuple[str, ...]
    required_targets_by_action: dict[str, tuple[str, ...]]
    decision_action_id: str


DUPLICATE_CHARGE_PLAN_CONTRACT = ScenarioPlanContract(
    scenario="duplicate_charge",
    action_order=(
        "read.billing_evidence",
        "read.prior_financial_actions",
        "decision.refund_eligibility",
    ),
    required_targets=(
        "account_state",
        "invoice",
        "charges",
        "payment_status",
        "credit_ledger",
        "usage",
        "policy",
        "prior_financial_actions",
    ),
    required_targets_by_action={
        "read.billing_evidence": (
            "account_state",
            "invoice",
            "charges",
            "payment_status",
            "credit_ledger",
            "usage",
            "policy",
        ),
        "read.prior_financial_actions": ("prior_financial_actions",),
        "decision.refund_eligibility": (
            "invoice",
            "charges",
            "policy",
            "prior_financial_actions",
        ),
    },
    decision_action_id="decision.refund_eligibility",
)

CREDIT_REFUND_PLAN_CONTRACT = ScenarioPlanContract(
    scenario="credit_refund_dispute",
    action_order=(
        "read.credit_refund_evidence",
        "read.prior_financial_actions",
        "decision.credit_refund_eligibility",
    ),
    required_targets=(
        "account_state",
        "invoice",
        "charges",
        "payment_status",
        "credit_ledger",
        "subscription",
        "policy",
        "prior_financial_actions",
    ),
    required_targets_by_action={
        "read.credit_refund_evidence": (
            "account_state",
            "invoice",
            "charges",
            "payment_status",
            "credit_ledger",
            "subscription",
            "policy",
        ),
        "read.prior_financial_actions": ("prior_financial_actions",),
        "decision.credit_refund_eligibility": (
            "invoice",
            "charges",
            "credit_ledger",
            "subscription",
            "policy",
            "prior_financial_actions",
        ),
    },
    decision_action_id="decision.credit_refund_eligibility",
)

PLAN_CONTRACTS = {
    DUPLICATE_CHARGE_PLAN_CONTRACT.scenario: DUPLICATE_CHARGE_PLAN_CONTRACT,
    CREDIT_REFUND_PLAN_CONTRACT.scenario: CREDIT_REFUND_PLAN_CONTRACT,
}


def get_plan_contract(scenario: str) -> ScenarioPlanContract | None:
    return PLAN_CONTRACTS.get(scenario)


def build_planner_input(ticket: TicketDetail) -> InvestigationPlannerInput:
    contract = PLAN_CONTRACTS[ticket.scenario]
    return InvestigationPlannerInput(
        ticket_id=ticket.id,
        title=ticket.title,
        summary=ticket.summary,
        scenario=ticket.scenario,
        allowed_action_ids=list(contract.action_order),
        evidence_target_vocabulary=list(contract.required_targets),
        required_action_ids=list(contract.action_order),
        required_targets=list(contract.required_targets),
        required_targets_by_action={
            action_id: list(targets)
            for action_id, targets in contract.required_targets_by_action.items()
        },
    )


class PlanContractVerifier:
    def verify(
        self,
        ticket: TicketDetail,
        plan: InvestigationPlan,
    ) -> VerifiedInvestigationPlan:
        contract = PLAN_CONTRACTS.get(ticket.scenario)
        if contract is None:
            return VerifiedInvestigationPlan(
                status="blocked",
                reason_codes=["plan.unsupported_scenario"],
            )

        reason_codes: list[str] = []
        feedback_items: list[PlanVerifierFeedbackItem] = []
        if plan.scenario != ticket.scenario:
            reason_codes.append("plan.scenario_mismatch")
            feedback_items.append(PlanVerifierFeedbackItem(reason_code="plan.scenario_mismatch"))

        steps_by_action: dict[str, InvestigationPlanStep] = {}
        step_ids = {step.step_id for step in plan.steps}
        for step in plan.steps:
            if not step.rationale.strip():
                reason_codes.append("plan.missing_rationale")
                feedback_items.append(
                    PlanVerifierFeedbackItem(
                        reason_code="plan.missing_rationale",
                        action_id=step.action_id,
                    )
                )
            if step.action_id in FORBIDDEN_PLANNED_ACTIONS or step.action_id.startswith(
                "mutation."
            ):
                reason_codes.append("plan.unsafe_financial_action")
                feedback_items.append(
                    PlanVerifierFeedbackItem(
                        reason_code="plan.unsafe_financial_action",
                        action_id=step.action_id,
                    )
                )
                continue
            policy = get_tool_policy(step.action_id)
            if policy is None:
                reason_codes.append("plan.unknown_action")
                feedback_items.append(
                    PlanVerifierFeedbackItem(
                        reason_code="plan.unknown_action",
                        action_id=step.action_id,
                    )
                )
                continue
            if step.action_id not in contract.action_order:
                reason_codes.append("plan.disallowed_action")
                feedback_items.append(
                    PlanVerifierFeedbackItem(
                        reason_code="plan.disallowed_action",
                        action_id=step.action_id,
                    )
                )
                continue
            if step.action_id in steps_by_action:
                reason_codes.append("plan.duplicate_action")
                feedback_items.append(
                    PlanVerifierFeedbackItem(
                        reason_code="plan.duplicate_action",
                        action_id=step.action_id,
                    )
                )
            steps_by_action[step.action_id] = step
            unknown_targets = set(step.evidence_targets) - set(contract.required_targets)
            if unknown_targets:
                reason_codes.append("plan.unknown_target")
                feedback_items.append(
                    PlanVerifierFeedbackItem(
                        reason_code="plan.unknown_target",
                        action_id=step.action_id,
                    )
                )
            missing_step_targets = [
                target
                for target in contract.required_targets_by_action[step.action_id]
                if target not in step.evidence_targets
            ]
            if missing_step_targets:
                reason_codes.append("plan.missing_required_target")
                feedback_items.append(
                    PlanVerifierFeedbackItem(
                        reason_code="plan.missing_required_target",
                        action_id=step.action_id,
                        missing_targets=missing_step_targets,
                    )
                )
            missing_dependencies = set(step.depends_on) - step_ids
            if missing_dependencies:
                reason_codes.append("plan.dependency_violation")
                feedback_items.append(
                    PlanVerifierFeedbackItem(
                        reason_code="plan.dependency_violation",
                        action_id=step.action_id,
                    )
                )

        missing_actions = [
            action_id for action_id in contract.action_order if action_id not in steps_by_action
        ]
        if missing_actions:
            reason_codes.append("plan.missing_required_action")
            feedback_items.extend(
                PlanVerifierFeedbackItem(
                    reason_code="plan.missing_required_action",
                    action_id=action_id,
                )
                for action_id in missing_actions
            )

        planned_action_positions = {
            step.action_id: index
            for index, step in enumerate(plan.steps)
            if step.action_id in steps_by_action
        }
        decision_position = planned_action_positions.get(contract.decision_action_id)
        if decision_position is not None:
            read_positions = [
                planned_action_positions[action_id]
                for action_id in contract.action_order
                if action_id != contract.decision_action_id
                and action_id in planned_action_positions
            ]
            if any(position > decision_position for position in read_positions):
                reason_codes.append("plan.dependency_violation")
                feedback_items.append(
                    PlanVerifierFeedbackItem(
                        reason_code="plan.dependency_violation",
                        action_id=contract.decision_action_id,
                    )
                )

        required_targets_seen = [
            target
            for target in contract.required_targets
            if any(target in step.evidence_targets for step in steps_by_action.values())
        ]
        missing_targets = set(contract.required_targets) - set(required_targets_seen)
        if missing_targets:
            reason_codes.append("plan.missing_required_target")
            feedback_items.append(
                PlanVerifierFeedbackItem(
                    reason_code="plan.missing_required_target",
                    missing_targets=[
                        target
                        for target in contract.required_targets
                        if target not in required_targets_seen
                    ],
                )
            )

        unique_reason_codes = list(dict.fromkeys(reason_codes))
        if unique_reason_codes:
            return VerifiedInvestigationPlan(
                status="blocked",
                reason_codes=unique_reason_codes,
                normalized_action_ids=[
                    action_id for action_id in contract.action_order if action_id in steps_by_action
                ],
                required_targets_seen=required_targets_seen,
                feedback_items=feedback_items,
            )

        return VerifiedInvestigationPlan(
            status="accepted",
            normalized_action_ids=list(contract.action_order),
            required_targets_seen=list(contract.required_targets),
        )
