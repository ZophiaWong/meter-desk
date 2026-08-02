from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from meterdesk_api.auth import (
    DEMO_PRINCIPALS,
    AuthenticatedPrincipal,
    DemoPrincipal,
    issue_demo_token,
    resolve_demo_principal,
)
from meterdesk_api.errors import MeterDeskAPIError
from meterdesk_api.settings import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["demo authentication"])


class DemoLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str


class DemoLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    principal: DemoPrincipal


@router.get("/demo-identities", response_model=list[DemoPrincipal])
async def list_demo_identities() -> list[DemoPrincipal]:
    return list(DEMO_PRINCIPALS)


@router.post("/demo-login", response_model=DemoLoginResponse)
async def demo_login(
    login: DemoLoginRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> DemoLoginResponse:
    principal = resolve_demo_principal(login.subject)
    if principal is None:
        raise MeterDeskAPIError(
            status_code=422,
            code="auth.unknown_demo_subject",
            message="Unknown demo identity.",
            details={"subject": login.subject},
        )
    return DemoLoginResponse(
        access_token=issue_demo_token(principal, settings),
        expires_in=settings.demo_auth_token_ttl_seconds,
        principal=principal,
    )


@router.get("/me", response_model=DemoPrincipal)
async def get_current_demo_principal(principal: AuthenticatedPrincipal) -> DemoPrincipal:
    return principal
