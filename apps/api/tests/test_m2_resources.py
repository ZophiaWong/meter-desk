import pytest
from httpx import ASGITransport, AsyncClient

from meterdesk_api.main import app
from meterdesk_api.repositories import get_repository
from meterdesk_api.seed_data import build_seed_repository


@pytest.fixture(autouse=True)
def seeded_repository_override():
    async def repository_override():
        return build_seed_repository()

    app.dependency_overrides[get_repository] = repository_override
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
    assert runs_response.json()[0]["id"] == "RUN-2042"
    assert runs_response.json()[0]["internal_resolution"]


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
async def test_governance_eval_and_deferred_write_contracts() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        approvals_response = await client.get("/approvals")
        traces_response = await client.get("/agent-runs/RUN-2042/traces")
        eval_cases_response = await client.get("/eval-cases")
        eval_results_response = await client.get("/eval-results")
        write_response = await client.post("/approvals/APR-2042/approve")

    assert approvals_response.status_code == 200
    approvals = approvals_response.json()
    assert approvals == [
        {
            "id": "APR-2042",
            "ticket_id": "TCK-1042",
            "title": "Original refund pending approval",
            "status": "pending",
            "amount": {"amount_cents": 124800, "currency": "USD", "display": "$1,248.00"},
            "reason": (
                "Refund the second captured charge ch_2026_0418_B to the original payment method."
            ),
            "policy_citation": "REFUND-DUP-001 v2026.02",
            "blocker": "Mutation blocked until human approval",
        }
    ]

    assert traces_response.status_code == 200
    trace_categories = [trace["category"] for trace in traces_response.json()]
    assert trace_categories == [
        "read.billing_evidence",
        "decision.refund_eligibility",
        "draft.customer_reply",
    ]

    assert eval_cases_response.status_code == 200
    cases = eval_cases_response.json()
    assert len(cases) == 9
    assert {case["scenario"] for case in cases} == {
        "duplicate_charge",
        "usage_spike",
        "credit_refund_dispute",
    }

    assert eval_results_response.status_code == 200
    results = eval_results_response.json()
    assert results == [
        {
            "id": "EVR-DUP-001-M2",
            "case_id": "eval-duplicate-charge-001",
            "agent_run_id": "RUN-2042",
            "status": "preview",
            "summary": "Static M2 preview from seeded Duplicate Charge trace.",
            "dimension_scores": {
                "approval_routing": "pass",
                "draft_quality": "preview",
                "outcome_correctness": "pass",
                "policy_compliance": "pass",
                "required_evidence": "pass",
            },
        }
    ]

    assert write_response.status_code == 404
