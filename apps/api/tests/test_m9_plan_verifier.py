from __future__ import annotations

import pytest

from meterdesk_api.agent.governance import get_tool_policy
from meterdesk_api.schemas import TicketDetail
from meterdesk_api.seed_data import TICKET_DETAILS


def _planning_module():
    try:
        from meterdesk_api.agent import planning
    except ImportError as error:
        pytest.fail(f"M9 planning module is missing: {error}")
    return planning


def _ticket(ticket_id: str) -> TicketDetail:
    ticket = TICKET_DETAILS[ticket_id]
    assert ticket is not None
    return ticket


def test_plan_tool_policies_are_registered() -> None:
    investigation = get_tool_policy("plan.investigation")
    verification = get_tool_policy("plan.verify")

    assert investigation is not None
    assert investigation.category == "plan"
    assert investigation.risk == "Low"
    assert investigation.executor == "provider_planner"
    assert investigation.eval_dimensions == ["tool_planning"]

    assert verification is not None
    assert verification.category == "plan"
    assert verification.risk == "Low"
    assert verification.executor == "backend_plan_verifier"
    assert verification.eval_dimensions == ["tool_planning"]


def test_investigation_plan_schema_is_openai_strict_compatible() -> None:
    planning = _planning_module()

    schema = planning.InvestigationPlan.model_json_schema()
    step_schema = schema["$defs"]["InvestigationPlanStep"]

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert step_schema["additionalProperties"] is False
    assert set(step_schema["required"]) == set(step_schema["properties"])


def test_planner_input_includes_required_targets_by_action_for_duplicate_charge() -> None:
    planning = _planning_module()

    planner_input = planning.build_planner_input(_ticket("TCK-1042"))

    assert planner_input.required_targets_by_action == {
        "read.billing_evidence": [
            "account_state",
            "invoice",
            "charges",
            "payment_status",
            "credit_ledger",
            "usage",
            "policy",
        ],
        "read.prior_financial_actions": ["prior_financial_actions"],
        "decision.refund_eligibility": [
            "invoice",
            "charges",
            "policy",
            "prior_financial_actions",
        ],
    }


def test_planner_input_includes_required_targets_by_action_for_credit_refund() -> None:
    planning = _planning_module()

    planner_input = planning.build_planner_input(_ticket("TCK-1137"))

    assert planner_input.required_targets_by_action == {
        "read.credit_refund_evidence": [
            "account_state",
            "invoice",
            "charges",
            "payment_status",
            "credit_ledger",
            "subscription",
            "policy",
        ],
        "read.prior_financial_actions": ["prior_financial_actions"],
        "decision.credit_refund_eligibility": [
            "invoice",
            "charges",
            "credit_ledger",
            "subscription",
            "policy",
            "prior_financial_actions",
        ],
    }


def test_verifier_accepts_duplicate_charge_plan_and_normalizes_read_order() -> None:
    planning = _planning_module()
    plan = planning.InvestigationPlan(
        scenario="duplicate_charge",
        plan_summary="Investigate billing evidence, prior actions, and refund eligibility.",
        steps=[
            planning.InvestigationPlanStep(
                step_id="prior",
                action_id="read.prior_financial_actions",
                evidence_targets=["prior_financial_actions"],
                rationale="Check prior financial actions to avoid duplicate refunds.",
                depends_on=[],
            ),
            planning.InvestigationPlanStep(
                step_id="evidence",
                action_id="read.billing_evidence",
                evidence_targets=[
                    "account_state",
                    "invoice",
                    "charges",
                    "payment_status",
                    "credit_ledger",
                    "usage",
                    "policy",
                ],
                rationale="Read invoice, charges, credit, usage, and policy evidence.",
                depends_on=[],
            ),
            planning.InvestigationPlanStep(
                step_id="decision",
                action_id="decision.refund_eligibility",
                evidence_targets=["invoice", "charges", "policy", "prior_financial_actions"],
                rationale="Ask the backend decision tool to classify refund eligibility.",
                depends_on=["prior", "evidence"],
            ),
        ],
        evidence_gaps=[],
        stop_conditions=["Stop if required billing evidence is missing."],
    )

    result = planning.PlanContractVerifier().verify(_ticket("TCK-1042"), plan)

    assert result.status == "accepted"
    assert result.reason_codes == []
    assert result.normalized_action_ids == [
        "read.billing_evidence",
        "read.prior_financial_actions",
        "decision.refund_eligibility",
    ]
    assert result.required_targets_seen == [
        "account_state",
        "invoice",
        "charges",
        "payment_status",
        "credit_ledger",
        "usage",
        "policy",
        "prior_financial_actions",
    ]


