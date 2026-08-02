from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from meterdesk_api.errors import MeterDeskAPIError
from meterdesk_api.routers.auth import router as auth_router
from meterdesk_api.routers.health import router as health_router
from meterdesk_api.routers.resources import router as resources_router
from meterdesk_api.settings import get_settings


async def meterdesk_api_error_handler(
    request: Request,
    error: MeterDeskAPIError,
) -> JSONResponse:
    request_id = request.state.request_id
    return JSONResponse(
        status_code=error.status_code,
        content=error.body(request_id=request_id),
        headers={**error.headers, "X-Request-ID": request_id},
    )


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

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = f"req_{uuid4()}"
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    app.add_exception_handler(MeterDeskAPIError, meterdesk_api_error_handler)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(resources_router)
    return app


app = create_app()
