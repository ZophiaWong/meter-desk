"""Test-only harnesses for P0-03's PostgreSQL evidence.

These helpers deliberately live under ``tests``.  The production repository has no
failpoints: evidence tests observe the SQLAlchemy/PostgreSQL boundary and inject an
exception only from the test process.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
from psycopg import sql as psycopg_sql
from sqlalchemy import event, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from meterdesk_api.db import DatabaseRuntime
from meterdesk_api.models import (
    AgentRun,
    ApprovalRequest,
    CaseWorkflow,
    CaseWorkflowTransition,
    MockMutation,
    ToolTrace,
)
from meterdesk_api.settings import get_settings


class InjectedDatabaseFailure(RuntimeError):
    """An exception raised by a test hook before a selected DML statement."""


@dataclass(frozen=True)
class DMLStatement:
    ordinal: int
    operation: str
    table: str
    statement: str


_DML_PATTERN = re.compile(
    r"^\s*(?P<operation>INSERT|UPDATE|DELETE)\s+(?:INTO\s+|FROM\s+)?"
    r'(?P<table>(?:"[^"]+"|[A-Za-z_][A-Za-z0-9_]*)(?:\.(?:"[^"]+"|[A-Za-z_][A-Za-z0-9_]*))?)',
    re.IGNORECASE,
)


def _parse_dml(statement: str) -> tuple[str, str] | None:
    match = _DML_PATTERN.match(statement)
    if match is None:
        return None
    table = match.group("table").replace('"', "").split(".")[-1].lower()
    return match.group("operation").upper(), table


class DMLRecorder:
    """Records the actual DML statements issued by one SQLAlchemy engine."""

    def __init__(self, *, fail_ordinal: int | None = None) -> None:
        self.fail_ordinal = fail_ordinal
        self.statements: list[DMLStatement] = []
        self._installed_engine: Engine | None = None

    @property
    def count(self) -> int:
        return len(self.statements)

    def _before_cursor_execute(
        self,
        _connection,
        _cursor,
        statement: str,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        parsed = _parse_dml(statement)
        if parsed is None:
            return
        operation, table = parsed
        entry = DMLStatement(
            ordinal=len(self.statements) + 1,
            operation=operation,
            table=table,
            statement=" ".join(statement.split()),
        )
        self.statements.append(entry)
        if self.fail_ordinal == entry.ordinal:
            raise InjectedDatabaseFailure(
                f"Injected P0-03 failure before DML ordinal {entry.ordinal} "
                f"({entry.operation} {entry.table})."
            )

    def install(self, engine: AsyncEngine) -> None:
        if self._installed_engine is not None:
            raise RuntimeError("DML recorder is already installed")
        self._installed_engine = engine.sync_engine
        event.listen(self._installed_engine, "before_cursor_execute", self._before_cursor_execute)

    def uninstall(self) -> None:
        if self._installed_engine is not None:
            event.remove(
                self._installed_engine,
                "before_cursor_execute",
                self._before_cursor_execute,
            )
            self._installed_engine = None


@contextmanager
def record_dml(
    engine: AsyncEngine,
    *,
    fail_ordinal: int | None = None,
) -> Iterator[DMLRecorder]:
    recorder = DMLRecorder(fail_ordinal=fail_ordinal)
    recorder.install(engine)
    try:
        yield recorder
    finally:
        recorder.uninstall()


@contextmanager
def fail_after_flush_postexec(
    session: AsyncSession,
    *,
    recorder: DMLRecorder,
    minimum_dml: int,
) -> Iterator[None]:
    """Raise after the final flush has emitted all observed DML, before commit."""

    raised = False

    def after_flush_postexec(_sync_session, _flush_context) -> None:
        nonlocal raised
        if not raised and recorder.count >= minimum_dml:
            raised = True
            raise InjectedDatabaseFailure(
                "Injected P0-03 failure from after_flush_postexec before commit."
            )

    event.listen(session.sync_session, "after_flush_postexec", after_flush_postexec)
    try:
        yield
    finally:
        event.remove(session.sync_session, "after_flush_postexec", after_flush_postexec)


def _stable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {
            str(key): _stable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_stable(item) for item in value]
    return value


def _row_snapshot(row: Any) -> dict[str, Any]:
    return {column: _stable(getattr(row, column)) for column in row.__table__.columns.keys()}


@dataclass(frozen=True)
class DatabaseSnapshot:
    runs: tuple[dict[str, Any], ...]
    workflows: tuple[dict[str, Any], ...]
    transitions: tuple[dict[str, Any], ...]
    approvals: tuple[dict[str, Any], ...]
    mutations: tuple[dict[str, Any], ...]
    traces: tuple[dict[str, Any], ...]

    def as_json(self) -> str:
        return json.dumps(
            {
                "runs": self.runs,
                "workflows": self.workflows,
                "transitions": self.transitions,
                "approvals": self.approvals,
                "mutations": self.mutations,
                "traces": self.traces,
            },
            sort_keys=True,
        )


async def load_database_snapshot(
    runtime: DatabaseRuntime,
    *,
    ticket_id: str,
) -> DatabaseSnapshot:
    """Load a stable, fresh-session snapshot of every P0-03 artifact for a ticket."""

    async with runtime.session_factory() as session:
        workflows = list(
            (
                await session.execute(
                    select(CaseWorkflow)
                    .where(CaseWorkflow.ticket_id == ticket_id)
                    .order_by(CaseWorkflow.id)
                )
            ).scalars()
        )
        workflow_ids = [workflow.id for workflow in workflows]
        runs = list(
            (
                await session.execute(
                    select(AgentRun).where(AgentRun.ticket_id == ticket_id).order_by(AgentRun.id)
                )
            ).scalars()
        )
        run_ids = [run.id for run in runs]
        transitions = list(
            (
                await session.execute(
                    select(CaseWorkflowTransition)
                    .where(CaseWorkflowTransition.workflow_id.in_(workflow_ids or ["__none__"]))
                    .order_by(CaseWorkflowTransition.id)
                )
            ).scalars()
        )
        approvals = list(
            (
                await session.execute(
                    select(ApprovalRequest)
                    .where(ApprovalRequest.ticket_id == ticket_id)
                    .order_by(ApprovalRequest.id)
                )
            ).scalars()
        )
        mutations = list(
            (
                await session.execute(
                    select(MockMutation)
                    .where(MockMutation.ticket_id == ticket_id)
                    .order_by(MockMutation.id)
                )
            ).scalars()
        )
        traces = list(
            (
                await session.execute(
                    select(ToolTrace)
                    .where(ToolTrace.agent_run_id.in_(run_ids or ["__none__"]))
                    .order_by(ToolTrace.id)
                )
            ).scalars()
        )
    return DatabaseSnapshot(
        runs=tuple(_row_snapshot(row) for row in runs),
        workflows=tuple(_row_snapshot(row) for row in workflows),
        transitions=tuple(_row_snapshot(row) for row in transitions),
        approvals=tuple(_row_snapshot(row) for row in approvals),
        mutations=tuple(_row_snapshot(row) for row in mutations),
        traces=tuple(_row_snapshot(row) for row in traces),
    )


def _database_url_for_psycopg(url: str) -> str:
    parsed = make_url(url)
    if parsed.drivername.startswith("postgresql+"):
        parsed = parsed.set(drivername="postgresql")
    return parsed.render_as_string(hide_password=False)


@dataclass(frozen=True)
class TemporaryPostgresDatabase:
    name: str
    url: str


@contextmanager
def temporary_postgres_database() -> Iterator[TemporaryPostgresDatabase]:
    """Create a unique database and drop it with FORCE in all exit paths."""

    configured_url = os.environ.get("DATABASE_URL") or get_settings().database_url
    parsed = make_url(configured_url)
    database_name = f"meterdesk_p003_{uuid4().hex[:16]}"
    admin_url = parsed.set(database="postgres")
    admin_connection = _database_url_for_psycopg(admin_url.render_as_string(hide_password=False))
    database_url = parsed.set(database=database_name).render_as_string(hide_password=False)
    try:
        with psycopg.connect(admin_connection, autocommit=True) as connection:
            connection.execute(
                psycopg_sql.SQL("CREATE DATABASE {} ").format(psycopg_sql.Identifier(database_name))
            )
    except psycopg.Error as error:
        raise RuntimeError(
            "P0-03 migration evidence requires a PostgreSQL role with CREATEDB privilege."
        ) from error
    try:
        yield TemporaryPostgresDatabase(name=database_name, url=database_url)
    finally:
        try:
            with psycopg.connect(admin_connection, autocommit=True) as connection:
                connection.execute(
                    psycopg_sql.SQL(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = {} AND pid <> pg_backend_pid()"
                    ).format(psycopg_sql.Literal(database_name))
                )
                connection.execute(
                    psycopg_sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                        psycopg_sql.Identifier(database_name)
                    )
                )
        except psycopg.Error:
            # Cleanup errors must not hide the migration assertion; the next
            # fixture will still use a unique database name.
            pass


def run_alembic(database_url: str, revision: str) -> subprocess.CompletedProcess[str]:
    api_dir = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    environment.pop("TEMP", None)
    environment.pop("TMP", None)
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revision],
        cwd=api_dir,
        env=environment,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )


async def wait_for_tasks(*tasks: asyncio.Task[Any], timeout: float = 5) -> tuple[Any, ...]:
    """Await concurrent evidence operations with the plan's five-second bound."""

    results = await asyncio.wait_for(
        asyncio.gather(*tasks, return_exceptions=True),
        timeout=timeout,
    )
    return tuple(results)
