from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from meterdesk_api.schemas import BillingEvidence


class DuplicateChargeDecisionInput(BaseModel):
    ticket_id: str
    evidence: BillingEvidence
    pending_approval_exists: bool
    executed_action_metadata: list[dict[str, Any]]


@dataclass(frozen=True)
class DuplicateChargeDecision:
    outcome: str
    requires_approval: bool
    reason: str
    evidence_refs: list[str]
    policy_refs: list[str]
    action_type: str | None = None
    amount_cents: int | None = None
    amount_display: str | None = None
    currency: str | None = None
    invoice_id: str | None = None
    target_charge_id: str | None = None

    @property
    def action_metadata(self) -> dict[str, Any]:
        if self.action_type is None:
            return {}
        return {
            "action_type": self.action_type,
            "invoice_id": self.invoice_id,
            "target_charge_id": self.target_charge_id,
            "action_basis": self.outcome,
        }


class DuplicateChargeDecisionTool:
    def evaluate(self, decision_input: DuplicateChargeDecisionInput) -> DuplicateChargeDecision:
        evidence = decision_input.evidence
        policy_refs = [evidence.policy.citation]
        invoice_ref = f"invoice {evidence.invoice.id}"

        if decision_input.pending_approval_exists:
            return DuplicateChargeDecision(
                outcome="pending_approval_exists",
                requires_approval=False,
                reason="A pending financial approval already exists for this ticket.",
                evidence_refs=[invoice_ref],
                policy_refs=policy_refs,
            )

        captured_matches = [
            charge
            for charge in evidence.charges
            if charge.status.lower() == "captured"
            and charge.amount.amount_cents == evidence.invoice.total.amount_cents
            and charge.amount.currency == evidence.invoice.total.currency
        ]

        if len(captured_matches) < 2:
            return DuplicateChargeDecision(
                outcome="insufficient_evidence_human_review",
                requires_approval=False,
                reason=(
                    "Fewer than two captured charges match the paid invoice total, so a duplicate "
                    "refund cannot be proposed from the available evidence."
                ),
                evidence_refs=[invoice_ref]
                + [f"charge {charge.id}" for charge in evidence.charges],
                policy_refs=policy_refs,
            )

        target_charge = captured_matches[-1]
        action_metadata = {
            "action_type": "original_refund",
            "invoice_id": evidence.invoice.id,
            "target_charge_id": target_charge.id,
        }
        already_executed = any(
            _metadata_matches(action_metadata, item)
            for item in decision_input.executed_action_metadata
        )
        if already_executed:
            return DuplicateChargeDecision(
                outcome="duplicate_action_already_executed",
                requires_approval=False,
                reason="A mock refund already exists for the duplicate captured charge.",
                evidence_refs=[invoice_ref, f"charge {target_charge.id}"],
                policy_refs=policy_refs,
            )

        return DuplicateChargeDecision(
            outcome="confirmed_duplicate_charge",
            requires_approval=True,
            action_type="original_refund",
            amount_cents=evidence.invoice.total.amount_cents,
            amount_display=evidence.invoice.total.display,
            currency=evidence.invoice.total.currency,
            invoice_id=evidence.invoice.id,
            target_charge_id=target_charge.id,
            reason=(
                f"Refund the duplicate captured charge {target_charge.id} to the original payment "
                "method after human approval."
            ),
            evidence_refs=[invoice_ref]
            + [f"charge {charge.id}" for charge in captured_matches]
            + [f"policy {evidence.policy.citation}"],
            policy_refs=policy_refs,
        )


def _metadata_matches(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    return all(actual.get(key) == value for key, value in expected.items())