def test_verifier_feedback_identifies_duplicate_decision_missing_targets() -> None:
    planning = _planning_module()
    plan = planning.InvestigationPlan(
        scenario="duplicate_charge",
        plan_summary="Read duplicate evidence but omit decision targets.",
        steps=[
            planning.InvestigationPlanStep(
                step_id="evidence",
                action_id="read.billing_evidence",
                evidence_targets=[
                    "account_state",
                    "invoice",
                    "charges",
                    "payment_status",
                    "credit_ledger",
                    "usage",
                    "policy",
                ],
                rationale="Read invoice, charges, credit, usage, and policy evidence.",
                depends_on=[],
            ),
            planning.InvestigationPlanStep(
                step_id="prior",
                action_id="read.prior_financial_actions",
                evidence_targets=["prior_financial_actions"],
                rationale="Check prior financial actions to avoid duplicate refunds.",
                depends_on=[],
            ),
            planning.InvestigationPlanStep(
                step_id="decision",
                action_id="decision.refund_eligibility",
                evidence_targets=[],
                rationale="Ask the backend decision tool to classify refund eligibility.",
                depends_on=["evidence", "prior"],
            ),
        ],
        evidence_gaps=[],
        stop_conditions=[],
    )

    result = planning.PlanContractVerifier().verify(_ticket("TCK-1042"), plan)

    assert result.status == "blocked"
    assert "plan.missing_required_target" in result.reason_codes
    assert result.feedback_items == [
        planning.PlanVerifierFeedbackItem(
            reason_code="plan.missing_required_target",
            action_id="decision.refund_eligibility",
            missing_targets=["invoice", "charges", "policy", "prior_financial_actions"],
        )
    ]


def test_verifier_blocks_unsafe_financial_actions() -> None:
    planning = _planning_module()
    plan = planning.InvestigationPlan(
        scenario="duplicate_charge",
        plan_summary="Unsafe plan that attempts to create approval directly.",
        steps=[
            planning.InvestigationPlanStep(
                step_id="approval",
                action_id="approval.create_request",
                evidence_targets=["invoice", "charges", "policy"],
                rationale="Create the approval request directly.",
                depends_on=[],
            )
        ],
        evidence_gaps=[],
        stop_conditions=[],
    )

    result = planning.PlanContractVerifier().verify(_ticket("TCK-1042"), plan)

    assert result.status == "blocked"
    assert "plan.unsafe_financial_action" in result.reason_codes
    assert "plan.missing_required_action" in result.reason_codes


def test_verifier_feedback_identifies_credit_decision_missing_targets() -> None:
    planning = _planning_module()
    plan = planning.InvestigationPlan(
        scenario="credit_refund_dispute",
        plan_summary="Read credit evidence but omit decision targets.",
        steps=[
            planning.InvestigationPlanStep(
                step_id="evidence",
                action_id="read.credit_refund_evidence",
                evidence_targets=[
                    "account_state",
                    "invoice",
                    "charges",
                    "payment_status",
                    "credit_ledger",
                    "subscription",
                    "policy",
                ],
                rationale="Collect credit/refund evidence.",
                depends_on=[],
            ),
            planning.InvestigationPlanStep(
                step_id="prior",
                action_id="read.prior_financial_actions",
                evidence_targets=["prior_financial_actions"],
                rationale="Check prior financial actions.",
                depends_on=[],
            ),
            planning.InvestigationPlanStep(
                step_id="decision",
                action_id="decision.credit_refund_eligibility",
                evidence_targets=[],
                rationale="Ask the backend decision tool to classify credit eligibility.",
                depends_on=["evidence", "prior"],
            ),
        ],
        evidence_gaps=[],
        stop_conditions=[],
    )

    result = planning.PlanContractVerifier().verify(_ticket("TCK-1137"), plan)

    assert result.status == "blocked"
    assert result.feedback_items == [
        planning.PlanVerifierFeedbackItem(
            reason_code="plan.missing_required_target",
            action_id="decision.credit_refund_eligibility",
            missing_targets=[
                "invoice",
                "charges",
                "credit_ledger",
                "subscription",
                "policy",
                "prior_financial_actions",
            ],
        )
    ]


def test_verifier_accepts_credit_refund_plan() -> None:
    planning = _planning_module()
    plan = planning.InvestigationPlan(
        scenario="credit_refund_dispute",
        plan_summary="Investigate credit ledger, subscription, invoice, and prior actions.",
        steps=[
            planning.InvestigationPlanStep(
                step_id="evidence",
                action_id="read.credit_refund_evidence",
                evidence_targets=[
                    "account_state",
                    "invoice",
                    "charges",
                    "payment_status",
                    "credit_ledger",
                    "subscription",
                    "policy",
                ],
                rationale=(
                    "Collect credit ledger, subscription, invoice, charge, and policy evidence."
                ),
                depends_on=[],
            ),
            planning.InvestigationPlanStep(
                step_id="prior",
                action_id="read.prior_financial_actions",
                evidence_targets=["prior_financial_actions"],
                rationale="Check prior financial actions to avoid duplicate credits or refunds.",
                depends_on=[],
            ),
            planning.InvestigationPlanStep(
                step_id="decision",
                action_id="decision.credit_refund_eligibility",
                evidence_targets=[
                    "invoice",
                    "charges",
                    "credit_ledger",
                    "subscription",
                    "policy",
                    "prior_financial_actions",
                ],
                rationale="Ask the backend decision tool to classify credit/refund eligibility.",
                depends_on=["evidence", "prior"],
            ),
        ],
        evidence_gaps=[],
        stop_conditions=["Stop if subscription or credit ledger evidence is unavailable."],
    )

    result = planning.PlanContractVerifier().verify(_ticket("TCK-1137"), plan)

    assert result.status == "accepted"
    assert result.normalized_action_ids == [
        "read.credit_refund_evidence",
        "read.prior_financial_actions",
        "decision.credit_refund_eligibility",
    ]
    assert result.required_targets_seen == [
        "account_state",
        "invoice",
        "charges",
        "payment_status",
        "credit_ledger",
        "subscription",
        "policy",
        "prior_financial_actions",
    ]
