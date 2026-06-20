import asyncio

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from meterdesk_api.db import create_engine
from meterdesk_api.models import (
    AgentRun,
    ApprovalRequest,
    Charge,
    CreditLedgerEntry,
    CustomerAccount,
    EvalCase,
    EvalResult,
    Invoice,
    MockMutation,
    PolicyRule,
    Ticket,
    TicketPolicyLink,
    ToolTrace,
    UsageRecord,
)
from meterdesk_api.seed_data import (
    AGENT_RUNS,
    APPROVALS,
    BILLING_EVIDENCE,
    DEMO_SEED_MARKER,
    DEMO_TICKET_IDS,
    EVAL_BILLING_EVIDENCE,
    EVAL_CASES,
    EVAL_FIXTURE_TICKET_IDS,
    EVAL_RESULTS,
    EVAL_TICKET_DETAILS,
    MOCK_MUTATIONS,
    TICKET_DETAILS,
    TICKETS,
    TRACES,
    utc,
)

DELETE_ORDER = [
    EvalResult,
    MockMutation,
    ToolTrace,
    ApprovalRequest,
    AgentRun,
    Charge,
    CreditLedgerEntry,
    UsageRecord,
    TicketPolicyLink,
    Invoice,
    EvalCase,
    PolicyRule,
    Ticket,
    CustomerAccount,
]


