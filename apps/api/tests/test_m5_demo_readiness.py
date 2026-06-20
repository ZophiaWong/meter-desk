from __future__ import annotations

import pytest

from meterdesk_api.seed_data import build_seed_repository


@pytest.mark.asyncio
async def test_demo_live_reset_clears_only_duplicate_charge_runtime_state() -> None:
    repository = build_seed_repository()

    await repository.reset_demo_live_state("TCK-1042")

    runs = await repository.list_agent_runs("TCK-1042")
    traces = await repository.list_traces("RUN-2042")
    approvals = await repository.list_approvals(status=None, ticket_id="TCK-1042")
    mutations = await repository.list_mock_mutations("TCK-1042")
    evidence = await repository.get_billing_evidence("TCK-1042")
    eval_cases = await repository.list_eval_cases()
    historical_mutations = await repository.list_mock_mutations("TCK-1137")

    assert runs == []
    assert traces is None
    assert approvals == []
    assert mutations == []
    assert evidence is not None
    assert evidence.invoice.id == "INV-2026-0418"
    assert len(eval_cases) == 9
    assert [mutation.id for mutation in historical_mutations] == ["MM-1137-001"]


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
    ]
    assert traces[-1].governance_metadata["policy_id"] == "approval.create_request"
