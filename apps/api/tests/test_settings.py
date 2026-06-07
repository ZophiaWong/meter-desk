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
