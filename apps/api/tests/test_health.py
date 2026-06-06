import pytest
from httpx import ASGITransport, AsyncClient

from meterdesk_api.main import app


@pytest.mark.asyncio
async def test_health_returns_api_liveness() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "meterdesk-api",
        "status": "ok",
        "environment": "development",
    }


@pytest.mark.asyncio
async def test_db_health_reports_reachable_database(monkeypatch) -> None:
    async def reachable_database() -> None:
        return None

    monkeypatch.setattr("meterdesk_api.routers.health.check_database", reachable_database)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {
        "service": "meterdesk-api",
        "status": "ok",
        "database": "reachable",
    }


@pytest.mark.asyncio
async def test_db_health_reports_unreachable_database(monkeypatch) -> None:
    async def unreachable_database() -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("meterdesk_api.routers.health.check_database", unreachable_database)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {
        "service": "meterdesk-api",
        "status": "error",
        "database": "unreachable",
        "detail": "RuntimeError",
    }