async def seed_demo_data() -> None:
    engine = create_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            async with session.begin():
                all_ticket_details = {**TICKET_DETAILS, **EVAL_TICKET_DETAILS}
                all_billing_evidence = {**BILLING_EVIDENCE, **EVAL_BILLING_EVIDENCE}
                reset_ticket_ids = (*DEMO_TICKET_IDS, *EVAL_FIXTURE_TICKET_IDS)
                demo_agent_run_ids = select(AgentRun.id).where(
                    AgentRun.ticket_id.in_(reset_ticket_ids)
                )
                await session.execute(
                    delete(EvalResult).where(
                        EvalResult.case_id.in_([case.id for case in EVAL_CASES])
                    )
                )
                await session.execute(
                    delete(EvalResult).where(EvalResult.agent_run_id.in_(demo_agent_run_ids))
                )
                await session.execute(
                    delete(MockMutation).where(MockMutation.ticket_id.in_(reset_ticket_ids))
                )
                await session.execute(
                    delete(ToolTrace).where(ToolTrace.agent_run_id.in_(demo_agent_run_ids))
                )
                await session.execute(
                    delete(ApprovalRequest).where(ApprovalRequest.ticket_id.in_(reset_ticket_ids))
                )
                await session.execute(
                    delete(AgentRun).where(AgentRun.ticket_id.in_(reset_ticket_ids))
                )

                for model in DELETE_ORDER:
                    await session.execute(
                        delete(model).where(model.seed_marker == DEMO_SEED_MARKER)
                    )

                accounts = {
                    detail.customer.id: detail.customer for detail in all_ticket_details.values()
                }
                session.add_all(
                    CustomerAccount(
                        id=account.id,
                        name=account.name,
                        plan=account.plan,
                        owner_email=account.owner,
                        status=account.status,
                        seed_marker=DEMO_SEED_MARKER,
                    )
                    for account in accounts.values()
                )
                await session.flush()

                session.add_all(
                    Ticket(
                        id=ticket.id,
                        customer_account_id=TICKET_DETAILS[ticket.id].customer.id,
                        title=TICKET_DETAILS[ticket.id].title,
                        scenario=ticket.scenario,
                        status=ticket.status,
                        severity=TICKET_DETAILS[ticket.id].severity,
                        opened_at=TICKET_DETAILS[ticket.id].opened_at,
                        opened_at_display=TICKET_DETAILS[ticket.id].opened_at_display,
                        summary=TICKET_DETAILS[ticket.id].summary,
                        outcome=TICKET_DETAILS[ticket.id].outcome,
                        sort_order=position,
                        is_active=ticket.is_active,
                        seed_marker=DEMO_SEED_MARKER,
                    )
                    for position, ticket in enumerate(TICKETS, start=1)
                )
                session.add_all(
                    Ticket(
                        id=ticket_id,
                        customer_account_id=detail.customer.id,
                        title=detail.title,
                        scenario=detail.scenario,
                        status=detail.status,
                        severity=detail.severity,
                        opened_at=detail.opened_at,
                        opened_at_display=detail.opened_at_display,
                        summary=detail.summary,
                        outcome=detail.outcome,
                        sort_order=100 + position,
                        is_active=False,
                        seed_marker=DEMO_SEED_MARKER,
                    )
                    for position, (ticket_id, detail) in enumerate(
                        EVAL_TICKET_DETAILS.items(), start=1
                    )
                )
                await session.flush()

                policies = {
                    evidence.policy.id: evidence.policy
                    for evidence in all_billing_evidence.values()
                }
                session.add_all(
                    PolicyRule(
                        id=policy.id,
                        version=policy.version,
                        citation=policy.citation,
                        title=policy.title,
                        reason=policy.reason,
                        body=f"{policy.title}: {policy.reason}",
                        seed_marker=DEMO_SEED_MARKER,
                    )
                    for policy in policies.values()
                )
                await session.flush()

                session.add_all(
                    TicketPolicyLink(
                        ticket_id=ticket_id,
                        policy_rule_id=evidence.policy.id,
                        seed_marker=DEMO_SEED_MARKER,
                    )
                    for ticket_id, evidence in all_billing_evidence.items()
                )

                session.add_all(
                    Invoice(
                        id=evidence.invoice.id,
                        ticket_id=ticket_id,
                        account_id=evidence.account.id,
                        period_start=evidence.invoice.period_start,
                        period_end=evidence.invoice.period_end,
                        period_display=evidence.invoice.period_display,
                        total_amount_cents=evidence.invoice.total.amount_cents,
                        total_display=evidence.invoice.total.display,
                        currency=evidence.invoice.total.currency,
                        status=evidence.invoice.status,
                        seed_marker=DEMO_SEED_MARKER,
                    )
                    for ticket_id, evidence in all_billing_evidence.items()
                )
                await session.flush()

                session.add_all(
                    Charge(
                        id=charge.id,
                        invoice_id=evidence.invoice.id,
                        amount_cents=charge.amount.amount_cents,
                        amount_display=charge.amount.display,
                        currency=charge.amount.currency,
                        status=charge.status,
                        captured_at=charge.captured_at,
                        captured_at_display=charge.captured_at_display,
                        processor_state=charge.processor_state,
                        seed_marker=DEMO_SEED_MARKER,
                    )
                    for evidence in all_billing_evidence.values()
                    for charge in evidence.charges
                )
                await session.flush()

                session.add_all(
                    UsageRecord(
                        id=usage.id,
                        ticket_id=ticket_id,
                        account_id=evidence.account.id,
                        label=usage.label,
                        detail=usage.detail,
                        period_start=usage.period_start,
                        period_end=usage.period_end,
                        seed_marker=DEMO_SEED_MARKER,
                    )
                    for ticket_id, evidence in all_billing_evidence.items()
                    for usage in evidence.usage
                )

                session.add_all(
                    CreditLedgerEntry(
                        id=credit.id,
                        ticket_id=ticket_id,
                        account_id=evidence.account.id,
                        label=credit.label,
                        detail=credit.detail,
                        amount_cents=credit.amount.amount_cents if credit.amount else None,
                        amount_display=credit.amount.display if credit.amount else None,
                        currency=credit.amount.currency if credit.amount else None,
                        seed_marker=DEMO_SEED_MARKER,
                    )
                    for ticket_id, evidence in all_billing_evidence.items()
                    for credit in evidence.credits
                )
                await session.flush()

                session.add_all(
                    AgentRun(
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
                        started_at=utc(2026, 6, 5, 12, 5),
                        completed_at=utc(2026, 6, 5, 12, 6),
                        seed_marker=DEMO_SEED_MARKER,
                    )
                    for runs in AGENT_RUNS.values()
                    for run in runs
                )
                await session.flush()

                session.add_all(
                    ToolTrace(
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
                        seed_marker=DEMO_SEED_MARKER,
                    )
                    for traces in TRACES.values()
                    for trace in traces
                )

                session.add_all(
                    ApprovalRequest(
                        id=approval.id,
                        ticket_id=approval.ticket_id,
                        agent_run_id=approval.agent_run_id,
                        title=approval.title,
                        status=approval.status,
                        action_type="original_refund",
                        amount_cents=approval.amount.amount_cents,
                        amount_display=approval.amount.display,
                        currency=approval.amount.currency,
                        reason=approval.reason,
                        blocker=approval.blocker,
                        policy_citation=approval.policy_citation,
                        evidence_refs=["invoice INV-2026-0418", "charge ch_2026_0418_B"],
                        action_metadata=approval.action_metadata,
                        created_at=utc(2026, 6, 5, 12, 6),
                        decided_by=approval.decided_by,
                        decision_note=approval.decision_note,
                        seed_marker=DEMO_SEED_MARKER,
                    )
                    for approval in APPROVALS
                )
                await session.flush()

                session.add(
                    ApprovalRequest(
                        id="APR-1137-HIST",
                        ticket_id="TCK-1137",
                        agent_run_id=None,
                        title="Historical goodwill credit approved",
                        status="approved",
                        action_type="goodwill_credit",
                        amount_cents=12000,
                        amount_display="$120.00",
                        currency="USD",
                        reason=(
                            "Historical read-only goodwill credit for trial cancellation dispute."
                        ),
                        blocker="Approved historical mock mutation",
                        policy_citation="TRIAL-CREDIT-003 v2026.03",
                        evidence_refs=["credit ledger cred-ledger-1137"],
                        action_metadata={
                            "action_type": "goodwill_credit",
                            "credit_ledger_entry_id": "cred-ledger-1137",
                        },
                        created_at=utc(2026, 5, 28, 15, 40),
                        decided_at=utc(2026, 5, 28, 15, 44),
                        decision="approved",
                        decided_by="Demo Operator",
                        decision_note="Historical seeded approval.",
                        seed_marker=DEMO_SEED_MARKER,
                    )
                )
                await session.flush()

                session.add_all(
                    MockMutation(
                        id=mutation.id,
                        ticket_id=mutation.ticket_id,
                        approval_request_id=mutation.approval_request_id,
                        agent_run_id=mutation.agent_run_id,
                        mutation_type=mutation.mutation_type,
                        status=mutation.status,
                        amount_cents=mutation.amount.amount_cents,
                        amount_display=mutation.amount.display,
                        currency=mutation.amount.currency,
                        reason=mutation.reason,
                        action_metadata=mutation.action_metadata,
                        executed_at=mutation.executed_at,
                        executed_at_display=mutation.executed_at_display,
                        seed_marker=DEMO_SEED_MARKER,
                    )
                    for mutation in MOCK_MUTATIONS
                )
                await session.flush()

                session.add_all(
                    EvalCase(
                        id=case.id,
                        scenario=case.scenario,
                        title=case.title,
                        description=case.description,
                        expected_outcome=case.expected_outcome,
                        required_evidence=case.required_evidence,
                        policy_refs=case.policy_refs,
                        expected_approval_routing=case.expected_approval_routing,
                        fixture_ticket_id=case.fixture_ticket_id,
                        grading_criteria={
                            "deterministic": [
                                "required_evidence",
                                "policy_refs",
                                "approval_routing",
                            ]
                        },
                        seed_marker=DEMO_SEED_MARKER,
                    )
                    for case in EVAL_CASES
                )
                await session.flush()

                session.add_all(
                    EvalResult(
                        id=result.id,
                        case_id=result.case_id,
                        agent_run_id=result.agent_run_id,
                        status=result.status,
                        summary=result.summary,
                        dimension_scores=result.dimension_scores,
                        details=result.details,
                        created_at=utc(2026, 6, 5, 12, 7),
                        seed_marker=DEMO_SEED_MARKER,
                    )
                    for result in EVAL_RESULTS
                )
    finally:
        await engine.dispose()

    print("MeterDesk M3 demo seed complete: demo-owned rows reset and rebuilt.")


def main() -> None:
    asyncio.run(seed_demo_data())


if __name__ == "__main__":
    main()
