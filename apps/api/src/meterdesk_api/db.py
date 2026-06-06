import socket
from collections.abc import AsyncIterator

import psycopg
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from meterdesk_api.settings import get_settings


def create_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        connect_args={"connect_timeout": 2},
        pool_pre_ping=True,
    )


async def check_database() -> None:
    _run_database_probe()


def _run_database_probe() -> None:
    settings = get_settings()
    database_url = make_url(settings.database_url)
    host = database_url.host or "localhost"
    port = database_url.port or 5432

    with socket.create_connection((host, port), timeout=2.0):
        pass

    psycopg_url = database_url.set(drivername="postgresql").render_as_string(hide_password=False)
    with psycopg.connect(psycopg_url, connect_timeout=3) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()


async def get_session() -> AsyncIterator[AsyncSession]:
    engine = create_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()
