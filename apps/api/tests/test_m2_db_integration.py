import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from meterdesk_api.db import create_engine
from meterdesk_api.main import app
from meterdesk_api.repositories import SqlAlchemyMeterDeskRepository
from meterdesk_api.schemas import EvalResultSummary
from meterdesk_api.seed import seed_demo_data

pytestmark = pytest.mark.skipif(
    os.environ.get("METERDESK_RUN_DB_TESTS") != "1",
    reason="Set METERDESK_RUN_DB_TESTS=1 and run against local Postgres.",
)


@pytest.mark.asyncio
async def test_seeded_postgres_resources_are_queryable() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        tickets = await client.get("/tickets")
        evidence = await client.get("/tickets/TCK-1042/billing-evidence")
        approvals = await client.get("/approvals")
        runs = await client.get("/tickets/TCK-1042/agent-runs")
        eval_cases = await client.get("/eval-cases")

    assert tickets.status_code == 200
    assert [ticket["id"] for ticket in tickets.json()] == ["TCK-1042", "TCK-1098", "TCK-1137"]
    assert evidence.status_code == 200
    assert evidence.json()["invoice"]["id"] == "INV-2026-0418"
    assert approvals.status_code == 200
    assert approvals.json() == []
    assert runs.status_code == 200
    assert runs.json() == []
    assert eval_cases.status_code == 200
    assert len(eval_cases.json()) == 9


@pytest.mark.asyncio
async def test_agent_run_requires_provider_configuration() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post("/tickets/TCK-1042/agent-runs")

    assert response.status_code == 503
    assert response.json()["detail"] == "OpenAI-compatible provider is not configured"


@pytest.mark.asyncio
async def test_seed_resets_m3_runtime_rows_for_demo_tickets() -> None:
    await seed_demo_data()
    engine = create_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            repository = SqlAlchemyMeterDeskRepository(session)
            run = await repository.create_agent_run(
                ticket_id="TCK-1042",
                source="db-test",
                model="fake-m3-model",
                prompt_version="m3-duplicate-charge-v1",
            )
            await repository.add_tool_trace(
                agent_run_id=run.id,
                category="read.billing_evidence",
                risk="Low",
                label="Read demo billing evidence",
                input_summary="Read evidence for TCK-1042.",
                output_summary="Found duplicate captured charge.",
                evidence_refs=["invoice INV-2026-0418"],
                policy_refs=[],
                approval_refs=[],
            )
            approval = await repository.create_approval_request(
                ticket_id="TCK-1042",
                agent_run_id=run.id,
                title="Original refund pending approval",
                action_type="original_refund",
                amount_cents=29000,
                amount_display="$290.00",
                currency="USD",
                reason="Duplicate captured charge for INV-2026-0418.",
                blocker="Mutation blocked until human approval",
                policy_citation="DUP-CHARGE-001 v2026.04",
                evidence_refs=["invoice INV-2026-0418", "charge ch_2026_0418_B"],
                action_metadata={"target_charge_id": "ch_2026_0418_B"},
            )
            await repository.approve_request(
                approval_id=approval.id,
                decided_by="DB Test",
                decision_note="Approved to verify seed reset.",
            )
    finally:
        await engine.dispose()

    await seed_demo_data()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        tickets = await client.get("/tickets")
        runs = await client.get("/tickets/TCK-1042/agent-runs")
        approvals = await client.get("/approvals?ticket_id=TCK-1042&status=all")
        pending_approvals = await client.get("/approvals")
        mutations = await client.get("/mock-mutations?ticket_id=TCK-1042")

    assert tickets.status_code == 200
    assert [ticket["id"] for ticket in tickets.json()] == ["TCK-1042", "TCK-1098", "TCK-1137"]
    assert runs.status_code == 200
    assert runs.json() == []
    assert approvals.status_code == 200
    assert approvals.json() == []
    assert pending_approvals.status_code == 200
    assert pending_approvals.json() == []
    assert mutations.status_code == 200
    assert mutations.json() == []


@pytest.mark.asyncio
async def test_reset_eval_fixture_state_removes_postgres_results_linked_to_fixture_runs() -> None:
    await seed_demo_data()
    engine = create_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            repository = SqlAlchemyMeterDeskRepository(session)
            run = await repository.create_agent_run(
                ticket_id="EVAL-TCK-DUP-001",
                source="db-test",
                model="fake-eval-model",
                prompt_version="m4-eval-v1",
            )
            await repository.replace_eval_result(
                EvalResultSummary(
                    id="EVR-db-test",
                    case_id="eval-duplicate-charge-001",
                    agent_run_id=run.id,
                    status="passed",
                    summary="Previous eval result.",
                    dimension_scores={},
                    details={},
                )
            )

            await repository.reset_eval_fixture_state("EVAL-TCK-DUP-001")

            runs = await repository.list_agent_runs("EVAL-TCK-DUP-001")
            results = await repository.list_eval_results()
            assert runs == []
            assert results == []
    finally:
        await engine.dispose()
