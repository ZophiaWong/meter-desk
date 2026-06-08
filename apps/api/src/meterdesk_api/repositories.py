from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meterdesk_api.db import get_session
from meterdesk_api.schemas import (
    AgentRunSummary,
    ApprovalSummary,
    BillingEvidence,
    EvalCaseSummary,
    EvalResultSummary,
    MockMutationSummary,
    TicketDetail,
    TicketSummary,
    ToolTraceSummary,
)

SESSION_DEPENDENCY = Depends(get_session)


class MeterDeskRepository(Protocol):
    async def list_tickets(self) -> list[TicketSummary]: ...

    async def get_ticket(self, ticket_id: str) -> TicketDetail | None: ...

    async def get_billing_evidence(self, ticket_id: str) -> BillingEvidence | None: ...

    async def list_agent_runs(self, ticket_id: str) -> list[AgentRunSummary] | None: ...

    async def list_traces(self, agent_run_id: str) -> list[ToolTraceSummary] | None: ...

    async def list_approvals(self, status: str | None = None) -> list[ApprovalSummary]: ...

    async def list_mock_mutations(self) -> list[MockMutationSummary]: ...

    async def list_eval_cases(self) -> list[EvalCaseSummary]: ...

    async def list_eval_results(self) -> list[EvalResultSummary]: ...


class InMemoryMeterDeskRepository:
    def __init__(
        self,
        *,
        tickets: Sequence[TicketSummary],
        ticket_details: dict[str, TicketDetail],
        billing_evidence: dict[str, BillingEvidence],
        agent_runs: dict[str, Sequence[AgentRunSummary]],
        traces: dict[str, Sequence[ToolTraceSummary]],
        approvals: Sequence[ApprovalSummary],
        mock_mutations: Sequence[MockMutationSummary],
        eval_cases: Sequence[EvalCaseSummary],
        eval_results: Sequence[EvalResultSummary],
    ) -> None:
        self._tickets = list(tickets)
        self._ticket_details = ticket_details
        self._billing_evidence = billing_evidence
        self._agent_runs = {key: list(value) for key, value in agent_runs.items()}
        self._traces = {key: list(value) for key, value in traces.items()}
        self._approvals = list(approvals)
        self._mock_mutations = list(mock_mutations)
        self._eval_cases = list(eval_cases)
        self._eval_results = list(eval_results)

    async def list_tickets(self) -> list[TicketSummary]:
        return self._tickets

    async def get_ticket(self, ticket_id: str) -> TicketDetail | None:
        return self._ticket_details.get(ticket_id)

    async def get_billing_evidence(self, ticket_id: str) -> BillingEvidence | None:
        return self._billing_evidence.get(ticket_id)

    async def list_agent_runs(self, ticket_id: str) -> list[AgentRunSummary] | None:
        if ticket_id not in self._ticket_details:
            return None
        return self._agent_runs.get(ticket_id, [])

    async def list_traces(self, agent_run_id: str) -> list[ToolTraceSummary] | None:
        if agent_run_id not in self._traces:
            return None
        return self._traces[agent_run_id]

    async def list_approvals(self, status: str | None = None) -> list[ApprovalSummary]:
        if status is None:
            return self._approvals
        return [approval for approval in self._approvals if approval.status == status]

    async def list_mock_mutations(self) -> list[MockMutationSummary]:
        return self._mock_mutations

    async def list_eval_cases(self) -> list[EvalCaseSummary]:
        return self._eval_cases

    async def list_eval_results(self) -> list[EvalResultSummary]:
        return self._eval_results


class SqlAlchemyMeterDeskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_tickets(self) -> list[TicketSummary]:
        from meterdesk_api.models import CustomerAccount, Ticket

        result = await self._session.execute(
            select(Ticket, CustomerAccount)
            .join(CustomerAccount, Ticket.customer_account_id == CustomerAccount.id)
            .order_by(Ticket.sort_order)
        )
        return [
            TicketSummary(
                id=ticket.id,
                title=ticket.title,
                customer=account.name,
                status=ticket.status,
                summary=ticket.summary,
                scenario=ticket.scenario,
                is_active=ticket.is_active,
            )
            for ticket, account in result.all()
        ]

    async def get_ticket(self, ticket_id: str) -> TicketDetail | None:
        from meterdesk_api.models import CustomerAccount, Ticket

        result = await self._session.execute(
            select(Ticket, CustomerAccount)
            .join(CustomerAccount, Ticket.customer_account_id == CustomerAccount.id)
            .where(Ticket.id == ticket_id)
        )
        row = result.one_or_none()
        if row is None:
            return None
        ticket, account = row
        from meterdesk_api.schemas import CustomerSummary

        return TicketDetail(
            id=ticket.id,
            title=ticket.title,
            scenario=ticket.scenario,
            status=ticket.status,
            severity=ticket.severity,
            opened_at=ticket.opened_at,
            opened_at_display=ticket.opened_at_display,
            summary=ticket.summary,
            outcome=ticket.outcome,
            customer=CustomerSummary(
                id=account.id,
                name=account.name,
                plan=account.plan,
                owner=account.owner_email,
                status=account.status,
            ),
        )

    async def get_billing_evidence(self, ticket_id: str) -> BillingEvidence | None:
        from meterdesk_api.models import (
            Charge,
            CreditLedgerEntry,
            CustomerAccount,
            Invoice,
            PolicyRule,
            Ticket,
            TicketPolicyLink,
            UsageRecord,
        )
        from meterdesk_api.schemas import (
            ChargeEvidence,
            CreditEvidence,
            CustomerSummary,
            InvoiceEvidence,
            MoneyAmount,
            PolicyEvidence,
            UsageEvidence,
        )

        ticket_result = await self._session.execute(
            select(Ticket, CustomerAccount)
            .join(CustomerAccount, Ticket.customer_account_id == CustomerAccount.id)
            .where(Ticket.id == ticket_id)
        )
        ticket_row = ticket_result.one_or_none()
        if ticket_row is None:
            return None
        ticket, account = ticket_row

        invoice = (
            await self._session.execute(
                select(Invoice).where(Invoice.ticket_id == ticket.id).order_by(Invoice.id).limit(1)
            )
        ).scalar_one()
        charges = (
            await self._session.execute(
                select(Charge).where(Charge.invoice_id == invoice.id).order_by(Charge.captured_at)
            )
        ).scalars()
        credits = (
            await self._session.execute(
                select(CreditLedgerEntry)
                .where(CreditLedgerEntry.ticket_id == ticket.id)
                .order_by(CreditLedgerEntry.id)
            )
        ).scalars()
        usage_records = (
            await self._session.execute(
                select(UsageRecord)
                .where(UsageRecord.ticket_id == ticket.id)
                .order_by(UsageRecord.id)
            )
        ).scalars()
        policy = (
            await self._session.execute(
                select(PolicyRule)
                .join(TicketPolicyLink, TicketPolicyLink.policy_rule_id == PolicyRule.id)
                .where(TicketPolicyLink.ticket_id == ticket.id)
                .limit(1)
            )
        ).scalar_one()

        return BillingEvidence(
            account=CustomerSummary(
                id=account.id,
                name=account.name,
                plan=account.plan,
                owner=account.owner_email,
                status=account.status,
            ),
            invoice=InvoiceEvidence(
                id=invoice.id,
                period_start=invoice.period_start,
                period_end=invoice.period_end,
                period_display=invoice.period_display,
                total=MoneyAmount(
                    amount_cents=invoice.total_amount_cents,
                    currency=invoice.currency,
                    display=invoice.total_display,
                ),
                status=invoice.status,
            ),
            charges=[
                ChargeEvidence(
                    id=charge.id,
                    status=charge.status,
                    amount=MoneyAmount(
                        amount_cents=charge.amount_cents,
                        currency=charge.currency,
                        display=charge.amount_display,
                    ),
                    captured_at=charge.captured_at,
                    captured_at_display=charge.captured_at_display,
                    processor_state=charge.processor_state,
                )
                for charge in charges
            ],
            credits=[
                CreditEvidence(
                    id=credit.id,
                    label=credit.label,
                    detail=credit.detail,
                    amount=(
                        MoneyAmount(
                            amount_cents=credit.amount_cents,
                            currency=credit.currency,
                            display=credit.amount_display,
                        )
                        if credit.amount_cents is not None
                        else None
                    ),
                )
                for credit in credits
            ],
            usage=[
                UsageEvidence(
                    id=usage.id,
                    label=usage.label,
                    detail=usage.detail,
                    period_start=usage.period_start,
                    period_end=usage.period_end,
                )
                for usage in usage_records
            ],
            policy=PolicyEvidence(
                id=policy.id,
                version=policy.version,
                citation=policy.citation,
                title=policy.title,
                reason=policy.reason,
            ),
        )

    async def list_agent_runs(self, ticket_id: str) -> list[AgentRunSummary] | None:
        from meterdesk_api.models import AgentRun, Ticket

        ticket = await self._session.get(Ticket, ticket_id)
        if ticket is None:
            return None
        runs = (
            await self._session.execute(
                select(AgentRun)
                .where(AgentRun.ticket_id == ticket_id)
                .order_by(AgentRun.started_at)
            )
        ).scalars()
        return [
            AgentRunSummary(
                id=run.id,
                ticket_id=run.ticket_id,
                status=run.status,
                source=run.source,
                final_outcome=run.final_outcome,
                internal_resolution=run.internal_resolution,
                customer_reply=run.customer_reply,
                model=run.model,
                prompt_version=run.prompt_version,
            )
            for run in runs
        ]

    async def list_traces(self, agent_run_id: str) -> list[ToolTraceSummary] | None:
        from meterdesk_api.models import AgentRun, ToolTrace

        run = await self._session.get(AgentRun, agent_run_id)
        if run is None:
            return None
        traces = (
            await self._session.execute(
                select(ToolTrace)
                .where(ToolTrace.agent_run_id == agent_run_id)
                .order_by(ToolTrace.sequence)
            )
        ).scalars()
        return [
            ToolTraceSummary(
                id=trace.id,
                agent_run_id=trace.agent_run_id,
                sequence=trace.sequence,
                category=trace.category,
                risk=trace.risk,
                label=trace.label,
                input_summary=trace.input_summary,
                output_summary=trace.output_summary,
                evidence_refs=trace.evidence_refs,
                policy_refs=trace.policy_refs,
                approval_refs=trace.approval_refs,
                error_state=trace.error_state,
            )
            for trace in traces
        ]

    async def list_approvals(self, status: str | None = None) -> list[ApprovalSummary]:
        from meterdesk_api.models import ApprovalRequest
        from meterdesk_api.schemas import MoneyAmount

        statement = select(ApprovalRequest).order_by(ApprovalRequest.created_at)
        if status is not None:
            statement = statement.where(ApprovalRequest.status == status)
        approvals = (await self._session.execute(statement)).scalars()
        return [
            ApprovalSummary(
                id=approval.id,
                ticket_id=approval.ticket_id,
                title=approval.title,
                status=approval.status,
                amount=MoneyAmount(
                    amount_cents=approval.amount_cents,
                    currency=approval.currency,
                    display=approval.amount_display,
                ),
                reason=approval.reason,
                policy_citation=approval.policy_citation,
                blocker=approval.blocker,
            )
            for approval in approvals
        ]

    async def list_mock_mutations(self) -> list[MockMutationSummary]:
        from meterdesk_api.models import MockMutation
        from meterdesk_api.schemas import MoneyAmount

        mutations = (
            await self._session.execute(select(MockMutation).order_by(MockMutation.executed_at))
        ).scalars()
        return [
            MockMutationSummary(
                id=mutation.id,
                ticket_id=mutation.ticket_id,
                approval_request_id=mutation.approval_request_id,
                agent_run_id=mutation.agent_run_id,
                mutation_type=mutation.mutation_type,
                status=mutation.status,
                amount=MoneyAmount(
                    amount_cents=mutation.amount_cents,
                    currency=mutation.currency,
                    display=mutation.amount_display,
                ),
                reason=mutation.reason,
                executed_at=mutation.executed_at,
                executed_at_display=mutation.executed_at_display,
            )
            for mutation in mutations
        ]

    async def list_eval_cases(self) -> list[EvalCaseSummary]:
        from meterdesk_api.models import EvalCase

        cases = (await self._session.execute(select(EvalCase).order_by(EvalCase.id))).scalars()
        return [
            EvalCaseSummary(
                id=case.id,
                scenario=case.scenario,
                title=case.title,
                description=case.description,
                expected_outcome=case.expected_outcome,
                required_evidence=case.required_evidence,
                policy_refs=case.policy_refs,
                expected_approval_routing=case.expected_approval_routing,
            )
            for case in cases
        ]

    async def list_eval_results(self) -> list[EvalResultSummary]:
        from meterdesk_api.models import EvalResult

        results = (
            await self._session.execute(select(EvalResult).order_by(EvalResult.id))
        ).scalars()
        return [
            EvalResultSummary(
                id=result.id,
                case_id=result.case_id,
                agent_run_id=result.agent_run_id,
                status=result.status,
                summary=result.summary,
                dimension_scores=result.dimension_scores,
            )
            for result in results
        ]


async def get_repository(
    session: AsyncSession = SESSION_DEPENDENCY,
) -> AsyncIterator[MeterDeskRepository]:
    yield SqlAlchemyMeterDeskRepository(session)
