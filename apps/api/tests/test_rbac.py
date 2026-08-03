from collections.abc import Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from api_client import authenticate_demo_client
from meterdesk_api.agent.runtime import get_agent_provider, get_optional_agent_provider
from meterdesk_api.errors import MeterDeskAPIError
from meterdesk_api.main import app
from meterdesk_api.repositories import get_repository
from meterdesk_api.seed_data import build_seed_repository


@pytest.fixture(autouse=True)
def isolated_business_dependencies() -> Iterator[None]:
    repository = build_seed_repository()

    async def repository_override():
        return repository

    async def missing_provider_override():
        raise MeterDeskAPIError(
            status_code=503,
            code="provider.not_configured",
            message="OpenAI-compatible provider is not configured.",
        )

    async def optional_provider_override():
        return None

    app.dependency_overrides[get_repository] = repository_override
    app.dependency_overrides[get_agent_provider] = missing_provider_override
    app.dependency_overrides[get_optional_agent_provider] = optional_provider_override
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_only_health_docs_and_demo_login_surfaces_are_public() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        health = await client.get("/health")
        docs = await client.get("/docs")
        openapi = await client.get("/openapi.json")
        identities = await client.get("/auth/demo-identities")
        login = await client.post("/auth/demo-login", json={"subject": "demo-admin"})
        me = await client.get("/auth/me")
        tickets = await client.get("/tickets")
        agent_run = await client.post("/tickets/TCK-1042/agent-runs")
        approval = await client.post("/approvals/APR-2042/approve", json={})
        eval_run = await client.post("/eval-cases/eval-duplicate-charge-002/run")

    assert health.status_code == 200
    assert docs.status_code == 200
    assert openapi.status_code == 200
    assert identities.status_code == 200
    assert login.status_code == 200
    for response in (me, tickets, agent_run, approval, eval_run):
        assert response.status_code == 401
        assert response.json()["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.parametrize(
    ("subject", "agent_status", "approval_status", "eval_status"),
    [
        ("demo-support-operator", 503, 403, 403),
        ("demo-approver", 403, 200, 403),
        ("demo-admin", 503, 200, 201),
    ],
)
@pytest.mark.asyncio
async def test_role_matrix_is_enforced_by_business_routes(
    subject: str,
    agent_status: int,
    approval_status: int,
    eval_status: int,
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client, subject=subject)
        read = await client.get("/tickets")
        agent_run = await client.post("/tickets/TCK-1042/agent-runs")
        approval = await client.post("/approvals/APR-2042/approve", json={})
        eval_run = await client.post("/eval-cases/eval-duplicate-charge-002/run")

    assert read.status_code == 200
    assert agent_run.status_code == agent_status
    assert approval.status_code == approval_status
    assert eval_run.status_code == eval_status

    for permission, response in (
        ("agent.run", agent_run),
        ("approval.decide", approval),
        ("eval.run", eval_run),
    ):
        if response.status_code != 403:
            continue
        assert response.json()["code"] == "auth.forbidden"
        assert response.json()["details"]["required_permission"] == permission
        assert response.json()["request_id"] == response.headers["X-Request-ID"]
