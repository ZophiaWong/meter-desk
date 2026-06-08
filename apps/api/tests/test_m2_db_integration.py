import os

import pytest
from httpx import ASGITransport, AsyncClient

from meterdesk_api.main import app

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
        eval_cases = await client.get("/eval-cases")

    assert tickets.status_code == 200
    assert [ticket["id"] for ticket in tickets.json()] == ["TCK-1042", "TCK-1098", "TCK-1137"]
    assert evidence.status_code == 200
    assert evidence.json()["invoice"]["id"] == "INV-2026-0418"
    assert approvals.status_code == 200
    assert approvals.json()[0]["id"] == "APR-2042"
    assert eval_cases.status_code == 200
    assert len(eval_cases.json()) == 9


@pytest.mark.asyncio
async def test_business_write_placeholders_are_not_registered() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post("/approvals/APR-2042/approve")

    assert response.status_code == 404
