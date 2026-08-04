from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from meterdesk_api.db import DatabaseRuntime, check_database, get_database_runtime
from meterdesk_api.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "service": "meterdesk-api",
        "status": "ok",
        "environment": settings.environment,
    }


@router.get("/health/db", response_model=None)
async def database_health(
    runtime: Annotated[DatabaseRuntime, Depends(get_database_runtime)],
):
    try:
        await check_database(runtime)
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "service": "meterdesk-api",
                "status": "error",
                "database": "unreachable",
                "detail": type(exc).__name__,
            },
        )

    return {
        "service": "meterdesk-api",
        "status": "ok",
        "database": "reachable",
    }
