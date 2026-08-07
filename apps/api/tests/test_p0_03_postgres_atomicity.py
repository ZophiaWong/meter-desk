from __future__ import annotations

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import uuid4

import pytest

from meterdesk_api.db import DatabaseRuntime, create_database_runtime
from meterdesk_api.repositories import SqlAlchemyMeterDeskRepository
from meterdesk_api.schemas import ApprovalDecisionActor
from p0_03_evidence_helpers import (
    DatabaseSnapshot,
    InjectedDatabaseFailure,
    fail_after_flush_postexec,
    load_database_snapshot,
    record_dml,
)

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.p0_03_evidence,
    pytest.mark.skipif(
        os.environ.get("METERDESK_RUN_DB_TESTS") != "1",
        reason="Set METERDESK_RUN_DB_TESTS=1 and run against local Postgres.",
    ),
]

TICKET_ID = "TCK-1042"


@dataclass(frozen=True)
class RunningFixture:
    runtime: DatabaseRuntime
    run_id: str
    workflow_id: str
    unique: str


@dataclass(frozen=True)
class ApprovalFixture(RunningFixture):
    approval_id: str


@pytest.fixture
async def atomic_runtime() -> AsyncIterator[DatabaseRuntime]:
    runtime = create_database_runtime()
    try:
        yield runtime
    finally:
        async with runtime.session_factory() as session:
            await SqlAlchemyMeterDeskRepository(session).reset_demo_live_state(TICKET_ID)
        await runtime.dispose()


@pytest.mark.asyncio
async def test_finalize_run_rolls_back_every_dml_ordinal_and_after_flush(
    atomic_runtime: DatabaseRuntime,
) -> None:
    control = await _record_finalize_control(atomic_runtime)
    assert control.dml_count > 0
    assert {item.table for item in control.statements} >= {
        "agent_runs",
        "case_workflows",
        "case_workflow_transitions",
        "approval_requests",
        "tool_traces",
    }

    for ordinal in range(1, control.dml_count + 1):
        fixture = await _prepare_running_fixture(atomic_runtime)
        before = await load_database_snapshot(atomic_runtime, ticket_id=TICKET_ID)
        with record_dml(atomic_runtime.engine, fail_ordinal=ordinal):
            async with atomic_runtime.session_factory() as session:
                repository = SqlAlchemyMeterDeskRepository(session)
                with pytest.raises(InjectedDatabaseFailure):
                    await repository.finalize_run(
                        agent_run_id=fixture.run_id,
                        **_finalize_arguments(fixture.unique),
                    )
        after = await load_database_snapshot(atomic_runtime, ticket_id=TICKET_ID)
        assert after == before, f"finalize rollback changed state at DML ordinal {ordinal}"
        _assert_running_snapshot(after, fixture)

    fixture = await _prepare_running_fixture(atomic_runtime)
    before = await load_database_snapshot(atomic_runtime, ticket_id=TICKET_ID)
    with record_dml(atomic_runtime.engine) as recorder:
        async with atomic_runtime.session_factory() as session:
            repository = SqlAlchemyMeterDeskRepository(session)
            with (
                fail_after_flush_postexec(
                    session,
                    recorder=recorder,
                    minimum_dml=control.dml_count,
                ),
                pytest.raises(InjectedDatabaseFailure),
            ):
                await repository.finalize_run(
                    agent_run_id=fixture.run_id,
                    **_finalize_arguments(fixture.unique),
                )
    after = await load_database_snapshot(atomic_runtime, ticket_id=TICKET_ID)
    assert after == before
    _assert_running_snapshot(after, fixture)


