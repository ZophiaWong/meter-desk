from __future__ import annotations

from meterdesk_api.agent.decision import (
    CreditRefundDecisionInput,
    CreditRefundDecisionTool,
    DuplicateChargeDecisionInput,
    DuplicateChargeDecisionTool,
)
from meterdesk_api.agent.governance import GovernanceKernel
from meterdesk_api.agent.provider import (
    AgentDraftOutput,
    AgentProviderError,
    AgentProviderInput,
    AgentResolutionProvider,
    validate_provider_output,
)
from meterdesk_api.errors import MeterDeskAPIError
from meterdesk_api.repositories import MeterDeskRepository
from meterdesk_api.schemas import AgentRunSummary

DUPLICATE_CHARGE_PROMPT_VERSION = "m3-duplicate-charge-v1"
CREDIT_REFUND_PROMPT_VERSION = "m8-credit-refund-v1"


class AgentLoopError(MeterDeskAPIError):
    status_code = 400
    code = "agent.run_failed"
    message = "Agent run failed."

    def __init__(self, message: str | None = None, details: dict[str, object] | None = None):
        super().__init__(
            status_code=self.status_code,
            code=self.code,
            message=message or self.message,
            details=details,
        )


class UnsupportedScenarioError(AgentLoopError):
    status_code = 422
    code = "agent.unsupported_scenario"
    message = "Agent loop does not support this scenario yet."


class PendingApprovalError(AgentLoopError):
    status_code = 409
    code = "approval.pending_duplicate"
    message = "A pending financial approval already exists for this action."


