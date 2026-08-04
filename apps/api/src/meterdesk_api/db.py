from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from meterdesk_api.settings import Settings, get_settings


@dataclass(frozen=True)
class DatabaseRuntime:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]

    async def dispose(self) -> None:
        await self.engine.dispose()


def create_engine(settings: Settings | None = None) -> AsyncEngine:
    resolved_settings = settings or get_settings()
    return create_async_engine(
        resolved_settings.database_url,
        connect_args={
            "connect_timeout": resolved_settings.database_connect_timeout_seconds,
        },
        pool_pre_ping=True,
        pool_size=resolved_settings.database_pool_size,
        max_overflow=resolved_settings.database_max_overflow,
        pool_timeout=resolved_settings.database_pool_timeout_seconds,
    )


def create_database_runtime(settings: Settings | None = None) -> DatabaseRuntime:
    engine = create_engine(settings)
    return DatabaseRuntime(
        engine=engine,
        session_factory=async_sessionmaker(engine, expire_on_commit=False),
    )


@asynccontextmanager
async def database_runtime_context(
    settings: Settings | None = None,
) -> AsyncIterator[DatabaseRuntime]:
    runtime = create_database_runtime(settings)
    try:
        yield runtime
    finally:
        await runtime.dispose()


async def get_database_runtime(request: Request) -> DatabaseRuntime:
    try:
        return request.app.state.database_runtime
    except AttributeError as error:
        raise RuntimeError(
            "Database runtime is unavailable; initialize the FastAPI lifespan first."
        ) from error


async def check_database(runtime: DatabaseRuntime) -> None:
    async with runtime.engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def get_session(
    runtime: Annotated[DatabaseRuntime, Depends(get_database_runtime)],
) -> AsyncIterator[AsyncSession]:
    async with runtime.session_factory() as session:
        yield session
