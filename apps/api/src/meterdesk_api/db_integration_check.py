import asyncio

from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from meterdesk_api.agent.runtime import get_agent_provider
from meterdesk_api.main import app


async def run_db_integration_check() -> None:
    async def missing_provider_override():
        raise HTTPException(
            status_code=503,
            detail="OpenAI-compatible provider is not configured",
        )

    app.dependency_overrides[get_agent_provider] = missing_provider_override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            tickets = await client.get("/tickets")
            evidence = await client.get("/tickets/TCK-1042/billing-evidence")
            approvals = await client.get("/approvals")
            runs = await client.get("/tickets/TCK-1042/agent-runs")
            eval_cases = await client.get("/eval-cases")
            write = await client.post("/tickets/TCK-1042/agent-runs")
    finally:
        app.dependency_overrides.pop(get_agent_provider, None)

    assert tickets.status_code == 200
    assert [ticket["id"] for ticket in tickets.json()] == ["TCK-1042", "TCK-1098", "TCK-1137"]
    assert evidence.status_code == 200
    assert evidence.json()["invoice"]["id"] == "INV-2026-0418"
    assert approvals.status_code == 200
    assert [approval["id"] for approval in approvals.json()] == ["APR-2042"]
    assert runs.status_code == 200
    assert [run["id"] for run in runs.json()] == ["RUN-2042"]
    assert eval_cases.status_code == 200
    assert len(eval_cases.json()) == 9
    assert write.status_code == 503
    assert write.json()["detail"] == "OpenAI-compatible provider is not configured"

    print("MeterDesk M5 DB integration check passed.")


def main() -> None:
    asyncio.run(run_db_integration_check())


if __name__ == "__main__":
    main()
