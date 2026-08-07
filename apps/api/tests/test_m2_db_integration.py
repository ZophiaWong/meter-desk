import os
from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from api_client import authenticate_demo_client
from meterdesk_api.agent.runtime import get_agent_provider
from meterdesk_api.db import database_runtime_context
from meterdesk_api.demo_reset_live import reset_live_demo_state
from meterdesk_api.errors import MeterDeskAPIError
from meterdesk_api.main import create_app
from meterdesk_api.models import EvalSuiteRun
from meterdesk_api.repositories import SqlAlchemyMeterDeskRepository
from meterdesk_api.schemas import ApprovalDecisionActor, EvalResultSummary
from meterdesk_api.seed import seed_demo_data
from meterdesk_api.seed_data import utc

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        os.environ.get("METERDESK_RUN_DB_TESTS") != "1",
        reason="Set METERDESK_RUN_DB_TESTS=1 and run against local Postgres.",
    ),
]


@pytest.fixture
async def postgres_app() -> AsyncIterator[FastAPI]:
    test_app = create_app()
    async with test_app.router.lifespan_context(test_app):
        yield test_app


@pytest.mark.asyncio
async def test_seeded_postgres_resources_are_queryable(postgres_app: FastAPI) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=postgres_app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client)
        tickets = await client.get("/tickets")
        evidence = await client.get("/tickets/TCK-1042/billing-evidence")
        credit_refund_evidence = await client.get("/tickets/TCK-1137/billing-evidence")
        approvals = await client.get("/approvals")
        runs = await client.get("/tickets/TCK-1042/agent-runs")
        credit_refund_runs = await client.get("/tickets/TCK-1137/agent-runs")
        eval_cases = await client.get("/eval-cases")

    assert tickets.status_code == 200
    assert [ticket["id"] for ticket in tickets.json()] == ["TCK-1042", "TCK-1098", "TCK-1137"]
    assert evidence.status_code == 200
    assert evidence.json()["invoice"]["id"] == "INV-2026-0418"
    assert credit_refund_evidence.status_code == 200
    assert credit_refund_evidence.json()["subscription"]["id"] == "sub-helio-2026"
    assert credit_refund_evidence.json()["credits"][0]["disputed_amount"]["display"] == "$120.00"
    assert approvals.status_code == 200
    assert [approval["id"] for approval in approvals.json()] == ["APR-2042", "APR-1137"]
    assert runs.status_code == 200
    assert [run["id"] for run in runs.json()] == ["RUN-2042"]
    assert credit_refund_runs.status_code == 200
    assert [run["id"] for run in credit_refund_runs.json()] == ["RUN-1137"]
    assert eval_cases.status_code == 200
    assert len(eval_cases.json()) == 9


@pytest.mark.asyncio
async def test_agent_run_requires_provider_configuration(postgres_app: FastAPI) -> None:
    async def missing_provider_override():
        raise MeterDeskAPIError(
            status_code=503,
            code="provider.not_configured",
            message="OpenAI-compatible provider is not configured.",
        )

    postgres_app.dependency_overrides[get_agent_provider] = missing_provider_override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=postgres_app),
            base_url="http://testserver",
        ) as client:
            await authenticate_demo_client(client)
            response = await client.post("/tickets/TCK-1042/agent-runs")
    finally:
        postgres_app.dependency_overrides.pop(get_agent_provider, None)

    assert response.status_code == 503
    assert response.json()["code"] == "provider.not_configured"


