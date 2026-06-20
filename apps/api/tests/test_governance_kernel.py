from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from meterdesk_api.agent.governance import (
    GovernanceKernel,
    GovernanceViolation,
    list_tool_policy_summaries,
)
from meterdesk_api.main import app
from meterdesk_api.seed_data import build_seed_repository


def test_tool_policy_registry_exposes_current_golden_path_matrix() -> None:
    policies = list_tool_policy_summaries()

    assert [policy.id for policy in policies] == [
        "read.billing_evidence",
        "read.prior_financial_actions",
        "decision.refund_eligibility",
        "draft.resolution",
        "approval.create_request",
        "mutation.mock_refund",
    ]
    mutation_policy = policies[-1]
    assert mutation_policy.risk == "High"
    assert mutation_policy.requires_approval_ref is True
    assert mutation_policy.gate == "Requires approved approval request"


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
    assert trace.governance_metadata["required_ref_categories"] == [
        "invoice",
        "charge",
        "credit",
        "usage",
        "policy",
    ]
    assert trace.governance_metadata["missing_ref_categories"] == []


@pytest.mark.asyncio
async def test_governance_kernel_blocks_missing_policy_refs() -> None:
    repository = build_seed_repository()
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


@pytest.mark.asyncio
async def test_governance_tool_policy_api_returns_read_only_matrix() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/governance/tool-policies")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 6
    assert payload[-1]["id"] == "mutation.mock_refund"
    assert payload[-1]["risk"] == "High"
    assert payload[-1]["requires_approval_ref"] is True
