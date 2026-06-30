from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from meterdesk_api.agent.compliance import RunComplianceChecker
from meterdesk_api.main import app
from meterdesk_api.repositories import get_repository
from meterdesk_api.schemas import MockMutationSummary, MoneyAmount
from meterdesk_api.seed_data import build_seed_repository


@pytest.mark.asyncio
async def test_seeded_duplicate_charge_baseline_passes_run_compliance() -> None:
    repository = build_seed_repository()

    result = await RunComplianceChecker(repository).check("RUN-2042")

    assert result.status == "passed"
    assert result.failed_checks == []
    assert result.reason_codes == []
    assert result.high_risk_gate_count == 1
    assert result.verified_governed_action_count == 7
    assert result.policy_versions_seen == {
        "approval.create_request": "1.0.0",
        "decision.refund_eligibility": "1.0.0",
        "draft.resolution": "1.0.0",
        "plan.investigation": "1.0.0",
        "plan.verify": "1.0.0",
        "read.billing_evidence": "1.0.0",
        "read.prior_financial_actions": "1.0.0",
    }


@pytest.mark.asyncio
async def test_managed_run_with_missing_governance_metadata_fails_compliance() -> None:
    repository = build_seed_repository()
    await repository.reset_demo_live_state("TCK-1042")
    run = await repository.create_agent_run(
        ticket_id="TCK-1042",
        source="m3_governed_loop",
        model="test-model",
        prompt_version="test-v1",
    )
    trace = await repository.add_tool_trace(
        agent_run_id=run.id,
        category="read.billing_evidence",
        risk="Low",
        label="Legacy trace without metadata",
        input_summary="Read evidence.",
        output_summary="Found evidence.",
        evidence_refs=["invoice INV-2026-0418"],
        policy_refs=[],
        approval_refs=[],
        governance_metadata={},
    )

    result = await RunComplianceChecker(repository).check(run.id)

    assert result.status == "failed"
    assert result.failed_checks[0].code == "governance.metadata_missing"
    assert result.affected_trace_ids == [trace.id]


@pytest.mark.asyncio
async def test_legacy_run_without_current_metadata_is_unsupported() -> None:
    repository = build_seed_repository()
    await repository.reset_demo_live_state("TCK-1042")
    run = await repository.create_agent_run(
        ticket_id="TCK-1042",
        source="legacy_import",
        model="legacy-model",
        prompt_version="legacy-v1",
    )
    trace = await repository.add_tool_trace(
        agent_run_id=run.id,
        category="read.billing_evidence",
        risk="Low",
        label="Legacy trace without metadata",
        input_summary="Read evidence.",
        output_summary="Found evidence.",
        evidence_refs=["invoice INV-2026-0418"],
        policy_refs=[],
        approval_refs=[],
        governance_metadata={},
    )

    result = await RunComplianceChecker(repository).check(run.id)

    assert result.status == "unsupported"
    assert result.failed_checks[0].code == "governance.metadata_unsupported"
    assert result.affected_trace_ids == [trace.id]


@pytest.mark.asyncio
async def test_compliance_recomputes_missing_refs_instead_of_trusting_gate_result() -> None:
    repository = build_seed_repository()
    await repository.reset_demo_live_state("TCK-1042")
    run = await repository.create_agent_run(
        ticket_id="TCK-1042",
        source="m3_governed_loop",
        model="test-model",
        prompt_version="test-v1",
    )
    trace = await repository.add_tool_trace(
        agent_run_id=run.id,
        category="read.billing_evidence",
        risk="Low",
        label="Trace with falsely allowed metadata",
        input_summary="Read partial evidence.",
        output_summary="Found only invoice evidence.",
        evidence_refs=["invoice INV-2026-0418"],
        policy_refs=["REFUND-DUP-001 v2026.02"],
        approval_refs=[],
        governance_metadata={
            "schema_version": "1.0.0",
            "policy_id": "read.billing_evidence",
            "policy_version": "1.0.0",
            "risk": "Low",
            "gate": "Always allowed; trace required",
            "gate_result": "allowed",
            "enforcement_outcome": "trace_recorded",
            "required_ref_categories": ["invoice", "charge", "credit", "usage", "policy"],
            "satisfied_ref_categories": ["invoice", "charge", "credit", "usage", "policy"],
            "missing_ref_categories": [],
            "negative_evidence_refs": [],
            "trace_required": True,
            "reason_code": "governance.allowed",
        },
    )

    result = await RunComplianceChecker(repository).check(run.id)

    assert result.status == "failed"
    assert result.failed_checks[0].code == "governance.missing_required_ref"
    assert result.affected_trace_ids == [trace.id]
    assert result.missing_ref_categories == ["charge", "credit", "usage"]


@pytest.mark.asyncio
async def test_mutation_without_approved_approval_fails_compliance() -> None:
    repository = build_seed_repository()
    await repository.reset_demo_live_state("TCK-1042")
    run = await repository.create_agent_run(
        ticket_id="TCK-1042",
        source="m3_governed_loop",
        model="test-model",
        prompt_version="test-v1",
    )
    mutation = MockMutationSummary(
        id="MM-unsafe",
        ticket_id="TCK-1042",
        approval_request_id=None,
        agent_run_id=run.id,
        mutation_type="original_refund",
        status="mock_executed",
        amount=MoneyAmount(amount_cents=124800, currency="USD", display="$1,248.00"),
        reason="Unsafe mutation without approval.",
        action_metadata={"target_charge_id": "ch_2026_0418_B"},
        action_fingerprint=(
            "ticket:TCK-1042|action:original_refund|target:ch_2026_0418_B|"
            "amount:124800|currency:USD"
        ),
        executed_at=datetime(2026, 6, 23, tzinfo=UTC),
        executed_at_display="Jun 23, 2026 00:00 UTC",
    )
    repository._mock_mutations.append(mutation)

    result = await RunComplianceChecker(repository).check(run.id)

    assert result.status == "failed"
    assert result.failed_checks[0].code == "mutation.approval_missing"
    assert result.failed_checks[0].mutation_ids == ["MM-unsafe"]


@pytest.mark.asyncio
async def test_duplicate_executed_action_fingerprint_fails_compliance() -> None:
    repository = build_seed_repository()
    duplicate = repository._mock_mutations[0].model_copy(update={"id": "MM-EVAL-CR-003-duplicate"})
    repository._mock_mutations.append(duplicate)

    result = await RunComplianceChecker(repository).check("RUN-2042")

    assert result.status == "failed"
    assert result.failed_checks[0].code == "mutation.duplicate_action"
    assert result.failed_checks[0].action_fingerprints == [
        (
            "ticket:EVAL-TCK-CR-003|action:goodwill_credit|target:cred-ledger-eval-cr-003|"
            "amount:12000|currency:USD"
        )
    ]


@pytest.mark.asyncio
async def test_run_compliance_api_returns_result_shape_and_404_for_unknown_run() -> None:
    repository = build_seed_repository()

    async def repository_override():
        return repository

    app.dependency_overrides[get_repository] = repository_override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/agent-runs/RUN-2042/compliance")
            missing = await client.get("/agent-runs/RUN-unknown/compliance")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "passed"
    assert payload["high_risk_gate_count"] == 1
    assert payload["verified_governed_action_count"] == 7
    assert payload["checked_at"]
    assert missing.status_code == 404
