from __future__ import annotations

from meterdesk_api.agent.decision import DuplicateChargeDecisionInput, DuplicateChargeDecisionTool
from meterdesk_api.agent.provider import (
    AgentDraftOutput,
    AgentProviderError,
    AgentProviderInput,
    AgentResolutionProvider,
    validate_provider_output,
)
from meterdesk_api.repositories import MeterDeskRepository
from meterdesk_api.schemas import AgentRunSummary

PROMPT_VERSION = "m3-duplicate-charge-v1"


class AgentLoopError(Exception):
    status_code = 400


class UnsupportedScenarioError(AgentLoopError):
    status_code = 422


class PendingApprovalError(AgentLoopError):
    status_code = 409


class AgentRunOrchestrator:
    def __init__(
        self,
        repository: MeterDeskRepository,
        provider: AgentResolutionProvider,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._decision_tool = DuplicateChargeDecisionTool()

    async def run_duplicate_charge(self, ticket_id: str) -> AgentRunSummary | None:
        ticket = await self._repository.get_ticket(ticket_id)
        if ticket is None:
            return None
        if ticket.scenario != "duplicate_charge":
            raise UnsupportedScenarioError("M3 agent loop only supports Duplicate Charge tickets")

        pending_approval = await self._repository.get_pending_financial_approval(
            ticket_id=ticket_id,
            action_type="original_refund",
        )
        if pending_approval is not None:
            raise PendingApprovalError("Pending financial approval already exists for this ticket")

        evidence = await self._repository.get_billing_evidence(ticket_id)
        if evidence is None:
            return None

        run = await self._repository.create_agent_run(
            ticket_id=ticket_id,
            source="m3_governed_loop",
            model=self._provider.model,
            prompt_version=PROMPT_VERSION,
        )
        await self._repository.add_tool_trace(
            agent_run_id=run.id,
            category="read.billing_evidence",
            risk="Low",
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
        await self._repository.add_tool_trace(
            agent_run_id=run.id,
            category="read.prior_financial_actions",
            risk="Low",
            label="Checked prior approvals and mock mutations",
            input_summary=f"Read existing approval and mutation state for {ticket_id}.",
            output_summary=f"Found {len(executed_metadata)} executed mock financial action(s).",
            evidence_refs=[f"ticket {ticket_id}"],
            policy_refs=[],
            approval_refs=[],
        )

        decision = self._decision_tool.evaluate(
            DuplicateChargeDecisionInput(
                ticket_id=ticket_id,
                evidence=evidence,
                pending_approval_exists=False,
                executed_action_metadata=executed_metadata,
            )
        )
        await self._repository.add_tool_trace(
            agent_run_id=run.id,
            category="decision.refund_eligibility",
            risk="Medium",
            label="Evaluated duplicate-charge refund eligibility",
            input_summary="Compared captured charges, invoice total, policy, and prior actions.",
            output_summary=decision.reason,
            evidence_refs=decision.evidence_refs,
            policy_refs=decision.policy_refs,
            approval_refs=[],
        )

        provider_input = AgentProviderInput(
            ticket_id=ticket_id,
            account_name=evidence.account.name,
            invoice_id=evidence.invoice.id,
            charge_ids=[charge.id for charge in evidence.charges],
            policy_citation=evidence.policy.citation,
            decision_outcome=decision.outcome,
            decision_reason=decision.reason,
            action_type=decision.action_type,
            amount_display=decision.amount_display,
            target_charge_id=decision.target_charge_id,
        )
        provider_output, provider_error = await self._create_resolution_with_retry(provider_input)
        if provider_error is not None:
            await self._repository.add_tool_trace(
                agent_run_id=run.id,
                category="draft.resolution",
                risk="Low",
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
        await self._repository.add_tool_trace(
            agent_run_id=run.id,
            category="draft.resolution",
            risk="Low",
            label="Drafted governed resolution",
            input_summary="Requested strict structured recommendation and drafts from provider.",
            output_summary="Provider returned validated draft-only resolution output.",
            evidence_refs=decision.evidence_refs,
            policy_refs=decision.policy_refs,
            approval_refs=[],
        )

        if decision.requires_approval:
            approval = await self._repository.create_approval_request(
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
                action_metadata=decision.action_metadata,
            )
            await self._repository.add_tool_trace(
                agent_run_id=run.id,
                category="approval.create_request",
                risk="Medium",
                label="Created approval request for financial action",
                input_summary="Created human approval gate for proposed original refund.",
                output_summary=f"Approval request {approval.id} is pending.",
                evidence_refs=decision.evidence_refs,
                policy_refs=decision.policy_refs,
                approval_refs=[approval.id],
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