class AgentRunOrchestrator:
    def __init__(
        self,
        repository: MeterDeskRepository,
        provider: AgentResolutionProvider,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._decision_tool = DuplicateChargeDecisionTool()
        self._credit_refund_decision_tool = CreditRefundDecisionTool()
        self._governance = GovernanceKernel(repository)

    async def run_ticket(self, ticket_id: str) -> AgentRunSummary | None:
        ticket = await self._repository.get_ticket(ticket_id)
        if ticket is None:
            return None
        if ticket.scenario == "duplicate_charge":
            return await self.run_duplicate_charge(ticket_id)
        if ticket.scenario == "credit_refund_dispute":
            return await self.run_credit_refund(ticket_id)
        raise UnsupportedScenarioError("Agent loop does not support this scenario yet.")

    async def run_duplicate_charge(self, ticket_id: str) -> AgentRunSummary | None:
        ticket = await self._repository.get_ticket(ticket_id)
        if ticket is None:
            return None
        if ticket.scenario != "duplicate_charge":
            raise UnsupportedScenarioError()

        pending_approval = await self._repository.get_pending_financial_approval(
            ticket_id=ticket_id,
            action_type="original_refund",
        )
        if pending_approval is not None:
            raise PendingApprovalError(
                details={"action_fingerprint": pending_approval.action_fingerprint}
            )

        evidence = await self._repository.get_billing_evidence(ticket_id)
        if evidence is None:
            return None

        run = await self._repository.create_agent_run(
            ticket_id=ticket_id,
            source="m3_governed_loop",
            model=self._provider.model,
            prompt_version=DUPLICATE_CHARGE_PROMPT_VERSION,
        )
        await self._governance.record_action(
            agent_run_id=run.id,
            policy_id="read.billing_evidence",
            label="Collected Duplicate Charge billing evidence",
            input_summary=(
                f"Read ticket, invoice, charges, credits, usage, and policy for {ticket_id}."
            ),
            output_summary=(
                f"Found invoice {evidence.invoice.id} with {len(evidence.charges)} charge records "
                f"and policy {evidence.policy.citation}."
            ),
            evidence_refs=[
                f"invoice {evidence.invoice.id}",
                *[f"charge {charge.id}" for charge in evidence.charges],
                *[f"credit {credit.id}" for credit in evidence.credits],
                *[f"usage {usage.id}" for usage in evidence.usage],
            ],
            policy_refs=[evidence.policy.citation],
            approval_refs=[],
        )

        executed_metadata = await self._repository.list_executed_action_metadata(ticket_id)
        negative_evidence_refs = ["no_prior_mock_mutation"] if not executed_metadata else []
        await self._governance.record_action(
            agent_run_id=run.id,
            policy_id="read.prior_financial_actions",
            label="Checked prior approvals and mock mutations",
            input_summary=f"Read existing approval and mutation state for {ticket_id}.",
            output_summary=f"Found {len(executed_metadata)} executed mock financial action(s).",
            evidence_refs=[f"ticket {ticket_id}"],
            policy_refs=[],
            approval_refs=[],
            negative_evidence_refs=negative_evidence_refs,
        )

        decision = self._decision_tool.evaluate(
            DuplicateChargeDecisionInput(
                ticket_id=ticket_id,
                evidence=evidence,
                pending_approval_exists=False,
                executed_action_metadata=executed_metadata,
            )
        )
        await self._governance.record_action(
            agent_run_id=run.id,
            policy_id="decision.refund_eligibility",
            label="Evaluated duplicate-charge refund eligibility",
            input_summary="Compared captured charges, invoice total, policy, and prior actions.",
            output_summary=decision.reason,
            evidence_refs=decision.evidence_refs,
            policy_refs=decision.policy_refs,
            approval_refs=[],
        )

        provider_input = AgentProviderInput(
            ticket_id=ticket_id,
            scenario="duplicate_charge",
            account_name=evidence.account.name,
            invoice_id=evidence.invoice.id,
            charge_ids=[charge.id for charge in evidence.charges],
            policy_citation=evidence.policy.citation,
            policy_citations=decision.policy_refs,
            decision_outcome=decision.outcome,
            decision_reason=decision.reason,
            action_type=decision.action_type,
            amount_display=decision.amount_display,
            target_charge_id=decision.target_charge_id,
        )
        provider_output, provider_error = await self._create_resolution_with_retry(provider_input)
        if provider_error is not None:
            await self._governance.record_action(
                agent_run_id=run.id,
                policy_id="draft.resolution",
                label="Provider draft failed validation",
                input_summary="Requested structured internal and customer-facing draft output.",
                output_summary="Provider failed after retry.",
                evidence_refs=decision.evidence_refs,
                policy_refs=decision.policy_refs,
                approval_refs=[],
                error_state=provider_error,
            )
            return await self._repository.fail_agent_run(run.id, provider_error)

        assert provider_output is not None
        # The decision tool owns the outcome; the provider only drafts text around it.
        run = await self._repository.complete_agent_run(
            agent_run_id=run.id,
            final_outcome=decision.outcome,
            internal_resolution=provider_output.internal_resolution,
            customer_reply=provider_output.customer_reply,
        )
        await self._governance.record_action(
            agent_run_id=run.id,
            policy_id="draft.resolution",
            label="Drafted governed resolution",
            input_summary="Requested strict structured recommendation and drafts from provider.",
            output_summary="Provider returned validated draft-only resolution output.",
            evidence_refs=decision.evidence_refs,
            policy_refs=decision.policy_refs,
            approval_refs=[],
        )

        if decision.requires_approval:
            await self._governance.create_approval_request(
                ticket_id=ticket_id,
                agent_run_id=run.id,
                title="Original refund pending approval",
                action_type=decision.action_type or "original_refund",
                amount_cents=decision.amount_cents or 0,
                amount_display=decision.amount_display or "$0.00",
                currency=decision.currency or evidence.invoice.total.currency,
                reason=decision.reason,
                blocker="Mutation blocked until human approval",
                policy_citation=evidence.policy.citation,
                evidence_refs=decision.evidence_refs,
                policy_refs=decision.policy_refs,
                action_metadata=decision.action_metadata,
                label="Created approval request for financial action",
                input_summary="Created human approval gate for proposed original refund.",
                output_summary="Approval request is pending.",
            )

        return run

    async def run_credit_refund(self, ticket_id: str) -> AgentRunSummary | None:
        ticket = await self._repository.get_ticket(ticket_id)
        if ticket is None:
            return None
        if ticket.scenario != "credit_refund_dispute":
            raise UnsupportedScenarioError(
                "Credit/Refund runner only supports Credit/Refund tickets."
            )

        evidence = await self._repository.get_billing_evidence(ticket_id)
        if evidence is None:
            return None

        run = await self._repository.create_agent_run(
            ticket_id=ticket_id,
            source="m8_credit_refund_loop",
            model=self._provider.model,
            prompt_version=CREDIT_REFUND_PROMPT_VERSION,
        )
        policy_refs = [policy.citation for policy in evidence.policies] or [
            evidence.policy.citation
        ]
        subscription_refs = (
            [f"subscription {evidence.subscription.id}"]
            if evidence.subscription is not None
            else []
        )
        read_evidence_refs = [
            f"invoice {evidence.invoice.id}",
            *[f"charge {charge.id}" for charge in evidence.charges],
            *[f"credit {credit.id}" for credit in evidence.credits],
            *subscription_refs,
        ]
        await self._governance.record_action(
            agent_run_id=run.id,
            policy_id="read.credit_refund_evidence",
            label="Collected Credit/Refund dispute evidence",
            input_summary=(
                f"Read ticket, subscription, invoice, charges, credit ledger, and policy for "
                f"{ticket_id}."
            ),
            output_summary=(
                f"Found invoice {evidence.invoice.id}, {len(evidence.credits)} credit ledger "
                f"entry, and {len(policy_refs)} policy citation(s)."
            ),
            evidence_refs=read_evidence_refs,
            policy_refs=policy_refs,
            approval_refs=[],
        )

        executed_metadata = await self._repository.list_executed_action_metadata(ticket_id)
        negative_evidence_refs = ["no_prior_mock_mutation"] if not executed_metadata else []
        await self._governance.record_action(
            agent_run_id=run.id,
            policy_id="read.prior_financial_actions",
            label="Checked prior approvals and mock mutations",
            input_summary=f"Read existing approval and mutation state for {ticket_id}.",
            output_summary=f"Found {len(executed_metadata)} executed mock financial action(s).",
            evidence_refs=[f"ticket {ticket_id}"],
            policy_refs=[],
            approval_refs=[],
            negative_evidence_refs=negative_evidence_refs,
        )

        decision = self._credit_refund_decision_tool.evaluate(
            CreditRefundDecisionInput(
                ticket_id=ticket_id,
                evidence=evidence,
                executed_action_metadata=executed_metadata,
            )
        )
        await self._governance.record_action(
            agent_run_id=run.id,
            policy_id="decision.credit_refund_eligibility",
            label="Evaluated credit/refund eligibility",
            input_summary=(
                "Compared credit ledger, cancellation timing, invoice, and prior actions."
            ),
            output_summary=decision.reason,
            evidence_refs=decision.evidence_refs,
            policy_refs=decision.policy_refs,
            approval_refs=[],
        )

        provider_input = AgentProviderInput(
            ticket_id=ticket_id,
            scenario="credit_refund_dispute",
            account_name=evidence.account.name,
            invoice_id=evidence.invoice.id,
            charge_ids=[charge.id for charge in evidence.charges],
            policy_citation=decision.policy_refs[0],
            policy_citations=decision.policy_refs,
            decision_outcome=decision.outcome,
            decision_reason=decision.reason,
            action_type=decision.action_type,
            amount_display=decision.amount_display,
            target_charge_id=decision.target_charge_id,
            target_credit_id=decision.target_credit_id,
            target_subscription_id=decision.subscription_id,
        )
        provider_output, provider_error = await self._create_resolution_with_retry(provider_input)
        if provider_error is not None:
            await self._governance.record_action(
                agent_run_id=run.id,
                policy_id="draft.resolution",
                label="Provider draft failed validation",
                input_summary="Requested structured internal and customer-facing draft output.",
                output_summary="Provider failed after retry.",
                evidence_refs=decision.evidence_refs,
                policy_refs=decision.policy_refs,
                approval_refs=[],
                error_state=provider_error,
            )
            return await self._repository.fail_agent_run(run.id, provider_error)

        assert provider_output is not None
        run = await self._repository.complete_agent_run(
            agent_run_id=run.id,
            final_outcome=decision.outcome,
            internal_resolution=provider_output.internal_resolution,
            customer_reply=provider_output.customer_reply,
        )
        await self._governance.record_action(
            agent_run_id=run.id,
            policy_id="draft.resolution",
            label="Drafted governed resolution",
            input_summary="Requested strict structured recommendation and drafts from provider.",
            output_summary="Provider returned validated draft-only resolution output.",
            evidence_refs=decision.evidence_refs,
            policy_refs=decision.policy_refs,
            approval_refs=[],
        )

        if decision.requires_approval:
            await self._governance.create_approval_request(
                ticket_id=ticket_id,
                agent_run_id=run.id,
                title=(
                    "Goodwill credit pending approval"
                    if decision.action_type == "goodwill_credit"
                    else "Original refund pending approval"
                ),
                action_type=decision.action_type or "goodwill_credit",
                amount_cents=decision.amount_cents or 0,
                amount_display=decision.amount_display or "$0.00",
                currency=decision.currency or evidence.invoice.total.currency,
                reason=decision.reason,
                blocker="Mutation blocked until human approval",
                policy_citation=decision.policy_refs[0],
                evidence_refs=decision.evidence_refs,
                policy_refs=decision.policy_refs,
                action_metadata=decision.action_metadata,
                label="Created approval request for financial action",
                input_summary="Created human approval gate for proposed credit/refund action.",
                output_summary="Approval request is pending.",
            )

        return run

    async def _create_resolution_with_retry(
        self,
        provider_input: AgentProviderInput,
    ) -> tuple[AgentDraftOutput | None, str | None]:
        last_error: str | None = None
        for _ in range(2):
            try:
                output = await self._provider.create_resolution(provider_input)
                validate_provider_output(output)
                return output, None
            except AgentProviderError as error:
                last_error = str(error)
        return None, f"Provider failed after retry: {last_error}"
