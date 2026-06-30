from __future__ import annotations

import pytest

from meterdesk_api.agent.compliance import RunComplianceChecker
from meterdesk_api.seed_data import build_seed_repository


@pytest.mark.asyncio
async def test_demo_live_reset_clears_only_requested_ticket_runtime_state() -> None:
    repository = build_seed_repository()

    await repository.reset_demo_live_state("TCK-1042")

    runs = await repository.list_agent_runs("TCK-1042")
    traces = await repository.list_traces("RUN-2042")
    approvals = await repository.list_approvals(status=None, ticket_id="TCK-1042")
    mutations = await repository.list_mock_mutations("TCK-1042")
    evidence = await repository.get_billing_evidence("TCK-1042")
    eval_cases = await repository.list_eval_cases()
    credit_refund_runs = await repository.list_agent_runs("TCK-1137")
    credit_refund_approvals = await repository.list_approvals(status=None, ticket_id="TCK-1137")

    assert runs == []
    assert traces is None
    assert approvals == []
    assert mutations == []
    assert evidence is not None
    assert evidence.invoice.id == "INV-2026-0418"
    assert len(eval_cases) == 9
    assert [run.id for run in credit_refund_runs] == ["RUN-1137"]
    assert [approval.id for approval in credit_refund_approvals] == ["APR-1137"]

    await repository.reset_demo_live_state("TCK-1137")

    assert await repository.list_agent_runs("TCK-1137") == []
    assert await repository.list_traces("RUN-1137") is None
    assert await repository.list_approvals(status=None, ticket_id="TCK-1137") == []
    assert await repository.list_mock_mutations("TCK-1137") == []


@pytest.mark.asyncio
async def test_seeded_duplicate_charge_baseline_traces_include_governance_metadata() -> None:
    repository = build_seed_repository()

    traces = await repository.list_traces("RUN-2042")

    assert traces is not None
    assert [trace.governance_metadata["gate_result"] for trace in traces] == [
        "allowed",
        "allowed",
        "allowed",
        "allowed",
        "allowed",
        "allowed",
        "allowed",
    ]
    assert [trace.category for trace in traces[:2]] == ["plan.investigation", "plan.verify"]
    assert traces[1].governance_metadata["planning"]["status"] == "accepted"
    assert traces[-1].governance_metadata["policy_id"] == "approval.create_request"


@pytest.mark.asyncio
async def test_seeded_credit_refund_baseline_passes_compliance_with_pending_credit_approval() -> (
    None
):
    repository = build_seed_repository()

    runs = await repository.list_agent_runs("TCK-1137")
    traces = await repository.list_traces("RUN-1137")
    approvals = await repository.list_approvals(status=None, ticket_id="TCK-1137")
    mutations = await repository.list_mock_mutations("TCK-1137")
    compliance = await RunComplianceChecker(repository).check("RUN-1137")

    assert [run.id for run in runs] == ["RUN-1137"]
    assert runs[0].final_outcome == "goodwill_credit_requires_approval"
    assert traces is not None
    assert [trace.category for trace in traces] == [
        "plan.investigation",
        "plan.verify",
        "read.credit_refund_evidence",
        "read.prior_financial_actions",
        "decision.credit_refund_eligibility",
        "draft.resolution",
        "approval.create_request",
    ]
    assert len(approvals) == 1
    assert approvals[0].id == "APR-1137"
    assert approvals[0].status == "pending"
    assert approvals[0].action_type == "goodwill_credit"
    assert approvals[0].amount.display == "$120.00"
    assert approvals[0].action_fingerprint == (
        "ticket:TCK-1137|action:goodwill_credit|target:cred-ledger-1137|amount:12000|currency:USD"
    )
    assert mutations == []
    assert compliance is not None
    assert compliance.status == "passed"
    assert compliance.high_risk_gate_count == 1
    assert compliance.verified_governed_action_count == 7
