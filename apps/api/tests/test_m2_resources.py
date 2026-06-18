import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from meterdesk_api.agent.runtime import get_agent_provider
from meterdesk_api.main import app
from meterdesk_api.repositories import get_repository
from meterdesk_api.seed_data import build_seed_repository


@pytest.fixture(autouse=True)
def seeded_repository_override():
    async def repository_override():
        return build_seed_repository()

    async def missing_provider_override():
        raise HTTPException(
            status_code=503,
            detail="OpenAI-compatible provider is not configured",
        )

    app.dependency_overrides[get_repository] = repository_override
    app.dependency_overrides[get_agent_provider] = missing_provider_override
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ticket_resources_return_seeded_duplicate_charge_contract() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        list_response = await client.get("/tickets")
        detail_response = await client.get("/tickets/TCK-1042")
        evidence_response = await client.get("/tickets/TCK-1042/billing-evidence")
        runs_response = await client.get("/tickets/TCK-1042/agent-runs")
        approvals_response = await client.get("/approvals?ticket_id=TCK-1042&status=all")
        mutations_response = await client.get("/mock-mutations?ticket_id=TCK-1042")

    assert list_response.status_code == 200
    ticket_ids = [ticket["id"] for ticket in list_response.json()]
    assert ticket_ids == ["TCK-1042", "TCK-1098", "TCK-1137"]

    assert detail_response.status_code == 200
    assert detail_response.json()["scenario"] == "duplicate_charge"
    assert detail_response.json()["customer"]["name"] == "Northstar Compute"

    assert evidence_response.status_code == 200
    evidence = evidence_response.json()
    assert evidence["invoice"]["id"] == "INV-2026-0418"
    assert evidence["invoice"]["total"]["amount_cents"] == 124800
    assert [charge["id"] for charge in evidence["charges"]] == [
        "ch_2026_0418_A",
        "ch_2026_0418_B",
    ]
    assert evidence["policy"]["id"] == "REFUND-DUP-001"

    assert runs_response.status_code == 200
    runs = runs_response.json()
    assert [run["id"] for run in runs] == ["RUN-2042"]
    assert runs[0]["status"] == "completed"
    assert runs[0]["final_outcome"] == "confirmed_duplicate_charge"
    assert runs[0]["internal_resolution"]
    assert runs[0]["customer_reply"]

    assert approvals_response.status_code == 200
    approvals = approvals_response.json()
    assert [approval["id"] for approval in approvals] == ["APR-2042"]
    assert approvals[0]["status"] == "pending"
    assert approvals[0]["agent_run_id"] == "RUN-2042"

    assert mutations_response.status_code == 200
    assert mutations_response.json() == []


@pytest.mark.asyncio
async def test_missing_resource_returns_404_and_empty_collections_return_arrays() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        missing_ticket = await client.get("/tickets/TCK-0000")
        missing_traces = await client.get("/agent-runs/RUN-0000/traces")
        mutations = await client.get("/mock-mutations")

    assert missing_ticket.status_code == 404
    assert missing_traces.status_code == 404
    assert mutations.status_code == 200
    assert isinstance(mutations.json(), list)


@pytest.mark.asyncio
async def test_m5_seed_starts_with_portfolio_baseline_governance_artifacts() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        approvals_response = await client.get("/approvals")
        traces_response = await client.get("/agent-runs/RUN-2042/traces")
        eval_cases_response = await client.get("/eval-cases")
        eval_results_response = await client.get("/eval-results")
        write_response = await client.post("/tickets/TCK-1042/agent-runs")

    assert approvals_response.status_code == 200
    assert [approval["id"] for approval in approvals_response.json()] == ["APR-2042"]

    assert traces_response.status_code == 200
    traces = traces_response.json()
    assert [trace["category"] for trace in traces] == [
        "read.billing_evidence",
        "read.prior_financial_actions",
        "decision.refund_eligibility",
        "draft.resolution",
        "approval.create_request",
    ]
    assert traces[-1]["approval_refs"] == ["APR-2042"]

    assert eval_cases_response.status_code == 200
    cases = eval_cases_response.json()
    assert len(cases) == 9
    assert {case["scenario"] for case in cases} == {
        "duplicate_charge",
        "usage_spike",
        "credit_refund_dispute",
    }

    assert eval_results_response.status_code == 200
    assert eval_results_response.json() == []

    assert write_response.status_code == 503
    assert write_response.json()["detail"] == "OpenAI-compatible provider is not configured"