@pytest.mark.asyncio
async def test_postgres_api_preserves_auth_decision_and_idempotency_contract(
    postgres_app: FastAPI,
) -> None:
    await seed_demo_data()

    async with AsyncClient(
        transport=ASGITransport(app=postgres_app),
        base_url="http://testserver",
    ) as client:
        anonymous_tickets = await client.get("/tickets")

        await authenticate_demo_client(client, subject="demo-support-operator")
        operator_approval = await client.post("/approvals/APR-2042/approve", json={})

        await authenticate_demo_client(client, subject="demo-approver")
        decision = await client.post(
            "/approvals/APR-2042/approve",
            json={"decision_note": "Approved by the Postgres integration test."},
        )
        mutations = await client.get("/mock-mutations?ticket_id=TCK-1042")
        credit_mutations_before = await client.get("/mock-mutations?ticket_id=TCK-1137")
        rejection = await client.post(
            "/approvals/APR-1137/reject",
            json={"decision_note": "Rejected by the Postgres integration test."},
        )
        credit_mutations_after = await client.get("/mock-mutations?ticket_id=TCK-1137")
        historical_approval = await client.get("/approvals?ticket_id=EVAL-TCK-CR-003&status=all")

        await authenticate_demo_client(client, subject="demo-admin")
        retry = await client.post(
            "/approvals/APR-2042/approve",
            json={"decision_note": "This retry must not replace the approver audit."},
        )
        mutations_after_retry = await client.get("/mock-mutations?ticket_id=TCK-1042")

    assert anonymous_tickets.status_code == 401
    assert operator_approval.status_code == 403
    assert operator_approval.json()["code"] == "auth.forbidden"

    assert decision.status_code == 200
    decided_approval = decision.json()["approval"]
    assert decided_approval["decision_actor"] == {
        "subject": "demo-approver",
        "display_name": "Demo Approver",
        "role": "approver",
        "source": "demo_session",
    }
    assert decided_approval["decision_request_id"] == decision.headers["X-Request-ID"]
    assert len(mutations.json()) == 1
    assert mutations.json()[0]["approval_request_id"] == "APR-2042"

    assert rejection.status_code == 200
    rejected_approval = rejection.json()["approval"]
    assert rejected_approval["status"] == "rejected"
    assert rejected_approval["decision_actor"]["subject"] == "demo-approver"
    assert rejected_approval["decision_request_id"] == rejection.headers["X-Request-ID"]
    assert credit_mutations_after.json() == credit_mutations_before.json()

    seeded_actor = historical_approval.json()[0]
    assert seeded_actor["decision_actor"]["subject"] == "demo-approver"
    assert seeded_actor["decision_actor"]["source"] == "seed_fixture"
    assert seeded_actor["decision_request_id"] == "req_seed_eval_cr_003_hist"

    assert retry.status_code == 200
    assert retry.json()["approval"] == decided_approval
    assert retry.json()["mock_mutation"]["id"] == decision.json()["mock_mutation"]["id"]
    assert len(mutations_after_retry.json()) == 1


