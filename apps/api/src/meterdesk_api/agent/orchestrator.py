from __future__ import annotations

from meterdesk_api.agent.decision import (
    CreditRefundDecisionInput,
    CreditRefundDecisionTool,
    DuplicateChargeDecisionInput,
    DuplicateChargeDecisionTool,
)
from meterdesk_api.agent.governance import (
    GovernanceKernel,
    build_governance_metadata_for_trace,
)
from meterdesk_api.agent.planning import (
    InvestigationPlan,
    PlanContractVerifier,
    PlanVerifierFeedbackItem,
    VerifiedInvestigationPlan,
    build_planner_input,
)
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
PLAN_VERIFIER_BLOCKED_ERROR = "Plan verifier blocked investigation plan"


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
        self._plan_verifier = PlanContractVerifier()
        self.last_start_replayed = False

    async def run_ticket(
        self,
        ticket_id: str,
        *,
        idempotency_key: str = "internal",
        request_id: str = "system",
    ) -> AgentRunSummary | None:
        ticket = await self._repository.get_ticket(ticket_id)
        if ticket is None:
            return None
        if ticket.scenario == "duplicate_charge":
            return await self.run_duplicate_charge(
                ticket_id,
                idempotency_key=idempotency_key,
                request_id=request_id,
            )
        if ticket.scenario == "credit_refund_dispute":
            return await self.run_credit_refund(
                ticket_id,
                idempotency_key=idempotency_key,
                request_id=request_id,
            )
        raise UnsupportedScenarioError("Agent loop does not support this scenario yet.")

    async def run_duplicate_charge(
        self,
        ticket_id: str,
        *,
        idempotency_key: str = "internal",
        request_id: str = "system",
    ) -> AgentRunSummary | None:
        ticket = await self._repository.get_ticket(ticket_id)
        if ticket is None:
            return None
        if ticket.scenario != "duplicate_charge":
            raise UnsupportedScenarioError()

        start_result = await self._repository.start_or_replay_run(
            ticket_id=ticket_id,
            idempotency_key=idempotency_key,
            source="m3_governed_loop",
            model=self._provider.model,
            prompt_version=DUPLICATE_CHARGE_PROMPT_VERSION,
        )
        self.last_start_replayed = start_result.replayed
        if start_result.replayed:
            return start_result.run
        run = start_result.run
        verified_plan, planning_error = await self._create_verified_investigation_plan(
            ticket=ticket,
            agent_run_id=run.id,
        )
        if verified_plan is None:
            return await self._repository.fail_run(
                agent_run_id=run.id,
                error_code="plan.verifier_blocked",
                error_state=planning_error or PLAN_VERIFIER_BLOCKED_ERROR,
                recoverable=True,
                request_id=request_id,
            )

        evidence = await self._repository.get_billing_evidence(ticket_id)
        if evidence is None:
            return await self._repository.fail_run(
                agent_run_id=run.id,
                error_code="evidence.missing",
                error_state="Billing evidence was not found.",
                recoverable=True,
                request_id=request_id,
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
            return await self._repository.fail_run(
                agent_run_id=run.id,
                error_code="provider.draft_failed",
                error_state=provider_error,
                recoverable=True,
                request_id=request_id,
            )

        assert provider_output is not None
        return await self._finalize_investigation(
            run=run,
            decision=decision,
            provider_output=provider_output,
            evidence=evidence,
            ticket_id=ticket_id,
            request_id=request_id,
            approval_title="Original refund pending approval",
            approval_input_summary="Created human approval gate for proposed original refund.",
        )

    async def run_credit_refund(
        self,
        ticket_id: str,
        *,
        idempotency_key: str = "internal",
        request_id: str = "system",
    ) -> AgentRunSummary | None:
        ticket = await self._repository.get_ticket(ticket_id)
        if ticket is None:
            return None
        if ticket.scenario != "credit_refund_dispute":
            raise UnsupportedScenarioError(
                "Credit/Refund runner only supports Credit/Refund tickets."
            )

        start_result = await self._repository.start_or_replay_run(
            ticket_id=ticket_id,
            idempotency_key=idempotency_key,
            source="m8_credit_refund_loop",
            model=self._provider.model,
            prompt_version=CREDIT_REFUND_PROMPT_VERSION,
        )
        self.last_start_replayed = start_result.replayed
        if start_result.replayed:
            return start_result.run
        run = start_result.run
        verified_plan, planning_error = await self._create_verified_investigation_plan(
            ticket=ticket,
            agent_run_id=run.id,
        )
        if verified_plan is None:
            return await self._repository.fail_run(
                agent_run_id=run.id,
                error_code="plan.verifier_blocked",
                error_state=planning_error or PLAN_VERIFIER_BLOCKED_ERROR,
                recoverable=True,
                request_id=request_id,
            )

        evidence = await self._repository.get_billing_evidence(ticket_id)
        if evidence is None:
            return await self._repository.fail_run(
                agent_run_id=run.id,
                error_code="evidence.missing",
                error_state="Billing evidence was not found.",
                recoverable=True,
                request_id=request_id,
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
            return await self._repository.fail_run(
                agent_run_id=run.id,
                error_code="provider.draft_failed",
                error_state=provider_error,
                recoverable=True,
                request_id=request_id,
            )

        return await self._finalize_investigation(
            run=run,
            decision=decision,
            provider_output=provider_output,
            evidence=evidence,
            ticket_id=ticket_id,
            request_id=request_id,
            approval_title=(
                "Goodwill credit pending approval"
                if decision.action_type == "goodwill_credit"
                else "Original refund pending approval"
            ),
            approval_input_summary="Created human approval gate for proposed credit/refund action.",
        )

    async def _finalize_investigation(
        self,
        *,
        run: AgentRunSummary,
        decision,
        provider_output: AgentDraftOutput,
        evidence,
        ticket_id: str,
        request_id: str,
        approval_title: str,
        approval_input_summary: str,
    ) -> AgentRunSummary:
        """Commit final draft trace, approval (when needed), and workflow state once."""
        draft_policy_id = "draft.resolution"
        draft_metadata = build_governance_metadata_for_trace(
            policy_id=draft_policy_id,
            evidence_refs=decision.evidence_refs,
            policy_refs=decision.policy_refs,
            approval_refs=[],
        )
        final_trace = {
            "category": draft_policy_id,
            "risk": "Low",
            "label": "Drafted governed resolution",
            "input_summary": "Requested strict structured recommendation and drafts from provider.",
            "output_summary": "Provider returned validated draft-only resolution output.",
            "evidence_refs": decision.evidence_refs,
            "policy_refs": decision.policy_refs,
            "approval_refs": [],
            "governance_metadata": draft_metadata,
        }
        approval_payload = None
        approval_trace = None
        target_status = "completed_no_action"
        reason_code = "decision.completed_no_action"
        reason_detail = decision.reason
        if decision.requires_approval:
            target_status = "awaiting_approval"
            reason_code = "decision.approval_required"
            reason_detail = decision.reason
            approval_payload = {
                "title": approval_title,
                "action_type": decision.action_type or "goodwill_credit",
                "amount_cents": decision.amount_cents or 0,
                "amount_display": decision.amount_display or "$0.00",
                "currency": decision.currency or evidence.invoice.total.currency,
                "reason": decision.reason,
                "blocker": "Mutation blocked until human approval",
                "policy_citation": decision.policy_refs[0],
                "evidence_refs": decision.evidence_refs,
                "action_metadata": decision.action_metadata,
            }
            approval_id = "pending"
            approval_metadata = build_governance_metadata_for_trace(
                policy_id="approval.create_request",
                evidence_refs=decision.evidence_refs,
                policy_refs=decision.policy_refs,
                approval_refs=[approval_id],
            )
            approval_trace = {
                "category": "approval.create_request",
                "risk": "Medium",
                "label": "Created approval request for financial action",
                "input_summary": approval_input_summary,
                "output_summary": "Approval request is pending.",
                "evidence_refs": decision.evidence_refs,
                "policy_refs": decision.policy_refs,
                "approval_refs": [approval_id],
                "governance_metadata": approval_metadata,
            }
        return await self._repository.finalize_run(
            agent_run_id=run.id,
            final_outcome=decision.outcome,
            internal_resolution=provider_output.internal_resolution,
            customer_reply=provider_output.customer_reply,
            target_status=target_status,
            reason_code=reason_code,
            reason_detail=reason_detail,
            request_id=request_id,
            final_trace=final_trace,
            approval=approval_payload,
            approval_trace=approval_trace,
        )

    async def _create_verified_investigation_plan(
        self,
        *,
        ticket,
        agent_run_id: str,
    ) -> tuple[VerifiedInvestigationPlan | None, str | None]:
        planner_input = build_planner_input(ticket)
        verifier_feedback: list[PlanVerifierFeedbackItem] = []
        blocked_attempt_reason_codes: list[list[str]] = []
        blocked_attempt_feedback: list[list[dict[str, object]]] = []
        last_plan: InvestigationPlan | None = None
        last_result: VerifiedInvestigationPlan | None = None

        for attempt_index in range(2):
            try:
                plan = await self._provider.create_investigation_plan(
                    planner_input,
                    verifier_feedback=verifier_feedback,
                )
            except AgentProviderError as error:
                return None, f"Provider failed to create investigation plan: {error}"

            result = self._plan_verifier.verify(ticket, plan)
            last_plan = plan
            last_result = result
            if result.status == "accepted":
                await self._record_plan_traces(
                    agent_run_id=agent_run_id,
                    ticket_id=ticket.id,
                    plan=plan,
                    result=result,
                    attempt_count=attempt_index + 1,
                    blocked_attempt_reason_codes=blocked_attempt_reason_codes,
                    blocked_attempt_feedback=blocked_attempt_feedback,
                )
                return result, None

            blocked_attempt_reason_codes.append(result.reason_codes)
            blocked_attempt_feedback.append(
                [item.model_dump(exclude_none=True) for item in result.feedback_items]
            )
            verifier_feedback = result.feedback_items

        assert last_plan is not None
        assert last_result is not None
        await self._record_plan_traces(
            agent_run_id=agent_run_id,
            ticket_id=ticket.id,
            plan=last_plan,
            result=last_result,
            attempt_count=2,
            blocked_attempt_reason_codes=blocked_attempt_reason_codes,
            blocked_attempt_feedback=blocked_attempt_feedback,
        )
        return None, PLAN_VERIFIER_BLOCKED_ERROR

    async def _record_plan_traces(
        self,
        *,
        agent_run_id: str,
        ticket_id: str,
        plan: InvestigationPlan,
        result: VerifiedInvestigationPlan,
        attempt_count: int,
        blocked_attempt_reason_codes: list[list[str]],
        blocked_attempt_feedback: list[list[dict[str, object]]],
    ) -> None:
        plan_metadata = {
            "planning": {
                "status": "proposed",
                "attempt_count": attempt_count,
                "plan_summary": plan.plan_summary,
                "steps": [step.model_dump() for step in plan.steps],
                "evidence_gaps": plan.evidence_gaps,
                "stop_conditions": plan.stop_conditions,
                "blocked_attempt_reason_codes": blocked_attempt_reason_codes,
                "blocked_attempt_feedback": blocked_attempt_feedback,
            }
        }
        await self._governance.record_action(
            agent_run_id=agent_run_id,
            policy_id="plan.investigation",
            label="LLM proposed investigation tool plan",
            input_summary=(
                f"Requested investigation plan for {ticket_id} before reading billing evidence."
            ),
            output_summary=plan.plan_summary,
            evidence_refs=[f"ticket {ticket_id}"],
            policy_refs=[],
            approval_refs=[],
            governance_metadata_extra=plan_metadata,
        )

        verify_error_state = result.reason_codes[0] if result.status == "blocked" else None
        verify_metadata = {
            "planning": {
                "status": result.status,
                "attempt_count": attempt_count,
                "normalized_action_ids": result.normalized_action_ids,
                "required_targets_seen": result.required_targets_seen,
                "reason_codes": result.reason_codes,
                "blocked_attempt_reason_codes": blocked_attempt_reason_codes,
                "feedback_items": [
                    item.model_dump(exclude_none=True) for item in result.feedback_items
                ],
                "blocked_attempt_feedback": blocked_attempt_feedback,
            }
        }
        if verify_error_state is not None:
            verify_metadata["reason_code"] = verify_error_state

        await self._governance.record_action(
            agent_run_id=agent_run_id,
            policy_id="plan.verify",
            label="Backend verified investigation plan contract",
            input_summary=(
                "Checked planned actions, evidence targets, dependencies, and safety scope."
            ),
            output_summary=(
                "Plan verifier accepted the investigation plan."
                if result.status == "accepted"
                else "Plan verifier blocked the investigation plan."
            ),
            evidence_refs=[f"ticket {ticket_id}"],
            policy_refs=[],
            approval_refs=[],
            error_state=verify_error_state,
            governance_metadata_extra=verify_metadata,
        )

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
