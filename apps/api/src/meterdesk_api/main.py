from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from meterdesk_api.routers.health import router as health_router
from meterdesk_api.routers.resources import router as resources_router
from meterdesk_api.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="MeterDesk API",
        summary="Internal API scaffold for MeterDesk.",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(resources_router)
    return app


app = create_app()
