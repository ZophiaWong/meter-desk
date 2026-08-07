from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api_client import authenticate_demo_client
from meterdesk_api.agent.governance import (
    GovernanceKernel,
    GovernanceViolation,
    list_tool_policy_summaries,
)
from meterdesk_api.main import app
from meterdesk_api.schemas import ApprovalDecisionActor
from meterdesk_api.seed_data import build_seed_repository


def test_tool_policy_registry_exposes_current_golden_path_matrix() -> None:
    policies = list_tool_policy_summaries()

    assert [policy.id for policy in policies] == [
        "plan.investigation",
        "plan.verify",
        "read.billing_evidence",
        "read.prior_financial_actions",
        "read.credit_refund_evidence",
        "decision.refund_eligibility",
        "decision.credit_refund_eligibility",
        "draft.resolution",
        "approval.create_request",
        "mutation.mock_refund",
        "mutation.mock_credit_or_refund",
    ]
    mutation_policy = policies[-1]
    assert mutation_policy.risk == "High"
    assert mutation_policy.requires_approval_ref is True
    assert mutation_policy.gate == "Requires approved approval request"
    assert mutation_policy.version == "1.0.0"


@pytest.mark.asyncio
async def test_governance_kernel_records_allowed_trace_metadata() -> None:
    repository = build_seed_repository()
    await repository.reset_demo_live_state("TCK-1042")
    run = await repository.create_agent_run(
        ticket_id="TCK-1042",
        source="test",
        model="test-model",
        prompt_version="test-v1",
    )

    trace = await GovernanceKernel(repository).record_action(
        agent_run_id=run.id,
        policy_id="read.billing_evidence",
        label="Collected Duplicate Charge billing evidence",
        input_summary="Read ticket, invoice, charges, credits, usage, and policy.",
        output_summary="Found invoice INV-2026-0418 and two charge records.",
        evidence_refs=[
            "invoice INV-2026-0418",
            "charge ch_2026_0418_A",
            "charge ch_2026_0418_B",
            "credit cred-ledger-1042",
            "usage usage-2026-04-northstar",
        ],
        policy_refs=["REFUND-DUP-001 v2026.02"],
        approval_refs=[],
    )

    assert trace.category == "read.billing_evidence"
    assert trace.risk == "Low"
    assert trace.governance_metadata["gate_result"] == "allowed"
    assert trace.governance_metadata["enforcement_outcome"] == "trace_recorded"
    assert trace.governance_metadata["schema_version"] == "1.0.0"
    assert trace.governance_metadata["reason_code"] == "governance.allowed"
    assert trace.governance_metadata["negative_evidence_refs"] == []
    assert trace.governance_metadata["required_ref_categories"] == [
        "invoice",
        "charge",
        "credit",
        "usage",
        "policy",
    ]
    assert trace.governance_metadata["missing_ref_categories"] == []


@pytest.mark.asyncio
async def test_governance_kernel_records_blocked_trace_for_missing_policy_refs() -> None:
    repository = build_seed_repository()
    await repository.reset_demo_live_state("TCK-1042")
    run = await repository.create_agent_run(
        ticket_id="TCK-1042",
        source="test",
        model="test-model",
        prompt_version="test-v1",
    )

    with pytest.raises(GovernanceViolation, match="policy"):
        await GovernanceKernel(repository).record_action(
            agent_run_id=run.id,
            policy_id="decision.refund_eligibility",
            label="Evaluated refund eligibility",
            input_summary="Compared captured charges.",
            output_summary="Refund requires approval.",
            evidence_refs=["invoice INV-2026-0418", "charge ch_2026_0418_B"],
            policy_refs=[],
            approval_refs=[],
        )
    traces = await repository.list_traces(run.id)

    assert traces is not None
    assert len(traces) == 1
    assert traces[0].category == "decision.refund_eligibility"
    assert traces[0].error_state == "governance.missing_required_ref"
    assert traces[0].governance_metadata["gate_result"] == "blocked"
    assert traces[0].governance_metadata["enforcement_outcome"] == "blocked_before_execution"
    assert traces[0].governance_metadata["reason_code"] == "governance.missing_required_ref"
    assert traces[0].governance_metadata["missing_ref_categories"] == ["policy"]


