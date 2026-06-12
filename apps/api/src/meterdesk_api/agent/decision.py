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
class DuplicateChargePaymentFacts:
    captured_invoice_total_count: int
    captured_invoice_total_refs: list[str]
    matching_uncaptured_authorization_refs: list[str]

    @property
    def has_matching_uncaptured_authorization(self) -> bool:
        return bool(self.matching_uncaptured_authorization_refs)


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

        facts = extract_duplicate_charge_payment_facts(evidence)

        if facts.captured_invoice_total_count < 2 and facts.has_matching_uncaptured_authorization:
            return DuplicateChargeDecision(
                outcome="no_refund_expected_billing_behavior",
                requires_approval=False,
                reason=(
                    "The second matching payment event is an authorization that was not captured, "
                    "so no refund or credit action is warranted from the available evidence."
                ),
                evidence_refs=[invoice_ref]
                + facts.captured_invoice_total_refs
                + facts.matching_uncaptured_authorization_refs,
                policy_refs=policy_refs,
            )

        if facts.captured_invoice_total_count < 2:
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

        captured_matches = [
            charge
            for charge in evidence.charges
            if f"charge {charge.id}" in facts.captured_invoice_total_refs
        ]
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


def extract_duplicate_charge_payment_facts(
    evidence: BillingEvidence,
) -> DuplicateChargePaymentFacts:
    captured_refs: list[str] = []
    authorization_refs: list[str] = []
    for charge in evidence.charges:
        matches_invoice_total = (
            charge.amount.amount_cents == evidence.invoice.total.amount_cents
            and charge.amount.currency == evidence.invoice.total.currency
        )
        if not matches_invoice_total:
            continue

        normalized_status = charge.status.lower()
        if normalized_status == "captured":
            captured_refs.append(f"charge {charge.id}")
        elif normalized_status in {"authorized", "authorization", "pending_authorization"}:
            authorization_refs.append(f"charge {charge.id}")

    return DuplicateChargePaymentFacts(
        captured_invoice_total_count=len(captured_refs),
        captured_invoice_total_refs=captured_refs,
        matching_uncaptured_authorization_refs=authorization_refs,
    )
