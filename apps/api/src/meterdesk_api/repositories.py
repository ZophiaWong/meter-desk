from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from fastapi import Depends
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from meterdesk_api.db import get_session
from meterdesk_api.errors import MeterDeskAPIError
from meterdesk_api.financial_actions import build_action_fingerprint
from meterdesk_api.schemas import (
    AgentRunSummary,
    ApprovalSummary,
    BillingEvidence,
    EvalCaseSummary,
    EvalResultSnapshotSummary,
    EvalResultSummary,
    EvalRunSummary,
    MockMutationSummary,
    MoneyAmount,
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

    async def get_agent_run(self, agent_run_id: str) -> AgentRunSummary | None: ...

    async def list_traces(self, agent_run_id: str) -> list[ToolTraceSummary] | None: ...

    async def list_approvals(
        self,
        status: str | None = None,
        ticket_id: str | None = None,
    ) -> list[ApprovalSummary]: ...

    async def list_mock_mutations(
        self,
        ticket_id: str | None = None,
    ) -> list[MockMutationSummary]: ...

    async def list_eval_cases(self) -> list[EvalCaseSummary]: ...

    async def list_eval_results(self) -> list[EvalResultSummary]: ...

    async def get_eval_case(self, case_id: str) -> EvalCaseSummary | None: ...

    async def replace_eval_result(self, result: EvalResultSummary) -> EvalResultSummary: ...

    async def create_eval_run(
        self,
        *,
        run_type: str,
        status: str,
        summary: str,
        baseline_name: str | None = None,
        case_id: str | None = None,
    ) -> EvalRunSummary: ...

    async def complete_eval_run(
        self,
        *,
        eval_run_id: str,
        status: str,
        summary: str,
    ) -> EvalRunSummary: ...

    async def list_eval_runs(self) -> list[EvalRunSummary]: ...

    async def get_eval_run(self, eval_run_id: str) -> EvalRunSummary | None: ...

    async def get_latest_eval_run(self) -> EvalRunSummary | None: ...

    async def add_eval_result_snapshot(
        self,
        snapshot: EvalResultSnapshotSummary,
    ) -> EvalResultSnapshotSummary: ...

    async def list_eval_result_snapshots(
        self,
        *,
        eval_run_id: str | None = None,
        case_id: str | None = None,
        snapshot_type: str | None = None,
    ) -> list[EvalResultSnapshotSummary]: ...

    async def reset_eval_fixture_state(self, fixture_ticket_id: str) -> None: ...

    async def reset_demo_live_state(self, ticket_id: str) -> None: ...

    async def get_pending_financial_approval(
        self,
        ticket_id: str,
        action_type: str,
    ) -> ApprovalSummary | None: ...

    async def get_pending_approval_by_fingerprint(
        self,
        action_fingerprint: str,
    ) -> ApprovalSummary | None: ...

    async def get_executed_mock_mutation_by_fingerprint(
        self,
        action_fingerprint: str,
    ) -> MockMutationSummary | None: ...

    async def list_executed_action_metadata(self, ticket_id: str) -> list[dict[str, object]]: ...

    async def create_agent_run(
        self,
        *,
        ticket_id: str,
        source: str,
        model: str,
        prompt_version: str,
    ) -> AgentRunSummary: ...

    async def complete_agent_run(
        self,
        *,
        agent_run_id: str,
        final_outcome: str,
        internal_resolution: str,
        customer_reply: str,
    ) -> AgentRunSummary: ...

    async def fail_agent_run(self, agent_run_id: str, error_state: str) -> AgentRunSummary: ...

    async def add_tool_trace(
        self,
        *,
        agent_run_id: str,
        category: str,
        risk: str,
        label: str,
        input_summary: str,
        output_summary: str,
        evidence_refs: list[str],
        policy_refs: list[str],
        approval_refs: list[str],
        error_state: str | None = None,
        governance_metadata: dict[str, object] | None = None,
    ) -> ToolTraceSummary: ...

    async def create_approval_request(
        self,
        *,
        ticket_id: str,
        agent_run_id: str,
        title: str,
        action_type: str,
        amount_cents: int,
        amount_display: str,
        currency: str,
        reason: str,
        blocker: str,
        policy_citation: str,
        evidence_refs: list[str],
        action_metadata: dict[str, object],
        action_fingerprint: str | None = None,
    ) -> ApprovalSummary: ...

    async def get_approval(self, approval_id: str) -> ApprovalSummary | None: ...

    async def get_mock_mutation_by_approval(
        self,
        approval_id: str,
    ) -> MockMutationSummary | None: ...

    async def approve_request(
        self,
        *,
        approval_id: str,
        decided_by: str,
        decision_note: str | None,
    ) -> tuple[ApprovalSummary, MockMutationSummary]: ...

    async def reject_request(
        self,
        *,
        approval_id: str,
        decided_by: str,
        decision_note: str | None,
    ) -> ApprovalSummary: ...


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
        eval_runs: Sequence[EvalRunSummary] = (),
        eval_result_snapshots: Sequence[EvalResultSnapshotSummary] = (),
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
        self._eval_runs = list(eval_runs)
        self._eval_result_snapshots = list(eval_result_snapshots)

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

    async def get_agent_run(self, agent_run_id: str) -> AgentRunSummary | None:
        for runs in self._agent_runs.values():
            for run in runs:
                if run.id == agent_run_id:
                    return run
        return None

    async def list_traces(self, agent_run_id: str) -> list[ToolTraceSummary] | None:
        if agent_run_id not in self._traces:
            return None
        return self._traces[agent_run_id]

    async def list_approvals(
        self,
        status: str | None = None,
        ticket_id: str | None = None,
    ) -> list[ApprovalSummary]:
        approvals = self._approvals
        if status is not None:
            approvals = [approval for approval in approvals if approval.status == status]
        if ticket_id is not None:
            approvals = [approval for approval in approvals if approval.ticket_id == ticket_id]
        return approvals

    async def list_mock_mutations(self, ticket_id: str | None = None) -> list[MockMutationSummary]:
        if ticket_id is None:
            return self._mock_mutations
        return [mutation for mutation in self._mock_mutations if mutation.ticket_id == ticket_id]

    async def list_eval_cases(self) -> list[EvalCaseSummary]:
        return self._eval_cases

    async def list_eval_results(self) -> list[EvalResultSummary]:
        return self._eval_results

    async def get_eval_case(self, case_id: str) -> EvalCaseSummary | None:
        return next((case for case in self._eval_cases if case.id == case_id), None)

    async def replace_eval_result(self, result: EvalResultSummary) -> EvalResultSummary:
        self._eval_results = [
            existing for existing in self._eval_results if existing.case_id != result.case_id
        ]
        self._eval_results.append(result)
        return result

    async def create_eval_run(
        self,
        *,
        run_type: str,
        status: str,
        summary: str,
        baseline_name: str | None = None,
        case_id: str | None = None,
    ) -> EvalRunSummary:
        run = EvalRunSummary(
            id=_new_id("eval-run"),
            run_type=run_type,
            status=status,
            summary=summary,
            baseline_name=baseline_name,
            case_id=case_id,
            started_at=_now(),
            completed_at=None,
        )
        self._eval_runs.append(run)
        return run

    async def complete_eval_run(
        self,
        *,
        eval_run_id: str,
        status: str,
        summary: str,
    ) -> EvalRunSummary:
        run = await self.get_eval_run(eval_run_id)
        if run is None:
            raise KeyError(eval_run_id)
        replacement = run.model_copy(
            update={"status": status, "summary": summary, "completed_at": _now()}
        )
        self._eval_runs = [
            replacement if existing.id == eval_run_id else existing for existing in self._eval_runs
        ]
        return replacement

    async def list_eval_runs(self) -> list[EvalRunSummary]:
        return sorted(self._eval_runs, key=lambda run: run.started_at, reverse=True)

    async def get_eval_run(self, eval_run_id: str) -> EvalRunSummary | None:
        return next((run for run in self._eval_runs if run.id == eval_run_id), None)

    async def get_latest_eval_run(self) -> EvalRunSummary | None:
        runs = [
            run
            for run in self._eval_runs
            if run.run_type != "baseline" and run.status != "running"
        ]
        return max(runs, key=lambda run: run.started_at, default=None)

    async def add_eval_result_snapshot(
        self,
        snapshot: EvalResultSnapshotSummary,
    ) -> EvalResultSnapshotSummary:
        self._eval_result_snapshots.append(snapshot)
        return snapshot

    async def list_eval_result_snapshots(
        self,
        *,
        eval_run_id: str | None = None,
        case_id: str | None = None,
        snapshot_type: str | None = None,
    ) -> list[EvalResultSnapshotSummary]:
        snapshots = self._eval_result_snapshots
        if eval_run_id is not None:
            snapshots = [snapshot for snapshot in snapshots if snapshot.eval_run_id == eval_run_id]
        if case_id is not None:
            snapshots = [snapshot for snapshot in snapshots if snapshot.case_id == case_id]
        if snapshot_type is not None:
            snapshots = [
                snapshot for snapshot in snapshots if snapshot.snapshot_type == snapshot_type
            ]
        return sorted(snapshots, key=lambda snapshot: snapshot.created_at)

    async def reset_eval_fixture_state(self, fixture_ticket_id: str) -> None:
        runs = self._agent_runs.pop(fixture_ticket_id, [])
        run_ids = {run.id for run in runs}
        self._eval_results = [
            result for result in self._eval_results if result.agent_run_id not in run_ids
        ]
        for run_id in run_ids:
            self._traces.pop(run_id, None)
        removed_approval_ids = {
            approval.id
            for approval in self._approvals
            if approval.ticket_id == fixture_ticket_id and approval.agent_run_id in run_ids
        }
        self._approvals = [
            approval
            for approval in self._approvals
            if not (approval.ticket_id == fixture_ticket_id and approval.agent_run_id in run_ids)
        ]
        self._mock_mutations = [
            mutation
            for mutation in self._mock_mutations
            if not (
                mutation.ticket_id == fixture_ticket_id
                and (
                    mutation.agent_run_id in run_ids
                    or mutation.approval_request_id in removed_approval_ids
                )
            )
        ]

    async def reset_demo_live_state(self, ticket_id: str) -> None:
        runs = self._agent_runs.pop(ticket_id, [])
        run_ids = {run.id for run in runs}
        for run_id in run_ids:
            self._traces.pop(run_id, None)
        self._approvals = [
            approval for approval in self._approvals if approval.ticket_id != ticket_id
        ]
        self._mock_mutations = [
            mutation for mutation in self._mock_mutations if mutation.ticket_id != ticket_id
        ]

    async def get_pending_financial_approval(
        self,
        ticket_id: str,
        action_type: str,
    ) -> ApprovalSummary | None:
        for approval in self._approvals:
            if (
                approval.ticket_id == ticket_id
                and approval.action_type == action_type
                and approval.status == "pending"
            ):
                return approval
        return None

    async def get_pending_approval_by_fingerprint(
        self,
        action_fingerprint: str,
    ) -> ApprovalSummary | None:
        for approval in self._approvals:
            if approval.action_fingerprint == action_fingerprint and approval.status == "pending":
                return approval
        return None

    async def get_executed_mock_mutation_by_fingerprint(
        self,
        action_fingerprint: str,
    ) -> MockMutationSummary | None:
        for mutation in self._mock_mutations:
            if (
                mutation.action_fingerprint == action_fingerprint
                and mutation.status == "mock_executed"
            ):
                return mutation
        return None

    async def list_executed_action_metadata(self, ticket_id: str) -> list[dict[str, object]]:
        return [
            {**mutation.action_metadata, "action_fingerprint": mutation.action_fingerprint}
            for mutation in self._mock_mutations
            if mutation.ticket_id == ticket_id and mutation.status == "mock_executed"
        ]

    async def create_agent_run(
        self,
        *,
        ticket_id: str,
        source: str,
        model: str,
        prompt_version: str,
    ) -> AgentRunSummary:
        run = AgentRunSummary(
            id=_new_id("RUN"),
            ticket_id=ticket_id,
            status="running",
            source=source,
            model=model,
            prompt_version=prompt_version,
        )
        self._agent_runs.setdefault(ticket_id, []).append(run)
        self._traces[run.id] = []
        return run

    async def complete_agent_run(
        self,
        *,
        agent_run_id: str,
        final_outcome: str,
        internal_resolution: str,
        customer_reply: str,
    ) -> AgentRunSummary:
        run = self._find_run(agent_run_id)
        completed = run.model_copy(
            update={
                "status": "completed",
                "final_outcome": final_outcome,
                "internal_resolution": internal_resolution,
                "customer_reply": customer_reply,
                "error_state": None,
            }
        )
        self._replace_run(completed)
        return completed

    async def fail_agent_run(self, agent_run_id: str, error_state: str) -> AgentRunSummary:
        run = self._find_run(agent_run_id)
        failed = run.model_copy(update={"status": "failed", "error_state": error_state})
        self._replace_run(failed)
        return failed

    async def add_tool_trace(
        self,
        *,
        agent_run_id: str,
        category: str,
        risk: str,
        label: str,
        input_summary: str,
        output_summary: str,
        evidence_refs: list[str],
        policy_refs: list[str],
        approval_refs: list[str],
        error_state: str | None = None,
        governance_metadata: dict[str, object] | None = None,
    ) -> ToolTraceSummary:
        traces = self._traces.setdefault(agent_run_id, [])
        trace = ToolTraceSummary(
            id=_new_id("trace"),
            agent_run_id=agent_run_id,
            sequence=len(traces) + 1,
            category=category,
            risk=risk,
            label=label,
            input_summary=input_summary,
            output_summary=output_summary,
            evidence_refs=evidence_refs,
            policy_refs=policy_refs,
            approval_refs=approval_refs,
            error_state=error_state,
            governance_metadata=governance_metadata or {},
        )
        traces.append(trace)
        return trace

    async def create_approval_request(
        self,
        *,
        ticket_id: str,
        agent_run_id: str,
        title: str,
        action_type: str,
        amount_cents: int,
        amount_display: str,
        currency: str,
        reason: str,
        blocker: str,
        policy_citation: str,
        evidence_refs: list[str],
        action_metadata: dict[str, object],
        action_fingerprint: str | None = None,
    ) -> ApprovalSummary:
        fingerprint = action_fingerprint or build_action_fingerprint(
            ticket_id=ticket_id,
            action_type=action_type,
            amount_cents=amount_cents,
            currency=currency,
            action_metadata=action_metadata,
        )
        duplicate = await self.get_pending_approval_by_fingerprint(fingerprint)
        if duplicate is not None:
            raise MeterDeskAPIError(
                status_code=409,
                code="approval.pending_duplicate",
                message="A pending financial approval already exists for this action.",
                details={"action_fingerprint": fingerprint},
            )
        approval = ApprovalSummary(
            id=_new_id("APR"),
            ticket_id=ticket_id,
            agent_run_id=agent_run_id,
            title=title,
            status="pending",
            action_type=action_type,
            amount=MoneyAmount(
                amount_cents=amount_cents,
                currency=currency,
                display=amount_display,
            ),
            reason=reason,
            policy_citation=policy_citation,
            blocker=blocker,
            evidence_refs=evidence_refs,
            action_metadata=action_metadata,
            action_fingerprint=fingerprint,
        )
        self._approvals.append(approval)
        return approval

    async def get_approval(self, approval_id: str) -> ApprovalSummary | None:
        return next((approval for approval in self._approvals if approval.id == approval_id), None)

    async def get_mock_mutation_by_approval(
        self,
        approval_id: str,
    ) -> MockMutationSummary | None:
        return next(
            (
                mutation
                for mutation in self._mock_mutations
                if mutation.approval_request_id == approval_id
            ),
            None,
        )

    async def approve_request(
        self,
        *,
        approval_id: str,
        decided_by: str,
        decision_note: str | None,
    ) -> tuple[ApprovalSummary, MockMutationSummary]:
        current = await self.get_approval(approval_id)
        existing = await self.get_mock_mutation_by_approval(approval_id)
        if existing is not None:
            approval = current.model_copy(
                update={
                    "status": "approved",
                    "decision": "approved",
                    "decided_at": _now(),
                    "decided_by": decided_by,
                    "decision_note": decision_note,
                    "blocker": "Approved; mock mutation executed",
                }
            )
            self._replace_approval(approval)
            return approval, existing
        duplicate_action = await self.get_executed_mock_mutation_by_fingerprint(
            current.action_fingerprint
        )
        if duplicate_action is not None:
            raise MeterDeskAPIError(
                status_code=409,
                code="mutation.duplicate_action",
                message="This financial action has already been executed.",
                details={"action_fingerprint": current.action_fingerprint},
            )

        approval = current.model_copy(
            update={
                "status": "approved",
                "decision": "approved",
                "decided_at": _now(),
                "decided_by": decided_by,
                "decision_note": decision_note,
                "blocker": "Approved; mock mutation executed",
            }
        )
        self._replace_approval(approval)
        mutation = MockMutationSummary(
            id=_new_id("MM"),
            ticket_id=approval.ticket_id,
            approval_request_id=approval.id,
            agent_run_id=approval.agent_run_id,
            mutation_type=approval.action_type,
            status="mock_executed",
            amount=approval.amount,
            reason=approval.reason,
            action_metadata=approval.action_metadata,
            action_fingerprint=approval.action_fingerprint,
            executed_at=_now(),
            executed_at_display=_format_display_time(_now()),
        )
        self._mock_mutations.append(mutation)
        return approval, mutation

    async def reject_request(
        self,
        *,
        approval_id: str,
        decided_by: str,
        decision_note: str | None,
    ) -> ApprovalSummary:
        approval = (await self.get_approval(approval_id)).model_copy(
            update={
                "status": "rejected",
                "decision": "rejected",
                "decided_at": _now(),
                "decided_by": decided_by,
                "decision_note": decision_note,
                "blocker": "Rejected by human reviewer; no mock mutation executed",
            }
        )
        self._replace_approval(approval)
        return approval

    def _find_run(self, agent_run_id: str) -> AgentRunSummary:
        for runs in self._agent_runs.values():
            for run in runs:
                if run.id == agent_run_id:
                    return run
        raise KeyError(agent_run_id)

    def _replace_run(self, replacement: AgentRunSummary) -> None:
        runs = self._agent_runs[replacement.ticket_id]
        for index, run in enumerate(runs):
            if run.id == replacement.id:
                runs[index] = replacement
                return
        raise KeyError(replacement.id)

    def _replace_approval(self, replacement: ApprovalSummary) -> None:
        for index, approval in enumerate(self._approvals):
            if approval.id == replacement.id:
                self._approvals[index] = replacement
                return
        raise KeyError(replacement.id)


class SqlAlchemyMeterDeskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_tickets(self) -> list[TicketSummary]:
        from meterdesk_api.models import CustomerAccount, EvalCase, Ticket

        result = await self._session.execute(
            select(Ticket, CustomerAccount)
            .join(CustomerAccount, Ticket.customer_account_id == CustomerAccount.id)
            .where(
                ~Ticket.id.in_(
                    select(EvalCase.fixture_ticket_id).where(
                        EvalCase.fixture_ticket_id.is_not(None)
                    )
                )
            )
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
            SubscriptionEvidenceRecord,
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
            SubscriptionEvidence,
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
        policy_result = await self._session.execute(
            select(PolicyRule)
            .join(TicketPolicyLink, TicketPolicyLink.policy_rule_id == PolicyRule.id)
            .where(TicketPolicyLink.ticket_id == ticket.id)
            .order_by(PolicyRule.id)
        )
        policies = list(policy_result.scalars())
        policy = _primary_policy_for_scenario(ticket.scenario, policies)
        subscription = (
            await self._session.execute(
                select(SubscriptionEvidenceRecord)
                .where(SubscriptionEvidenceRecord.ticket_id == ticket.id)
                .order_by(SubscriptionEvidenceRecord.id)
                .limit(1)
            )
        ).scalar_one_or_none()

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
                    amount=_optional_money(
                        credit.amount_cents,
                        credit.currency,
                        credit.amount_display,
                    ),
                    granted_amount=_optional_money(
                        credit.granted_amount_cents,
                        credit.granted_currency,
                        credit.granted_amount_display,
                    ),
                    consumed_amount=_optional_money(
                        credit.consumed_amount_cents,
                        credit.consumed_currency,
                        credit.consumed_amount_display,
                    ),
                    remaining_amount=_optional_money(
                        credit.remaining_amount_cents,
                        credit.remaining_currency,
                        credit.remaining_amount_display,
                    ),
                    disputed_amount=_optional_money(
                        credit.disputed_amount_cents,
                        credit.disputed_currency,
                        credit.disputed_amount_display,
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
            policies=[
                PolicyEvidence(
                    id=policy_item.id,
                    version=policy_item.version,
                    citation=policy_item.citation,
                    title=policy_item.title,
                    reason=policy_item.reason,
                )
                for policy_item in policies
            ],
            subscription=(
                SubscriptionEvidence(
                    id=subscription.id,
                    label=subscription.label,
                    status=subscription.status,
                    trial_started_at_display=subscription.trial_started_at_display,
                    trial_ended_at_display=subscription.trial_ended_at_display,
                    canceled_at_display=subscription.canceled_at_display,
                    renewal_captured_at_display=subscription.renewal_captured_at_display,
                    canceled_before_renewal_capture=(subscription.canceled_before_renewal_capture),
                )
                if subscription is not None
                else None
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
                error_state=run.error_state,
                model=run.model,
                prompt_version=run.prompt_version,
            )
            for run in runs
        ]

    async def get_agent_run(self, agent_run_id: str) -> AgentRunSummary | None:
        from meterdesk_api.models import AgentRun

        run = await self._session.get(AgentRun, agent_run_id)
        return _run_to_summary(run) if run is not None else None

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
                governance_metadata=trace.governance_metadata,
            )
            for trace in traces
        ]

    async def list_approvals(
        self,
        status: str | None = None,
        ticket_id: str | None = None,
    ) -> list[ApprovalSummary]:
        from meterdesk_api.models import ApprovalRequest

        statement = select(ApprovalRequest).order_by(ApprovalRequest.created_at)
        if status is not None:
            statement = statement.where(ApprovalRequest.status == status)
        if ticket_id is not None:
            statement = statement.where(ApprovalRequest.ticket_id == ticket_id)
        approvals = (await self._session.execute(statement)).scalars()
        return [_approval_to_summary(approval) for approval in approvals]

    async def list_mock_mutations(self, ticket_id: str | None = None) -> list[MockMutationSummary]:
        from meterdesk_api.models import MockMutation

        statement = select(MockMutation).order_by(MockMutation.executed_at)
        if ticket_id is not None:
            statement = statement.where(MockMutation.ticket_id == ticket_id)
        mutations = (await self._session.execute(statement)).scalars()
        return [_mutation_to_summary(mutation) for mutation in mutations]

    async def get_pending_financial_approval(
        self,
        ticket_id: str,
        action_type: str,
    ) -> ApprovalSummary | None:
        from meterdesk_api.models import ApprovalRequest

        approval = (
            await self._session.execute(
                select(ApprovalRequest)
                .where(ApprovalRequest.ticket_id == ticket_id)
                .where(ApprovalRequest.action_type == action_type)
                .where(ApprovalRequest.status == "pending")
                .limit(1)
            )
        ).scalar_one_or_none()
        return _approval_to_summary(approval) if approval is not None else None

    async def get_pending_approval_by_fingerprint(
        self,
        action_fingerprint: str,
    ) -> ApprovalSummary | None:
        from meterdesk_api.models import ApprovalRequest

        approval = (
            await self._session.execute(
                select(ApprovalRequest)
                .where(ApprovalRequest.action_fingerprint == action_fingerprint)
                .where(ApprovalRequest.status == "pending")
                .limit(1)
            )
        ).scalar_one_or_none()
        return _approval_to_summary(approval) if approval is not None else None

    async def get_executed_mock_mutation_by_fingerprint(
        self,
        action_fingerprint: str,
    ) -> MockMutationSummary | None:
        from meterdesk_api.models import MockMutation

        mutation = (
            await self._session.execute(
                select(MockMutation)
                .where(MockMutation.action_fingerprint == action_fingerprint)
                .where(MockMutation.status == "mock_executed")
                .limit(1)
            )
        ).scalar_one_or_none()
        return _mutation_to_summary(mutation) if mutation is not None else None

    async def list_executed_action_metadata(self, ticket_id: str) -> list[dict[str, object]]:
        from meterdesk_api.models import MockMutation

        mutations = (
            await self._session.execute(
                select(MockMutation)
                .where(MockMutation.ticket_id == ticket_id)
                .where(MockMutation.status == "mock_executed")
                .order_by(MockMutation.executed_at)
            )
        ).scalars()
        return [
            {**mutation.action_metadata, "action_fingerprint": mutation.action_fingerprint}
            for mutation in mutations
        ]

    async def create_agent_run(
        self,
        *,
        ticket_id: str,
        source: str,
        model: str,
        prompt_version: str,
    ) -> AgentRunSummary:
        from meterdesk_api.models import AgentRun

        now = _now()
        run = AgentRun(
            id=_new_id("RUN"),
            ticket_id=ticket_id,
            status="running",
            source=source,
            final_outcome=None,
            internal_resolution=None,
            customer_reply=None,
            error_state=None,
            model=model,
            prompt_version=prompt_version,
            started_at=now,
            completed_at=None,
            seed_marker=None,
        )
        self._session.add(run)
        await self._session.commit()
        return _run_to_summary(run)

    async def complete_agent_run(
        self,
        *,
        agent_run_id: str,
        final_outcome: str,
        internal_resolution: str,
        customer_reply: str,
    ) -> AgentRunSummary:
        from meterdesk_api.models import AgentRun

        run = await self._session.get(AgentRun, agent_run_id)
        run.status = "completed"
        run.final_outcome = final_outcome
        run.internal_resolution = internal_resolution
        run.customer_reply = customer_reply
        run.error_state = None
        run.completed_at = _now()
        await self._session.commit()
        return _run_to_summary(run)

    async def fail_agent_run(self, agent_run_id: str, error_state: str) -> AgentRunSummary:
        from meterdesk_api.models import AgentRun

        run = await self._session.get(AgentRun, agent_run_id)
        run.status = "failed"
        run.error_state = error_state
        run.completed_at = _now()
        await self._session.commit()
        return _run_to_summary(run)

    async def add_tool_trace(
        self,
        *,
        agent_run_id: str,
        category: str,
        risk: str,
        label: str,
        input_summary: str,
        output_summary: str,
        evidence_refs: list[str],
        policy_refs: list[str],
        approval_refs: list[str],
        error_state: str | None = None,
        governance_metadata: dict[str, object] | None = None,
    ) -> ToolTraceSummary:
        from meterdesk_api.models import ToolTrace

        sequence = (
            await self._session.execute(
                select(func.coalesce(func.max(ToolTrace.sequence), 0)).where(
                    ToolTrace.agent_run_id == agent_run_id
                )
            )
        ).scalar_one()
        trace = ToolTrace(
            id=_new_id("trace"),
            agent_run_id=agent_run_id,
            sequence=sequence + 1,
            category=category,
            risk=risk,
            label=label,
            input_summary=input_summary,
            output_summary=output_summary,
            evidence_refs=evidence_refs,
            policy_refs=policy_refs,
            approval_refs=approval_refs,
            error_state=error_state,
            governance_metadata=governance_metadata or {},
            seed_marker=None,
        )
        self._session.add(trace)
        await self._session.commit()
        return _trace_to_summary(trace)

    async def create_approval_request(
        self,
        *,
        ticket_id: str,
        agent_run_id: str,
        title: str,
        action_type: str,
        amount_cents: int,
        amount_display: str,
        currency: str,
        reason: str,
        blocker: str,
        policy_citation: str,
        evidence_refs: list[str],
        action_metadata: dict[str, object],
        action_fingerprint: str | None = None,
    ) -> ApprovalSummary:
        from meterdesk_api.models import ApprovalRequest

        fingerprint = action_fingerprint or build_action_fingerprint(
            ticket_id=ticket_id,
            action_type=action_type,
            amount_cents=amount_cents,
            currency=currency,
            action_metadata=action_metadata,
        )
        approval = ApprovalRequest(
            id=_new_id("APR"),
            ticket_id=ticket_id,
            agent_run_id=agent_run_id,
            title=title,
            status="pending",
            action_type=action_type,
            amount_cents=amount_cents,
            amount_display=amount_display,
            currency=currency,
            reason=reason,
            blocker=blocker,
            policy_citation=policy_citation,
            evidence_refs=evidence_refs,
            action_metadata=action_metadata,
            action_fingerprint=fingerprint,
            created_at=_now(),
            decided_at=None,
            decision=None,
            decided_by=None,
            decision_note=None,
            seed_marker=None,
        )
        self._session.add(approval)
        try:
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise MeterDeskAPIError(
                status_code=409,
                code="approval.pending_duplicate",
                message="A pending financial approval already exists for this action.",
                details={"action_fingerprint": fingerprint},
            ) from error
        return _approval_to_summary(approval)

    async def get_approval(self, approval_id: str) -> ApprovalSummary | None:
        from meterdesk_api.models import ApprovalRequest

        approval = await self._session.get(ApprovalRequest, approval_id)
        return _approval_to_summary(approval) if approval is not None else None

    async def get_mock_mutation_by_approval(
        self,
        approval_id: str,
    ) -> MockMutationSummary | None:
        from meterdesk_api.models import MockMutation

        mutation = (
            await self._session.execute(
                select(MockMutation).where(MockMutation.approval_request_id == approval_id).limit(1)
            )
        ).scalar_one_or_none()
        return _mutation_to_summary(mutation) if mutation is not None else None

    async def approve_request(
        self,
        *,
        approval_id: str,
        decided_by: str,
        decision_note: str | None,
    ) -> tuple[ApprovalSummary, MockMutationSummary]:
        from meterdesk_api.models import ApprovalRequest, MockMutation

        approval = await self._session.get(ApprovalRequest, approval_id)
        mutation = (
            await self._session.execute(
                select(MockMutation).where(MockMutation.approval_request_id == approval.id).limit(1)
            )
        ).scalar_one_or_none()
        if mutation is None:
            duplicate_action = (
                await self._session.execute(
                    select(MockMutation)
                    .where(MockMutation.action_fingerprint == approval.action_fingerprint)
                    .where(MockMutation.status == "mock_executed")
                    .limit(1)
                )
            ).scalar_one_or_none()
            if duplicate_action is not None:
                raise MeterDeskAPIError(
                    status_code=409,
                    code="mutation.duplicate_action",
                    message="This financial action has already been executed.",
                    details={"action_fingerprint": approval.action_fingerprint},
                )
            approval.status = "approved"
            approval.decision = "approved"
            approval.decided_at = _now()
            approval.decided_by = decided_by
            approval.decision_note = decision_note
            approval.blocker = "Approved; mock mutation executed"
            now = _now()
            mutation = MockMutation(
                id=_new_id("MM"),
                ticket_id=approval.ticket_id,
                approval_request_id=approval.id,
                agent_run_id=approval.agent_run_id,
                mutation_type=approval.action_type,
                status="mock_executed",
                amount_cents=approval.amount_cents,
                amount_display=approval.amount_display,
                currency=approval.currency,
                reason=approval.reason,
                action_metadata=approval.action_metadata,
                action_fingerprint=approval.action_fingerprint,
                executed_at=now,
                executed_at_display=_format_display_time(now),
                seed_marker=None,
            )
            self._session.add(mutation)
        else:
            approval.status = "approved"
            approval.decision = "approved"
            approval.decided_at = _now()
            approval.decided_by = decided_by
            approval.decision_note = decision_note
            approval.blocker = "Approved; mock mutation executed"

        try:
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise MeterDeskAPIError(
                status_code=409,
                code="mutation.duplicate_action",
                message="This financial action has already been executed.",
                details={"action_fingerprint": approval.action_fingerprint},
            ) from error
        return _approval_to_summary(approval), _mutation_to_summary(mutation)

    async def reject_request(
        self,
        *,
        approval_id: str,
        decided_by: str,
        decision_note: str | None,
    ) -> ApprovalSummary:
        from meterdesk_api.models import ApprovalRequest

        approval = await self._session.get(ApprovalRequest, approval_id)
        approval.status = "rejected"
        approval.decision = "rejected"
        approval.decided_at = _now()
        approval.decided_by = decided_by
        approval.decision_note = decision_note
        approval.blocker = "Rejected by human reviewer; no mock mutation executed"
        await self._session.commit()
        return _approval_to_summary(approval)

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
                fixture_ticket_id=case.fixture_ticket_id,
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
                details=result.details,
            )
            for result in results
        ]

    async def get_eval_case(self, case_id: str) -> EvalCaseSummary | None:
        from meterdesk_api.models import EvalCase

        case = await self._session.get(EvalCase, case_id)
        if case is None:
            return None
        return EvalCaseSummary(
            id=case.id,
            scenario=case.scenario,
            title=case.title,
            description=case.description,
            expected_outcome=case.expected_outcome,
            required_evidence=case.required_evidence,
            policy_refs=case.policy_refs,
            expected_approval_routing=case.expected_approval_routing,
            fixture_ticket_id=case.fixture_ticket_id,
        )

    async def replace_eval_result(self, result: EvalResultSummary) -> EvalResultSummary:
        from meterdesk_api.models import EvalResult

        await self._session.execute(delete(EvalResult).where(EvalResult.case_id == result.case_id))
        self._session.add(
            EvalResult(
                id=result.id,
                case_id=result.case_id,
                agent_run_id=result.agent_run_id,
                status=result.status,
                summary=result.summary,
                dimension_scores=result.dimension_scores,
                details=result.details,
                created_at=_now(),
                seed_marker=None,
            )
        )
        await self._session.commit()
        return result

    async def create_eval_run(
        self,
        *,
        run_type: str,
        status: str,
        summary: str,
        baseline_name: str | None = None,
        case_id: str | None = None,
    ) -> EvalRunSummary:
        from meterdesk_api.models import EvalSuiteRun

        run = EvalSuiteRun(
            id=_new_id("eval-run"),
            run_type=run_type,
            status=status,
            summary=summary,
            baseline_name=baseline_name,
            case_id=case_id,
            started_at=_now(),
            completed_at=None,
            seed_marker=None,
        )
        self._session.add(run)
        await self._session.commit()
        return _eval_run_to_summary(run)

    async def complete_eval_run(
        self,
        *,
        eval_run_id: str,
        status: str,
        summary: str,
    ) -> EvalRunSummary:
        from meterdesk_api.models import EvalSuiteRun

        run = await self._session.get(EvalSuiteRun, eval_run_id)
        if run is None:
            raise KeyError(eval_run_id)
        run.status = status
        run.summary = summary
        run.completed_at = _now()
        await self._session.commit()
        return _eval_run_to_summary(run)

    async def list_eval_runs(self) -> list[EvalRunSummary]:
        from meterdesk_api.models import EvalSuiteRun

        runs = (
            await self._session.execute(
                select(EvalSuiteRun).order_by(EvalSuiteRun.started_at.desc())
            )
        ).scalars()
        return [_eval_run_to_summary(run) for run in runs]

    async def get_eval_run(self, eval_run_id: str) -> EvalRunSummary | None:
        from meterdesk_api.models import EvalSuiteRun

        run = await self._session.get(EvalSuiteRun, eval_run_id)
        return _eval_run_to_summary(run) if run is not None else None

    async def get_latest_eval_run(self) -> EvalRunSummary | None:
        from meterdesk_api.models import EvalSuiteRun

        run = (
            await self._session.execute(
                select(EvalSuiteRun)
                .where(EvalSuiteRun.run_type != "baseline")
                .where(EvalSuiteRun.status != "running")
                .order_by(EvalSuiteRun.started_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return _eval_run_to_summary(run) if run is not None else None

    async def add_eval_result_snapshot(
        self,
        snapshot: EvalResultSnapshotSummary,
    ) -> EvalResultSnapshotSummary:
        from meterdesk_api.models import EvalResultSnapshot

        self._session.add(
            EvalResultSnapshot(
                id=snapshot.id,
                eval_run_id=snapshot.eval_run_id,
                result_id=snapshot.result_id,
                case_id=snapshot.case_id,
                agent_run_id=snapshot.agent_run_id,
                snapshot_type=snapshot.snapshot_type,
                status=snapshot.status,
                summary=snapshot.summary,
                dimension_scores=snapshot.dimension_scores,
                details=snapshot.details,
                trace_signature=snapshot.trace_signature,
                version_snapshot=snapshot.version_snapshot,
                explanations=snapshot.explanations,
                created_at=snapshot.created_at,
                seed_marker=None,
            )
        )
        await self._session.commit()
        return snapshot

    async def list_eval_result_snapshots(
        self,
        *,
        eval_run_id: str | None = None,
        case_id: str | None = None,
        snapshot_type: str | None = None,
    ) -> list[EvalResultSnapshotSummary]:
        from meterdesk_api.models import EvalResultSnapshot

        query = select(EvalResultSnapshot)
        if eval_run_id is not None:
            query = query.where(EvalResultSnapshot.eval_run_id == eval_run_id)
        if case_id is not None:
            query = query.where(EvalResultSnapshot.case_id == case_id)
        if snapshot_type is not None:
            query = query.where(EvalResultSnapshot.snapshot_type == snapshot_type)
        snapshots = (
            await self._session.execute(query.order_by(EvalResultSnapshot.created_at))
        ).scalars()
        return [_eval_snapshot_to_summary(snapshot) for snapshot in snapshots]

    async def reset_eval_fixture_state(self, fixture_ticket_id: str) -> None:
        from meterdesk_api.models import (
            AgentRun,
            ApprovalRequest,
            EvalResult,
            MockMutation,
            ToolTrace,
        )

        agent_run_ids = select(AgentRun.id).where(AgentRun.ticket_id == fixture_ticket_id)
        approval_ids = select(ApprovalRequest.id).where(
            ApprovalRequest.ticket_id == fixture_ticket_id,
            ApprovalRequest.agent_run_id.in_(agent_run_ids),
        )
        await self._session.execute(
            delete(EvalResult).where(EvalResult.agent_run_id.in_(agent_run_ids))
        )
        await self._session.execute(
            delete(MockMutation).where(
                MockMutation.ticket_id == fixture_ticket_id,
                (
                    MockMutation.agent_run_id.in_(agent_run_ids)
                    | MockMutation.approval_request_id.in_(approval_ids)
                ),
            )
        )
        await self._session.execute(
            delete(ToolTrace).where(ToolTrace.agent_run_id.in_(agent_run_ids))
        )
        await self._session.execute(
            delete(ApprovalRequest).where(
                ApprovalRequest.ticket_id == fixture_ticket_id,
                ApprovalRequest.agent_run_id.in_(agent_run_ids),
            )
        )
        await self._session.execute(delete(AgentRun).where(AgentRun.ticket_id == fixture_ticket_id))
        await self._session.commit()

    async def reset_demo_live_state(self, ticket_id: str) -> None:
        from meterdesk_api.models import AgentRun, ApprovalRequest, MockMutation, ToolTrace

        agent_run_ids = select(AgentRun.id).where(AgentRun.ticket_id == ticket_id)
        await self._session.execute(delete(MockMutation).where(MockMutation.ticket_id == ticket_id))
        await self._session.execute(
            delete(ToolTrace).where(ToolTrace.agent_run_id.in_(agent_run_ids))
        )
        await self._session.execute(
            delete(ApprovalRequest).where(ApprovalRequest.ticket_id == ticket_id)
        )
        await self._session.execute(delete(AgentRun).where(AgentRun.ticket_id == ticket_id))
        await self._session.commit()


async def get_repository(
    session: AsyncSession = SESSION_DEPENDENCY,
) -> AsyncIterator[MeterDeskRepository]:
    yield SqlAlchemyMeterDeskRepository(session)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _now() -> datetime:
    return datetime.now(UTC)


def _format_display_time(value: datetime) -> str:
    return value.strftime("%b %-d, %Y %H:%M UTC")


def _optional_money(
    amount_cents: int | None,
    currency: str | None,
    display: str | None,
) -> MoneyAmount | None:
    if amount_cents is None or currency is None or display is None:
        return None
    return MoneyAmount(amount_cents=amount_cents, currency=currency, display=display)


def _primary_policy_for_scenario(scenario: str, policies: list) -> object:
    preferred_by_scenario = {
        "duplicate_charge": "REFUND-DUP-001",
        "usage_spike": "USAGE-SPIKE-002",
        "credit_refund_dispute": "TRIAL-CREDIT-003",
    }
    preferred = preferred_by_scenario.get(scenario)
    if preferred is not None:
        for policy in policies:
            if policy.id == preferred:
                return policy
    return policies[0]


def _run_to_summary(run) -> AgentRunSummary:
    return AgentRunSummary(
        id=run.id,
        ticket_id=run.ticket_id,
        status=run.status,
        source=run.source,
        final_outcome=run.final_outcome,
        internal_resolution=run.internal_resolution,
        customer_reply=run.customer_reply,
        error_state=run.error_state,
        model=run.model,
        prompt_version=run.prompt_version,
    )


def _trace_to_summary(trace) -> ToolTraceSummary:
    return ToolTraceSummary(
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
        governance_metadata=trace.governance_metadata,
    )


def _eval_run_to_summary(run) -> EvalRunSummary:
    return EvalRunSummary(
        id=run.id,
        run_type=run.run_type,
        status=run.status,
        summary=run.summary,
        baseline_name=run.baseline_name,
        case_id=run.case_id,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


def _eval_snapshot_to_summary(snapshot) -> EvalResultSnapshotSummary:
    return EvalResultSnapshotSummary(
        id=snapshot.id,
        eval_run_id=snapshot.eval_run_id,
        result_id=snapshot.result_id,
        case_id=snapshot.case_id,
        agent_run_id=snapshot.agent_run_id,
        snapshot_type=snapshot.snapshot_type,
        status=snapshot.status,
        summary=snapshot.summary,
        dimension_scores=snapshot.dimension_scores,
        details=snapshot.details,
        trace_signature=snapshot.trace_signature,
        version_snapshot=snapshot.version_snapshot,
        explanations=snapshot.explanations,
        created_at=snapshot.created_at,
    )


def _approval_to_summary(approval) -> ApprovalSummary:
    return ApprovalSummary(
        id=approval.id,
        ticket_id=approval.ticket_id,
        agent_run_id=approval.agent_run_id,
        title=approval.title,
        status=approval.status,
        action_type=approval.action_type,
        amount=MoneyAmount(
            amount_cents=approval.amount_cents,
            currency=approval.currency,
            display=approval.amount_display,
        ),
        reason=approval.reason,
        policy_citation=approval.policy_citation,
        blocker=approval.blocker,
        evidence_refs=approval.evidence_refs,
        action_metadata=approval.action_metadata,
        action_fingerprint=approval.action_fingerprint,
        decided_at=approval.decided_at,
        decision=approval.decision,
        decided_by=approval.decided_by,
        decision_note=approval.decision_note,
    )


def _mutation_to_summary(mutation) -> MockMutationSummary:
    return MockMutationSummary(
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
        action_metadata=mutation.action_metadata,
        action_fingerprint=mutation.action_fingerprint,
        executed_at=mutation.executed_at,
        executed_at_display=mutation.executed_at_display,
    )