@pytest.mark.asyncio
async def test_approve_and_execute_rolls_back_every_dml_ordinal_and_after_flush(
    atomic_runtime: DatabaseRuntime,
) -> None:
    control_fixture = await _prepare_approval_fixture(atomic_runtime)
    control = await _record_approve_control(atomic_runtime, control_fixture)
    assert control.dml_count > 0
    assert {item.table for item in control.statements} >= {
        "approval_requests",
        "case_workflows",
        "case_workflow_transitions",
        "mock_mutations",
        "tool_traces",
    }

    for ordinal in range(1, control.dml_count + 1):
        fixture = await _prepare_approval_fixture(atomic_runtime)
        before = await load_database_snapshot(atomic_runtime, ticket_id=TICKET_ID)
        with record_dml(atomic_runtime.engine, fail_ordinal=ordinal):
            async with atomic_runtime.session_factory() as session:
                repository = SqlAlchemyMeterDeskRepository(session)
                with pytest.raises(InjectedDatabaseFailure):
                    await repository.approve_and_execute(
                        approval_id=fixture.approval_id,
                        decision_actor=_approval_actor(),
                        decision_request_id=f"p0-03-atomic-{fixture.unique}",
                        decision_note="Atomicity evidence.",
                    )
        after = await load_database_snapshot(atomic_runtime, ticket_id=TICKET_ID)
        assert after == before, f"approve rollback changed state at DML ordinal {ordinal}"
        _assert_pending_approval_snapshot(after, fixture)

    fixture = await _prepare_approval_fixture(atomic_runtime)
    before = await load_database_snapshot(atomic_runtime, ticket_id=TICKET_ID)
    with record_dml(atomic_runtime.engine) as recorder:
        async with atomic_runtime.session_factory() as session:
            repository = SqlAlchemyMeterDeskRepository(session)
            with (
                fail_after_flush_postexec(
                    session,
                    recorder=recorder,
                    minimum_dml=control.dml_count,
                ),
                pytest.raises(InjectedDatabaseFailure),
            ):
                await repository.approve_and_execute(
                    approval_id=fixture.approval_id,
                    decision_actor=_approval_actor(),
                    decision_request_id=f"p0-03-after-flush-{fixture.unique}",
                    decision_note="Atomicity evidence.",
                )
    after = await load_database_snapshot(atomic_runtime, ticket_id=TICKET_ID)
    assert after == before
    _assert_pending_approval_snapshot(after, fixture)


@dataclass(frozen=True)
class DMLControl:
    dml_count: int
    statements: tuple


async def _record_finalize_control(runtime: DatabaseRuntime) -> DMLControl:
    fixture = await _prepare_running_fixture(runtime)
    with record_dml(runtime.engine) as recorder:
        async with runtime.session_factory() as session:
            await SqlAlchemyMeterDeskRepository(session).finalize_run(
                agent_run_id=fixture.run_id,
                **_finalize_arguments(fixture.unique),
            )
    return DMLControl(recorder.count, tuple(recorder.statements))


async def _record_approve_control(
    runtime: DatabaseRuntime,
    fixture: ApprovalFixture,
) -> DMLControl:
    with record_dml(runtime.engine) as recorder:
        async with runtime.session_factory() as session:
            await SqlAlchemyMeterDeskRepository(session).approve_and_execute(
                approval_id=fixture.approval_id,
                decision_actor=_approval_actor(),
                decision_request_id=f"p0-03-control-{fixture.unique}",
                decision_note="Atomicity control.",
            )
    return DMLControl(recorder.count, tuple(recorder.statements))


async def _prepare_running_fixture(runtime: DatabaseRuntime) -> RunningFixture:
    unique = uuid4().hex
    async with runtime.session_factory() as session:
        repository = SqlAlchemyMeterDeskRepository(session)
        await repository.reset_demo_live_state(TICKET_ID)
        run = await repository.create_agent_run(
            ticket_id=TICKET_ID,
            source="p0-03-atomicity",
            model="deterministic-test-model",
            prompt_version="p0-03-evidence-v1",
        )
        assert run.workflow_id is not None
        await repository.add_tool_trace(
            agent_run_id=run.id,
            category="read.billing_evidence",
            risk="Low",
            label="Existing trace before atomic command",
            input_summary="Atomicity fixture input.",
            output_summary="Atomicity fixture output.",
            evidence_refs=["invoice INV-2026-0418"],
            policy_refs=[],
            approval_refs=[],
        )
    return RunningFixture(runtime, run.id, run.workflow_id, unique)


