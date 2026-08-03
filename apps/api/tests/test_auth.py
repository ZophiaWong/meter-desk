import base64
import hashlib
import hmac
import json
import re
import time
from collections.abc import Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from meterdesk_api.main import app, create_app
from meterdesk_api.settings import get_settings

TEST_SIGNING_KEY = "test-only-meterdesk-demo-signing-key-at-least-32-bytes"
REQUEST_ID_PATTERN = re.compile(
    r"^req_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


@pytest.fixture(autouse=True)
def isolated_demo_auth_settings(monkeypatch) -> Iterator[None]:
    monkeypatch.setenv("DEMO_AUTH_SIGNING_KEY", TEST_SIGNING_KEY)
    monkeypatch.setenv("DEMO_AUTH_TOKEN_TTL_SECONDS", "28800")
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _signed_token(payload: dict[str, object]) -> str:
    header_segment = _base64url(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    payload_segment = _base64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_segment}.{payload_segment}"
    signature = hmac.new(
        TEST_SIGNING_KEY.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_base64url(signature)}"


def _decode_unverified_segment(segment: str) -> dict[str, object]:
    padding = "=" * (-len(segment) % 4)
    return json.loads(base64.urlsafe_b64decode(f"{segment}{padding}"))


def _valid_claims(**overrides: object) -> dict[str, object]:
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": "meterdesk-demo-auth",
        "aud": "meterdesk-api",
        "sub": "demo-support-operator",
        "iat": now,
        "exp": now + 28800,
        "jti": "test-jti",
    }
    claims.update(overrides)
    return claims


@pytest.mark.asyncio
async def test_demo_identity_registry_is_public_and_every_response_has_a_unique_request_id() -> (
    None
):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        identities = await client.get("/auth/demo-identities")
        health = await client.get("/health")

    assert identities.status_code == 200
    assert identities.json() == [
        {
            "subject": "demo-support-operator",
            "display_name": "Demo Support Operator",
            "role": "support_operator",
        },
        {
            "subject": "demo-approver",
            "display_name": "Demo Approver",
            "role": "approver",
        },
        {
            "subject": "demo-admin",
            "display_name": "Demo Admin",
            "role": "admin",
        },
    ]
    identity_request_id = identities.headers["X-Request-ID"]
    health_request_id = health.headers["X-Request-ID"]
    assert REQUEST_ID_PATTERN.fullmatch(identity_request_id)
    assert REQUEST_ID_PATTERN.fullmatch(health_request_id)
    assert identity_request_id != health_request_id


@pytest.mark.asyncio
async def test_unhandled_error_returns_a_structured_request_id() -> None:
    test_app = create_app()

    @test_app.get("/_test/unhandled")
    async def raise_unhandled_error() -> None:
        raise RuntimeError("deliberate test failure")

    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/_test/unhandled")

    request_id = response.headers["X-Request-ID"]
    assert response.status_code == 500
    assert REQUEST_ID_PATTERN.fullmatch(request_id)
    assert response.json() == {
        "code": "api.internal_error",
        "message": "Unexpected internal server error.",
        "details": {},
        "request_id": request_id,
    }


@pytest.mark.asyncio
async def test_demo_login_issues_fixed_claims_without_role_and_me_resolves_server_principal() -> (
    None
):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        login = await client.post(
            "/auth/demo-login",
            json={"subject": "demo-support-operator"},
        )
        token = login.json()["access_token"]
        me = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["expires_in"] == 28800
    assert login.json()["principal"] == {
        "subject": "demo-support-operator",
        "display_name": "Demo Support Operator",
        "role": "support_operator",
    }

    header_segment, payload_segment, _ = token.split(".")
    assert _decode_unverified_segment(header_segment) == {"alg": "HS256", "typ": "JWT"}
    claims = _decode_unverified_segment(payload_segment)
    assert claims["iss"] == "meterdesk-demo-auth"
    assert claims["aud"] == "meterdesk-api"
    assert claims["sub"] == "demo-support-operator"
    assert claims["exp"] - claims["iat"] == 28800
    assert isinstance(claims["jti"], str) and claims["jti"]
    assert "role" not in claims
    assert "display_name" not in claims

    assert me.status_code == 200
    assert me.json() == login.json()["principal"]


@pytest.mark.asyncio
async def test_auth_me_rejects_missing_credentials_with_bearer_challenge() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/auth/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    request_id = response.headers["X-Request-ID"]
    assert response.json() == {
        "code": "auth.authentication_required",
        "message": "Authentication is required.",
        "details": {},
        "request_id": request_id,
    }


@pytest.mark.parametrize(
    "token",
    [
        _signed_token(_valid_claims(exp=int(time.time()) - 1)),
        _signed_token(_valid_claims(iss="not-meterdesk")),
        _signed_token(_valid_claims(aud="not-meterdesk-api")),
        _signed_token(_valid_claims(sub="unknown-demo-subject")),
        _signed_token({key: value for key, value in _valid_claims().items() if key != "jti"}),
    ],
    ids=["expired", "wrong-issuer", "wrong-audience", "unknown-subject", "missing-claim"],
)
@pytest.mark.asyncio
async def test_auth_me_rejects_invalid_signed_tokens(token: str) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["code"] == "auth.invalid_token"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_auth_me_rejects_a_token_with_a_forged_signature() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        login = await client.post("/auth/demo-login", json={"subject": "demo-admin"})
        token = login.json()["access_token"]
        header, payload, signature = token.split(".")
        forged_first_character = "A" if signature[0] != "A" else "B"
        forged = f"{header}.{payload}.{forged_first_character}{signature[1:]}"
        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {forged}"},
        )

    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_token"


@pytest.mark.asyncio
async def test_demo_login_rejects_unknown_subject_and_extra_fields() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        unknown = await client.post(
            "/auth/demo-login",
            json={"subject": "demo-invented-user"},
        )
        extra = await client.post(
            "/auth/demo-login",
            json={"subject": "demo-admin", "role": "admin"},
        )

    assert unknown.status_code == 422
    unknown_request_id = unknown.headers["X-Request-ID"]
    assert unknown.json() == {
        "code": "auth.unknown_demo_subject",
        "message": "Unknown demo identity.",
        "details": {"subject": "demo-invented-user"},
        "request_id": unknown_request_id,
    }
    assert extra.status_code == 422
    assert extra.headers["X-Request-ID"]
