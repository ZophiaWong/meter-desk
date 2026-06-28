from __future__ import annotations

from meterdesk_api.agent.decision import CreditRefundDecisionInput, CreditRefundDecisionTool
from meterdesk_api.seed_data import BILLING_EVIDENCE


def test_trial_credit_dispute_recommends_goodwill_credit_for_remaining_disputed_credit() -> None:
    decision = CreditRefundDecisionTool().evaluate(
        CreditRefundDecisionInput(
            ticket_id="TCK-1137",
            evidence=BILLING_EVIDENCE["TCK-1137"],
            executed_action_metadata=[],
        )
    )

    assert decision.outcome == "goodwill_credit_requires_approval"
    assert decision.requires_approval is True
    assert decision.action_type == "goodwill_credit"
    assert decision.amount_cents == 12000
    assert decision.amount_display == "$120.00"
    assert decision.currency == "USD"
    assert decision.target_credit_id == "cred-ledger-1137"
    assert decision.policy_refs == ["TRIAL-CREDIT-003 v2026.03"]
    assert decision.evidence_refs == [
        "credit cred-ledger-1137",
        "subscription sub-helio-2026",
        "invoice INV-2026-0312",
        "policy TRIAL-CREDIT-003 v2026.03",
    ]
    assert decision.action_metadata == {
        "action_type": "goodwill_credit",
        "credit_ledger_entry_id": "cred-ledger-1137",
        "subscription_id": "sub-helio-2026",
        "action_basis": "goodwill_credit_requires_approval",
    }


def test_prior_adjustment_prevents_duplicate_credit_mutation() -> None:
    decision = CreditRefundDecisionTool().evaluate(
        CreditRefundDecisionInput(
            ticket_id="TCK-1137",
            evidence=BILLING_EVIDENCE["TCK-1137"],
            executed_action_metadata=[
                {
                    "action_type": "goodwill_credit",
                    "credit_ledger_entry_id": "cred-ledger-1137",
                    "action_fingerprint": (
                        "ticket:TCK-1137|action:goodwill_credit|target:cred-ledger-1137|"
                        "amount:12000|currency:USD"
                    ),
                }
            ],
        )
    )

    assert decision.outcome == "prior_adjustment_already_applied"
    assert decision.requires_approval is False
    assert decision.action_type is None
    assert decision.policy_refs == ["ADJUSTMENT-LIMIT-002 v2026.03"]
    assert decision.evidence_refs == [
        "credit cred-ledger-1137",
        "subscription sub-helio-2026",
        "invoice INV-2026-0312",
        "prior_adjustment ticket TCK-1137",
        "policy ADJUSTMENT-LIMIT-002 v2026.03",
    ]