@pytest.mark.asyncio
async def test_governance_kernel_blocks_high_risk_action_without_approval_ref() -> None:
    repository = build_seed_repository()

    with pytest.raises(GovernanceViolation, match="approval"):
        await GovernanceKernel(repository).record_action(
            agent_run_id="RUN-2042",
            policy_id="mutation.mock_refund",
            label="Executed approved mock financial mutation",
            input_summary="Executed approved request.",
            output_summary="Created mock mutation.",
            evidence_refs=["invoice INV-2026-0418", "charge ch_2026_0418_B"],
            policy_refs=["REFUND-DUP-001 v2026.02"],
            approval_refs=[],
        )


@pytest.mark.asyncio
async def test_governance_kernel_blocks_high_risk_action_with_pending_approval() -> None:
    repository = build_seed_repository()

    with pytest.raises(GovernanceViolation, match="requires approved approval"):
        await GovernanceKernel(repository).record_action(
            agent_run_id="RUN-2042",
            policy_id="mutation.mock_refund",
            label="Executed approved mock financial mutation",
            input_summary="Executed approved request APR-2042.",
            output_summary="Created mock mutation.",
            evidence_refs=["invoice INV-2026-0418", "charge ch_2026_0418_B"],
            policy_refs=["REFUND-DUP-001 v2026.02"],
            approval_refs=["APR-2042"],
        )
    traces = await repository.list_traces("RUN-2042")

    assert traces is not None
    assert traces[-1].category == "mutation.mock_refund"
    assert traces[-1].error_state == "governance.approval_gate_blocked"
    assert traces[-1].governance_metadata["gate_result"] == "blocked"
    assert traces[-1].governance_metadata["reason_code"] == "governance.approval_gate_blocked"


@pytest.mark.asyncio
async def test_governance_kernel_does_not_trace_a_stale_same_direction_retry(
    monkeypatch,
) -> None:
    repository = build_seed_repository()
    pending_approval = await repository.get_approval("APR-2042")
    assert pending_approval is not None
    first_result = await repository.approve_request(
        approval_id="APR-2042",
        decision_actor=ApprovalDecisionActor(
            subject="demo-approver",
            display_name="Demo Approver",
            role="approver",
            source="demo_session",
        ),
        decision_request_id="req_first_execution",
        decision_note="First decision owns the execution trace.",
    )
    original_get_approval = repository.get_approval
    approval_reads = 0

    async def stale_get_approval(approval_id: str):
        nonlocal approval_reads
        approval_reads += 1
        if approval_reads == 1:
            return pending_approval
        return await original_get_approval(approval_id)

    monkeypatch.setattr(repository, "get_approval", stale_get_approval)
    traces_before = await repository.list_traces("RUN-2042")

    response = await GovernanceKernel(repository).execute_approved_mock_refund(
        approval_id="APR-2042",
        decision_actor=ApprovalDecisionActor(
            subject="demo-admin",
            display_name="Demo Admin",
            role="admin",
            source="demo_session",
        ),
        decision_request_id="req_stale_retry",
        decision_note="A retry must not create another execution trace.",
    )
    traces_after = await repository.list_traces("RUN-2042")

    assert response.approval == first_result.approval
    assert response.mock_mutation == first_result.mutation
    assert traces_before is not None
    assert traces_after == traces_before


