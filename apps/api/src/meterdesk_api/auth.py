from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated
from uuid import uuid4

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from pydantic import BaseModel, ConfigDict

from meterdesk_api.errors import MeterDeskAPIError
from meterdesk_api.settings import Settings, get_settings

DEMO_AUTH_ISSUER = "meterdesk-demo-auth"
DEMO_AUTH_AUDIENCE = "meterdesk-api"
DEMO_AUTH_ALGORITHM = "HS256"
REQUIRED_TOKEN_CLAIMS = ("iss", "aud", "sub", "iat", "exp", "jti")


class DemoRole(StrEnum):
    SUPPORT_OPERATOR = "support_operator"
    APPROVER = "approver"
    ADMIN = "admin"


class Permission(StrEnum):
    READ = "business.read"
    AGENT_RUN = "agent.run"
    WORKFLOW_CANCEL = "workflow.cancel"
    APPROVAL_DECIDE = "approval.decide"
    EVAL_RUN = "eval.run"


class DemoPrincipal(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: str
    display_name: str
    role: DemoRole


DEMO_PRINCIPALS = (
    DemoPrincipal(
        subject="demo-support-operator",
        display_name="Demo Support Operator",
        role=DemoRole.SUPPORT_OPERATOR,
    ),
    DemoPrincipal(
        subject="demo-approver",
        display_name="Demo Approver",
        role=DemoRole.APPROVER,
    ),
    DemoPrincipal(
        subject="demo-admin",
        display_name="Demo Admin",
        role=DemoRole.ADMIN,
    ),
)
DEMO_PRINCIPAL_BY_SUBJECT = {principal.subject: principal for principal in DEMO_PRINCIPALS}
ROLE_PERMISSIONS = {
    DemoRole.SUPPORT_OPERATOR: frozenset(
        {Permission.READ, Permission.AGENT_RUN, Permission.WORKFLOW_CANCEL}
    ),
    DemoRole.APPROVER: frozenset({Permission.READ, Permission.APPROVAL_DECIDE}),
    DemoRole.ADMIN: frozenset(Permission),
}

bearer_scheme = HTTPBearer(auto_error=False)


def resolve_demo_principal(subject: str) -> DemoPrincipal | None:
    return DEMO_PRINCIPAL_BY_SUBJECT.get(subject)


def issue_demo_token(
    principal: DemoPrincipal,
    settings: Settings,
    *,
    issued_at: datetime | None = None,
) -> str:
    now = issued_at or datetime.now(UTC)
    issued_at_timestamp = int(now.timestamp())
    payload = {
        "iss": DEMO_AUTH_ISSUER,
        "aud": DEMO_AUTH_AUDIENCE,
        "sub": principal.subject,
        "iat": issued_at_timestamp,
        "exp": issued_at_timestamp + settings.demo_auth_token_ttl_seconds,
        "jti": str(uuid4()),
    }
    return jwt.encode(
        payload,
        settings.demo_auth_signing_key,
        algorithm=DEMO_AUTH_ALGORITHM,
    )


def _authentication_error(*, missing: bool = False) -> MeterDeskAPIError:
    return MeterDeskAPIError(
        status_code=401,
        code="auth.authentication_required" if missing else "auth.invalid_token",
        message="Authentication is required." if missing else "Authentication token is invalid.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_demo_token(token: str, settings: Settings) -> DemoPrincipal:
    try:
        payload = jwt.decode(
            token,
            settings.demo_auth_signing_key,
            algorithms=[DEMO_AUTH_ALGORITHM],
            audience=DEMO_AUTH_AUDIENCE,
            issuer=DEMO_AUTH_ISSUER,
            options={"require": list(REQUIRED_TOKEN_CLAIMS)},
        )
    except InvalidTokenError as error:
        raise _authentication_error() from error

    subject = payload.get("sub")
    principal = resolve_demo_principal(subject) if isinstance(subject, str) else None
    if principal is None:
        raise _authentication_error()
    return principal


async def get_authenticated_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DemoPrincipal:
    if credentials is None:
        raise _authentication_error(missing=True)
    return verify_demo_token(credentials.credentials, settings)


AuthenticatedPrincipal = Annotated[DemoPrincipal, Depends(get_authenticated_principal)]


def enforce_permission(principal: DemoPrincipal, permission: Permission) -> DemoPrincipal:
    if permission not in ROLE_PERMISSIONS[principal.role]:
        raise MeterDeskAPIError(
            status_code=403,
            code="auth.forbidden",
            message="The current identity does not have the required permission.",
            details={
                "required_permission": permission,
                "role": principal.role,
            },
        )
    return principal


async def require_agent_run(principal: AuthenticatedPrincipal) -> DemoPrincipal:
    return enforce_permission(principal, Permission.AGENT_RUN)


async def require_approval_decision(principal: AuthenticatedPrincipal) -> DemoPrincipal:
    return enforce_permission(principal, Permission.APPROVAL_DECIDE)


async def require_workflow_cancel(principal: AuthenticatedPrincipal) -> DemoPrincipal:
    return enforce_permission(principal, Permission.WORKFLOW_CANCEL)


async def require_eval_run(principal: AuthenticatedPrincipal) -> DemoPrincipal:
    return enforce_permission(principal, Permission.EVAL_RUN)
