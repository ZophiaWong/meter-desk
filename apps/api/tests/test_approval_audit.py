from collections.abc import Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from api_client import authenticate_demo_client
from meterdesk_api.errors import MeterDeskAPIError
from meterdesk_api.main import app
from meterdesk_api.repositories import get_repository
from meterdesk_api.schemas import ApprovalDecisionActor
from meterdesk_api.seed_data import build_seed_repository


@pytest.fixture(autouse=True)
def isolated_approval_repository() -> Iterator[None]:
    repository = build_seed_repository()

    async def repository_override():
        return repository

    app.dependency_overrides[get_repository] = repository_override
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_approval_decision_rejects_a_caller_supplied_actor() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client, subject="demo-approver")
        forged = await client.post(
            "/approvals/APR-2042/approve",
            json={
                "decided_by": "Forged Finance Director",
                "decision_note": "Caller tried to choose the audit actor.",
            },
        )
        approval = await client.get("/approvals?ticket_id=TCK-1042&status=all")
        mutations = await client.get("/mock-mutations?ticket_id=TCK-1042")

    assert forged.status_code == 422
    assert forged.headers["X-Request-ID"]
    assert approval.json()[0]["status"] == "pending"
    assert approval.json()[0]["decision_actor"] is None
    assert approval.json()[0]["decision_request_id"] is None
    assert mutations.json() == []


@pytest.mark.asyncio
async def test_approve_retry_returns_the_first_authenticated_actor_and_audit() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client, subject="demo-approver")
        first = await client.post(
            "/approvals/APR-2042/approve",
            json={"decision_note": "Evidence confirms the duplicate capture."},
        )

        await authenticate_demo_client(client, subject="demo-admin")
        retry = await client.post(
            "/approvals/APR-2042/approve",
            json={"decision_note": "Admin must not replace the first audit."},
        )
        opposite = await client.post(
            "/approvals/APR-2042/reject",
            json={"decision_note": "Admin must not reverse the terminal decision."},
        )
        mutations = await client.get("/mock-mutations?ticket_id=TCK-1042")

    assert first.status_code == 200
    first_approval = first.json()["approval"]
    assert first_approval["decision_actor"] == {
        "subject": "demo-approver",
        "display_name": "Demo Approver",
        "role": "approver",
        "source": "demo_session",
    }
    assert first_approval["decision_request_id"] == first.headers["X-Request-ID"]
    assert first_approval["decision_note"] == "Evidence confirms the duplicate capture."
    assert "decided_by" not in first_approval

    assert retry.status_code == 200
    retry_approval = retry.json()["approval"]
    assert retry_approval["decision_actor"] == first_approval["decision_actor"]
    assert retry_approval["decision_request_id"] == first_approval["decision_request_id"]
    assert retry_approval["decision_note"] == first_approval["decision_note"]
    assert retry_approval["decided_at"] == first_approval["decided_at"]
    assert retry.headers["X-Request-ID"] != retry_approval["decision_request_id"]
    assert retry.json()["mock_mutation"]["id"] == first.json()["mock_mutation"]["id"]

    assert opposite.status_code == 409
    assert opposite.json()["code"] == "approval.terminal_conflict"
    assert len(mutations.json()) == 1


@pytest.mark.asyncio
async def test_reject_retry_returns_the_first_authenticated_actor_and_audit() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client, subject="demo-approver")
        first = await client.post(
            "/approvals/APR-2042/reject",
            json={"decision_note": "The evidence needs correction."},
        )

        await authenticate_demo_client(client, subject="demo-admin")
        retry = await client.post(
            "/approvals/APR-2042/reject",
            json={"decision_note": "Admin must not replace the first rejection."},
        )
        opposite = await client.post("/approvals/APR-2042/approve", json={})
        mutations = await client.get("/mock-mutations?ticket_id=TCK-1042")

    assert first.status_code == 200
    first_approval = first.json()["approval"]
    assert first_approval["status"] == "rejected"
    assert first_approval["decision_actor"]["subject"] == "demo-approver"
    assert first_approval["decision_request_id"] == first.headers["X-Request-ID"]
    assert first_approval["decision_note"] == "The evidence needs correction."

    assert retry.status_code == 200
    assert retry.json()["approval"] == first_approval
    assert retry.headers["X-Request-ID"] != first_approval["decision_request_id"]
    assert opposite.status_code == 409
    assert mutations.json() == []


@pytest.mark.asyncio
async def test_historical_eval_approval_has_a_deterministic_seed_actor() -> None:
    repository = build_seed_repository()

    approval = await repository.get_approval("APR-EVAL-CR-003-HIST")

    assert approval is not None
    assert approval.decision_actor is not None
    assert approval.decision_actor.model_dump() == {
        "subject": "demo-approver",
        "display_name": "Demo Approver",
        "role": "approver",
        "source": "seed_fixture",
    }
    assert approval.decision_request_id == "req_seed_eval_cr_003_hist"


@pytest.mark.asyncio
async def test_repository_same_direction_retry_cannot_replace_the_first_audit() -> None:
    repository = build_seed_repository()
    first_actor = ApprovalDecisionActor(
        subject="demo-approver",
        display_name="Demo Approver",
        role="approver",
        source="demo_session",
    )
    retry_actor = ApprovalDecisionActor(
        subject="demo-admin",
        display_name="Demo Admin",
        role="admin",
        source="demo_session",
    )

    first, first_mutation = await repository.approve_request(
        approval_id="APR-2042",
        decision_actor=first_actor,
        decision_request_id="req_first_repository_decision",
        decision_note="First audit owns the terminal record.",
    )
    retry, retry_mutation = await repository.approve_request(
        approval_id="APR-2042",
        decision_actor=retry_actor,
        decision_request_id="req_retry_must_not_replace",
        decision_note="This must not replace the first audit.",
    )

    assert retry == first
    assert retry_mutation == first_mutation
    assert retry.decision_actor == first_actor
    assert retry.decision_request_id == "req_first_repository_decision"
    assert retry.decision_note == "First audit owns the terminal record."

    with pytest.raises(MeterDeskAPIError) as conflict:
        await repository.reject_request(
            approval_id="APR-2042",
            decision_actor=retry_actor,
            decision_request_id="req_opposite_repository_decision",
            decision_note=None,
        )

    assert conflict.value.status_code == 409
    assert conflict.value.code == "approval.terminal_conflict"