@pytest.mark.asyncio
async def test_seed_restores_m5_portfolio_baseline_for_demo_tickets(
    postgres_app: FastAPI,
) -> None:
    await seed_demo_data()

    async with database_runtime_context() as runtime:
        async with runtime.session_factory() as session:
            repository = SqlAlchemyMeterDeskRepository(session)
            await repository.reset_demo_live_state("TCK-1042")
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
            await repository.finalize_run(
                agent_run_id=run.id,
                final_outcome="confirmed_duplicate_charge",
                internal_resolution="Duplicate captured charge for INV-2026-0418.",
                customer_reply="Draft only.",
                target_status="awaiting_approval",
                reason_code="test.db_seed_reset_approval_required",
                approval={
                    "title": "Database reset proof pending approval",
                    "action_type": "db_test_refund",
                    "amount_cents": 29000,
                    "amount_display": "$290.00",
                    "currency": "USD",
                    "reason": "Duplicate captured charge for INV-2026-0418.",
                    "blocker": "Mutation blocked until human approval",
                    "policy_citation": "DUP-CHARGE-001 v2026.04",
                    "evidence_refs": ["invoice INV-2026-0418", "charge ch_2026_0418_B"],
                    "action_metadata": {"target_charge_id": "ch_2026_0418_B"},
                },
            )
            approval = (await repository.list_approvals(ticket_id="TCK-1042"))[-1]
            await repository.approve_request(
                approval_id=approval.id,
                decision_actor=ApprovalDecisionActor(
                    subject="demo-admin",
                    display_name="Demo Admin",
                    role="admin",
                    source="demo_session",
                ),
                decision_request_id="req_db_test_seed_reset",
                decision_note="Approved to verify seed reset.",
            )

    await seed_demo_data()

    async with AsyncClient(
        transport=ASGITransport(app=postgres_app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client)
        tickets = await client.get("/tickets")
        runs = await client.get("/tickets/TCK-1042/agent-runs")
        approvals = await client.get("/approvals?ticket_id=TCK-1042&status=all")
        pending_approvals = await client.get("/approvals")
        mutations = await client.get("/mock-mutations?ticket_id=TCK-1042")

    assert tickets.status_code == 200
    assert [ticket["id"] for ticket in tickets.json()] == ["TCK-1042", "TCK-1098", "TCK-1137"]
    assert runs.status_code == 200
    assert [run["id"] for run in runs.json()] == ["RUN-2042"]
    assert runs.json()[0]["status"] == "completed"
    assert approvals.status_code == 200
    assert [approval["id"] for approval in approvals.json()] == ["APR-2042"]
    assert approvals.json()[0]["status"] == "pending"
    assert pending_approvals.status_code == 200
    assert [approval["id"] for approval in pending_approvals.json()] == ["APR-2042", "APR-1137"]
    assert mutations.status_code == 200
    assert mutations.json() == []


@pytest.mark.asyncio
async def test_reset_eval_fixture_state_removes_postgres_results_linked_to_fixture_runs() -> None:
    await seed_demo_data()

    async with database_runtime_context() as runtime:
        async with runtime.session_factory() as session:
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


@pytest.mark.asyncio
async def test_seed_removes_eval_suite_runs_linked_to_seeded_cases() -> None:
    await seed_demo_data()

    async with database_runtime_context() as runtime:
        async with runtime.session_factory() as session:
            async with session.begin():
                session.add(
                    EvalSuiteRun(
                        id="EVRUN-db-test-seeded-case",
                        run_type="case",
                        status="completed",
                        summary="Previous ad-hoc eval case run.",
                        baseline_name=None,
                        case_id="eval-duplicate-charge-002",
                        started_at=utc(2026, 6, 30, 10, 0),
                        completed_at=utc(2026, 6, 30, 10, 1),
                        seed_marker=None,
                    )
                )

        await seed_demo_data()

        async with runtime.session_factory() as session:
            remaining_runs = (
                await session.execute(
                    select(EvalSuiteRun.id).where(EvalSuiteRun.id == "EVRUN-db-test-seeded-case")
                )
            ).scalars()

        assert list(remaining_runs) == []


@pytest.mark.asyncio
async def test_demo_reset_live_clears_only_duplicate_charge_runtime_rows(
    postgres_app: FastAPI,
) -> None:
    await seed_demo_data()
    await reset_live_demo_state()

    async with AsyncClient(
        transport=ASGITransport(app=postgres_app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client)
        evidence = await client.get("/tickets/TCK-1042/billing-evidence")
        runs = await client.get("/tickets/TCK-1042/agent-runs")
        approvals = await client.get("/approvals?ticket_id=TCK-1042&status=all")
        mutations = await client.get("/mock-mutations?ticket_id=TCK-1042")
        eval_cases = await client.get("/eval-cases")
        credit_runs = await client.get("/tickets/TCK-1137/agent-runs")
        credit_approvals = await client.get("/approvals?ticket_id=TCK-1137&status=all")
        credit_mutations = await client.get("/mock-mutations?ticket_id=TCK-1137")

    assert evidence.status_code == 200
    assert evidence.json()["invoice"]["id"] == "INV-2026-0418"
    assert runs.status_code == 200
    assert runs.json() == []
    assert approvals.status_code == 200
    assert approvals.json() == []
    assert mutations.status_code == 200
    assert mutations.json() == []
    assert eval_cases.status_code == 200
    assert len(eval_cases.json()) == 9
    assert credit_runs.status_code == 200
    assert [run["id"] for run in credit_runs.json()] == ["RUN-1137"]
    assert credit_approvals.status_code == 200
    assert [approval["id"] for approval in credit_approvals.json()] == ["APR-1137"]
    assert credit_mutations.status_code == 200
    assert credit_mutations.json() == []
