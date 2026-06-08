import asyncio

from httpx import ASGITransport, AsyncClient

from meterdesk_api.main import app


async def run_db_integration_check() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        tickets = await client.get("/tickets")
        evidence = await client.get("/tickets/TCK-1042/billing-evidence")
        approvals = await client.get("/approvals")
        eval_cases = await client.get("/eval-cases")
        write = await client.post("/approvals/APR-2042/approve")

    assert tickets.status_code == 200
    assert [ticket["id"] for ticket in tickets.json()] == ["TCK-1042", "TCK-1098", "TCK-1137"]
    assert evidence.status_code == 200
    assert evidence.json()["invoice"]["id"] == "INV-2026-0418"
    assert approvals.status_code == 200
    assert approvals.json()[0]["id"] == "APR-2042"
    assert eval_cases.status_code == 200
    assert len(eval_cases.json()) == 9
    assert write.status_code == 404

    print("MeterDesk M2 DB integration check passed.")


def main() -> None:
    asyncio.run(run_db_integration_check())


if __name__ == "__main__":
    main()
