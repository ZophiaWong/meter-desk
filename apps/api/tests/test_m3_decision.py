from __future__ import annotations

from meterdesk_api.agent.decision import (
    DuplicateChargeDecisionInput,
    DuplicateChargeDecisionTool,
    extract_duplicate_charge_payment_facts,
)
from meterdesk_api.seed_data import BILLING_EVIDENCE


def test_duplicate_charge_decision_confirms_refund_when_two_captures_match_invoice() -> None:
    evidence = BILLING_EVIDENCE["TCK-1042"]

    decision = DuplicateChargeDecisionTool().evaluate(
        DuplicateChargeDecisionInput(
            ticket_id="TCK-1042",
            evidence=evidence,
            pending_approval_exists=False,
            executed_action_metadata=[],
        )
    )

    assert decision.outcome == "confirmed_duplicate_charge"
    assert decision.requires_approval is True
    assert decision.action_type == "original_refund"
    assert decision.amount_cents == evidence.invoice.total.amount_cents
    assert decision.currency == "USD"
    assert decision.target_charge_id == "ch_2026_0418_B"
    assert decision.policy_refs == ["REFUND-DUP-001 v2026.02"]
    assert "charge ch_2026_0418_B" in decision.evidence_refs


def test_duplicate_charge_decision_blocks_when_pending_approval_exists() -> None:
    evidence = BILLING_EVIDENCE["TCK-1042"]

    decision = DuplicateChargeDecisionTool().evaluate(
        DuplicateChargeDecisionInput(
            ticket_id="TCK-1042",
            evidence=evidence,
            pending_approval_exists=True,
            executed_action_metadata=[],
        )
    )

    assert decision.outcome == "pending_approval_exists"
    assert decision.requires_approval is False
    assert decision.action_type is None


def test_duplicate_charge_decision_does_not_propose_duplicate_after_mock_execution() -> None:
    evidence = BILLING_EVIDENCE["TCK-1042"]

    decision = DuplicateChargeDecisionTool().evaluate(
        DuplicateChargeDecisionInput(
            ticket_id="TCK-1042",
            evidence=evidence,
            pending_approval_exists=False,
            executed_action_metadata=[
                {
                    "action_type": "original_refund",
                    "invoice_id": "INV-2026-0418",
                    "target_charge_id": "ch_2026_0418_B",
                }
            ],
        )
    )

    assert decision.outcome == "duplicate_action_already_executed"
    assert decision.requires_approval is False


def test_duplicate_charge_decision_returns_insufficient_evidence_for_single_capture() -> None:
    evidence = BILLING_EVIDENCE["TCK-1042"].model_copy(
        update={"charges": [BILLING_EVIDENCE["TCK-1042"].charges[0]]}
    )

    decision = DuplicateChargeDecisionTool().evaluate(
        DuplicateChargeDecisionInput(
            ticket_id="TCK-1042",
            evidence=evidence,
            pending_approval_exists=False,
            executed_action_metadata=[],
        )
    )

    assert decision.outcome == "insufficient_evidence_human_review"
    assert decision.requires_approval is False
    assert decision.amount_cents is None


def test_duplicate_charge_decision_identifies_uncaptured_authorization() -> None:
    captured = BILLING_EVIDENCE["TCK-1042"].charges[0]
    authorization = (
        BILLING_EVIDENCE["TCK-1042"]
        .charges[1]
        .model_copy(
            update={
                "id": "auth_2026_0418_B",
                "status": "Authorized",
                "processor_state": "Authorization only; not captured",
            }
        )
    )
    evidence = BILLING_EVIDENCE["TCK-1042"].model_copy(
        update={"charges": [captured, authorization]}
    )

    facts = extract_duplicate_charge_payment_facts(evidence)
    decision = DuplicateChargeDecisionTool().evaluate(
        DuplicateChargeDecisionInput(
            ticket_id="TCK-1042",
            evidence=evidence,
            pending_approval_exists=False,
            executed_action_metadata=[],
        )
    )

    assert facts.captured_invoice_total_count == 1
    assert facts.has_matching_uncaptured_authorization is True
    assert decision.outcome == "no_refund_expected_billing_behavior"
    assert decision.requires_approval is False
    assert "auth_2026_0418_B" in " ".join(decision.evidence_refs)
