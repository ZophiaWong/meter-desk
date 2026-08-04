import pytest
from pydantic import ValidationError

from meterdesk_api.settings import Settings


def test_settings_defaults_match_local_development_ports(monkeypatch) -> None:
    for env_name in (
        "ENVIRONMENT",
        "API_HOST",
        "API_PORT",
        "FRONTEND_ORIGIN",
        "DATABASE_URL",
    ):
        monkeypatch.delenv(env_name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.environment == "development"
    assert settings.api_port == 8000
    assert settings.frontend_origin == "http://localhost:3000"
    assert settings.database_url == (
        "postgresql+psycopg://meterdesk:meterdesk@localhost:5432/meterdesk"
    )
    assert settings.database_pool_size == 5
    assert settings.database_max_overflow == 5
    assert settings.database_pool_timeout_seconds == 5
    assert settings.database_connect_timeout_seconds == 3


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("database_pool_size", 0),
        ("database_max_overflow", -1),
        ("database_pool_timeout_seconds", 0),
        ("database_connect_timeout_seconds", 0),
    ],
)
def test_database_pool_settings_reject_invalid_values(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


def test_production_environment_rejects_demo_authentication() -> None:
    with pytest.raises(ValidationError, match="Demo authentication cannot run in production"):
        Settings(environment="production", _env_file=None)