async def _prepare_approval_fixture(runtime: DatabaseRuntime) -> ApprovalFixture:
    fixture = await _prepare_running_fixture(runtime)
    async with runtime.session_factory() as session:
        repository = SqlAlchemyMeterDeskRepository(session)
        await repository.finalize_run(
            agent_run_id=fixture.run_id,
            **_finalize_arguments(fixture.unique),
        )
        approvals = await repository.list_approvals(ticket_id=TICKET_ID, status="pending")
    assert len(approvals) == 1
    return ApprovalFixture(
        runtime=runtime,
        run_id=fixture.run_id,
        workflow_id=fixture.workflow_id,
        unique=fixture.unique,
        approval_id=approvals[0].id,
    )


def _finalize_arguments(unique: str) -> dict[str, object]:
    approval_id = f"APR-P003-{unique}"
    return {
        "final_outcome": "confirmed_duplicate_charge",
        "internal_resolution": "Duplicate captured charge confirmed for atomicity evidence.",
        "customer_reply": "Draft only.",
        "target_status": "awaiting_approval",
        "reason_code": "p0_03.evidence.awaiting_approval",
        "reason_detail": "Atomicity evidence fixture.",
        "request_id": f"req-p0-03-{unique}",
        "final_trace": {
            "id": f"TRACE-P003-FINAL-{unique}",
            "category": "decision.refund_eligibility",
            "risk": "Medium",
            "label": "Final decision trace",
            "input_summary": "Atomicity evidence input.",
            "output_summary": "Approval required.",
            "evidence_refs": ["invoice INV-2026-0418"],
            "policy_refs": ["DUP-CHARGE-001 v2026.04"],
            "approval_refs": [],
            "governance_metadata": {"gate_result": "allowed"},
        },
        "approval": {
            "id": approval_id,
            "title": "P0-03 atomicity approval",
            "action_type": "original_refund",
            "amount_cents": 29000,
            "amount_display": "$290.00",
            "currency": "USD",
            "reason": "Duplicate captured charge requires approval.",
            "blocker": "Mutation blocked until human approval.",
            "policy_citation": "DUP-CHARGE-001 v2026.04",
            "evidence_refs": ["invoice INV-2026-0418", "charge ch_2026_0418_B"],
            "action_metadata": {"target_charge_id": f"p0-03-charge-{unique}"},
            "action_fingerprint": f"p0-03-atomic-fingerprint:{unique}",
        },
        "approval_trace": {
            "id": f"TRACE-P003-APPROVAL-{unique}",
            "category": "approval.create_request",
            "risk": "Medium",
            "label": "Approval trace",
            "input_summary": "Created approval gate.",
            "output_summary": "Approval pending.",
            "evidence_refs": ["invoice INV-2026-0418"],
            "policy_refs": ["DUP-CHARGE-001 v2026.04"],
            "approval_refs": ["pending"],
            "governance_metadata": {"gate_result": "allowed"},
        },
    }


def _approval_actor() -> ApprovalDecisionActor:
    return ApprovalDecisionActor(
        subject="p0-03-approver",
        display_name="P0-03 Evidence Approver",
        role="approver",
        source="demo_session",
    )


def _assert_running_snapshot(snapshot: DatabaseSnapshot, fixture: RunningFixture) -> None:
    run = next(row for row in snapshot.runs if row["id"] == fixture.run_id)
    workflow = next(row for row in snapshot.workflows if row["id"] == fixture.workflow_id)
    assert run["status"] == "running"
    assert run["final_outcome"] is None
    assert run["completed_at"] is None
    assert workflow["status"] == "investigating"
    assert workflow["version"] == 1
    assert workflow["transition_sequence"] == 1
    assert snapshot.approvals == ()


def _assert_pending_approval_snapshot(snapshot: DatabaseSnapshot, fixture: ApprovalFixture) -> None:
    run = next(row for row in snapshot.runs if row["id"] == fixture.run_id)
    workflow = next(row for row in snapshot.workflows if row["id"] == fixture.workflow_id)
    approval = next(row for row in snapshot.approvals if row["id"] == fixture.approval_id)
    assert run["status"] == "completed"
    assert workflow["status"] == "awaiting_approval"
    assert workflow["version"] == 2
    assert workflow["transition_sequence"] == 2
    assert approval["status"] == "pending"
    assert approval["decision_actor_subject"] is None
    assert approval["decision_request_id"] is None
    assert snapshot.mutations == ()
