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


class CreditRefundDecisionInput(BaseModel):
    ticket_id: str
    evidence: BillingEvidence
    executed_action_metadata: list[dict[str, Any]]


@dataclass(frozen=True)
class CreditRefundDecision:
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
    target_credit_id: str | None = None
    subscription_id: str | None = None

    @property
    def action_metadata(self) -> dict[str, Any]:
        if self.action_type is None:
            return {}
        metadata: dict[str, Any] = {
            "action_type": self.action_type,
            "action_basis": self.outcome,
        }
        if self.target_charge_id is not None:
            metadata["target_charge_id"] = self.target_charge_id
        if self.target_credit_id is not None:
            metadata["credit_ledger_entry_id"] = self.target_credit_id
        if self.subscription_id is not None:
            metadata["subscription_id"] = self.subscription_id
        if self.invoice_id is not None:
            metadata["invoice_id"] = self.invoice_id
        return metadata


class CreditRefundDecisionTool:
    def evaluate(self, decision_input: CreditRefundDecisionInput) -> CreditRefundDecision:
        evidence = decision_input.evidence
        credit = evidence.credits[0] if evidence.credits else None
        subscription = evidence.subscription
        invoice_ref = f"invoice {evidence.invoice.id}"
        credit_ref = f"credit {credit.id}" if credit is not None else "credit missing"
        subscription_ref = (
            f"subscription {subscription.id}"
            if subscription is not None
            else "subscription missing"
        )

        trial_policy = _policy_citation(evidence, "TRIAL-CREDIT-003")
        cancellation_policy = _policy_citation(evidence, "CANCEL-REFUND-004")
        adjustment_policy = _policy_citation(evidence, "ADJUSTMENT-LIMIT-002")

        if _has_prior_adjustment(decision_input.ticket_id, credit, decision_input):
            return CreditRefundDecision(
                outcome="prior_adjustment_already_applied",
                requires_approval=False,
                reason=(
                    "A prior mock financial adjustment already exists for this credit dispute, "
                    "so a duplicate credit or refund should not be proposed."
                ),
                evidence_refs=[
                    credit_ref,
                    subscription_ref,
                    invoice_ref,
                    f"prior_adjustment ticket {decision_input.ticket_id}",
                    f"policy {adjustment_policy}",
                ],
                policy_refs=[adjustment_policy],
            )

        captured_charge = next(
            (charge for charge in evidence.charges if charge.status.lower() == "captured"),
            None,
        )
        if (
            subscription is not None
            and subscription.canceled_before_renewal_capture
            and captured_charge is not None
        ):
            return CreditRefundDecision(
                outcome="refund_requires_approval",
                requires_approval=True,
                action_type="original_refund",
                amount_cents=captured_charge.amount.amount_cents,
                amount_display=captured_charge.amount.display,
                currency=captured_charge.amount.currency,
                invoice_id=evidence.invoice.id,
                target_charge_id=captured_charge.id,
                subscription_id=subscription.id,
                reason=(
                    f"Refund captured charge {captured_charge.id} because cancellation occurred "
                    "before the renewal capture, after human approval."
                ),
                evidence_refs=[
                    f"charge {captured_charge.id}",
                    credit_ref,
                    subscription_ref,
                    invoice_ref,
                    f"policy {cancellation_policy}",
                ],
                policy_refs=[cancellation_policy],
            )

        disputed_amount = credit.disputed_amount if credit is not None else None
        if credit is not None and subscription is not None and disputed_amount is not None:
            return CreditRefundDecision(
                outcome="goodwill_credit_requires_approval",
                requires_approval=True,
                action_type="goodwill_credit",
                amount_cents=disputed_amount.amount_cents,
                amount_display=disputed_amount.display,
                currency=disputed_amount.currency,
                target_credit_id=credit.id,
                subscription_id=subscription.id,
                reason=(
                    f"Create a goodwill credit for the disputed remaining trial credit "
                    f"{disputed_amount.display} after human approval."
                ),
                evidence_refs=[
                    credit_ref,
                    subscription_ref,
                    invoice_ref,
                    f"policy {trial_policy}",
                ],
                policy_refs=[trial_policy],
            )

        return CreditRefundDecision(
            outcome="insufficient_evidence_human_review",
            requires_approval=False,
            reason="Credit/refund dispute evidence is incomplete, so human review is required.",
            evidence_refs=[credit_ref, subscription_ref, invoice_ref],
            policy_refs=[trial_policy],
        )


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


def _has_prior_adjustment(
    ticket_id: str,
    credit,
    decision_input: CreditRefundDecisionInput,
) -> bool:
    if credit is None:
        return False
    expected = {
        "action_type": "goodwill_credit",
        "credit_ledger_entry_id": credit.id,
    }
    return any(
        _metadata_matches(expected, item) for item in decision_input.executed_action_metadata
    )


def _policy_citation(evidence: BillingEvidence, policy_id: str) -> str:
    for policy in [*evidence.policies, evidence.policy]:
        if policy.id == policy_id:
            return policy.citation
    return evidence.policy.citation


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