@pytest.mark.asyncio
async def test_governance_kernel_records_negative_evidence_refs() -> None:
    repository = build_seed_repository()
    await repository.reset_demo_live_state("TCK-1042")
    run = await repository.create_agent_run(
        ticket_id="TCK-1042",
        source="test",
        model="test-model",
        prompt_version="test-v1",
    )

    trace = await GovernanceKernel(repository).record_action(
        agent_run_id=run.id,
        policy_id="read.prior_financial_actions",
        label="Checked prior approvals and mock mutations",
        input_summary="Read existing approval and mutation state for TCK-1042.",
        output_summary="Found no executed mock financial actions.",
        evidence_refs=["ticket TCK-1042"],
        policy_refs=[],
        approval_refs=[],
        negative_evidence_refs=["no_prior_mock_mutation"],
    )

    assert trace.governance_metadata["negative_evidence_refs"] == ["no_prior_mock_mutation"]


@pytest.mark.asyncio
async def test_governance_kernel_blocks_approval_creation_for_executed_fingerprint() -> None:
    repository = build_seed_repository()
    await repository.reset_demo_live_state("TCK-1042")
    run = await repository.create_agent_run(
        ticket_id="TCK-1042",
        source="test",
        model="test-model",
        prompt_version="test-v1",
    )
    kernel = GovernanceKernel(repository)
    await repository.finalize_run(
        agent_run_id=run.id,
        final_outcome="confirmed_duplicate_charge",
        internal_resolution="Refund duplicate captured charge.",
        customer_reply="Draft only.",
        target_status="awaiting_approval",
        reason_code="decision.approval_required",
        approval={
            "title": "Original refund pending approval",
            "action_type": "original_refund",
            "amount_cents": 124800,
            "amount_display": "$1,248.00",
            "currency": "USD",
            "reason": "Refund duplicate captured charge.",
            "blocker": "Mutation blocked until human approval",
            "policy_citation": "REFUND-DUP-001 v2026.02",
            "evidence_refs": ["invoice INV-2026-0418", "charge ch_2026_0418_B"],
            "action_metadata": {
                "action_type": "original_refund",
                "invoice_id": "INV-2026-0418",
                "target_charge_id": "ch_2026_0418_B",
            },
        },
    )
    approval = (await repository.list_approvals(ticket_id="TCK-1042"))[0]
    await kernel.execute_approved_mock_refund(
        approval.id,
        decision_actor=ApprovalDecisionActor(
            subject="demo-approver",
            display_name="Demo Approver",
            role="approver",
            source="demo_session",
        ),
        decision_request_id="req_test_governance_approval",
        decision_note="Approved.",
    )
    second_run = await repository.create_agent_run(
        ticket_id="TCK-1042",
        source="test",
        model="test-model",
        prompt_version="test-v1",
    )

    with pytest.raises(GovernanceViolation) as error:
        await kernel.create_approval_request(
            ticket_id="TCK-1042",
            agent_run_id=second_run.id,
            title="Original refund pending approval",
            action_type="original_refund",
            amount_cents=124800,
            amount_display="$1,248.00",
            currency="USD",
            reason="Refund duplicate captured charge.",
            blocker="Mutation blocked until human approval",
            policy_citation="REFUND-DUP-001 v2026.02",
            evidence_refs=["invoice INV-2026-0418", "charge ch_2026_0418_B"],
            policy_refs=["REFUND-DUP-001 v2026.02"],
            action_metadata={
                "action_type": "original_refund",
                "invoice_id": "INV-2026-0418",
                "target_charge_id": "ch_2026_0418_B",
            },
            label="Created approval request for financial action",
            input_summary="Created human approval gate for proposed original refund.",
            output_summary="Approval request is pending.",
        )
    traces = await repository.list_traces(second_run.id)

    assert error.value.code == "mutation.duplicate_action"
    assert traces is not None
    assert traces[-1].error_state == "mutation.duplicate_action"


@pytest.mark.asyncio
async def test_governance_tool_policy_api_returns_read_only_matrix() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client)
        response = await client.get("/governance/tool-policies")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 11
    assert payload[0]["id"] == "plan.investigation"
    assert payload[1]["id"] == "plan.verify"
    assert payload[-1]["id"] == "mutation.mock_credit_or_refund"
    assert payload[-1]["risk"] == "High"
    assert payload[-1]["requires_approval_ref"] is True
