from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from meterdesk_api.db import DatabaseRuntime, create_database_runtime
from meterdesk_api.errors import MeterDeskAPIError
from meterdesk_api.models import AgentRun, CaseWorkflow
from meterdesk_api.repositories import SqlAlchemyMeterDeskRepository
from meterdesk_api.schemas import ApprovalDecisionActor
from p0_03_evidence_helpers import load_database_snapshot

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
class RaceFixture:
    runtime: DatabaseRuntime
    workflow_id: str
    run_id: str
    approval_id: str | None
    unique: str


@pytest.fixture
async def concurrency_runtime():
    runtime = create_database_runtime()
    try:
        yield runtime
    finally:
        async with runtime.session_factory() as session:
            await SqlAlchemyMeterDeskRepository(session).reset_demo_live_state(TICKET_ID)
        await runtime.dispose()


@pytest.mark.asyncio
async def test_same_key_start_race_creates_one_run_and_replays_the_winner(
    concurrency_runtime: DatabaseRuntime,
) -> None:
    runtime = concurrency_runtime
    await _reset(runtime)
    results = await _run_start_race(runtime, key_left="same-key", key_right="same-key")

    assert sorted(result.replayed for result in results) == [False, True]
    assert results[0].run.id == results[1].run.id
    assert await _count_running_runs(runtime) == 1
    assert await _count_workflow_transitions(runtime) == 1


@pytest.mark.asyncio
async def test_different_key_start_race_has_one_success_and_one_conflict(
    concurrency_runtime: DatabaseRuntime,
) -> None:
    runtime = concurrency_runtime
    await _reset(runtime)
    results = await _run_start_race(runtime, key_left="key-a", key_right="key-b")

    successful = [result for result in results if not isinstance(result, MeterDeskAPIError)]
    conflicts = [result for result in results if isinstance(result, MeterDeskAPIError)]
    assert len(successful) == 1
    assert len(conflicts) == 1
    assert conflicts[0].status_code == 409
    assert conflicts[0].code in {"workflow.active_conflict", "workflow.start_conflict"}
    assert await _count_running_runs(runtime) == 1


@pytest.mark.asyncio
async def test_same_key_retry_race_reuses_cycle_without_duplicate_transition(
    concurrency_runtime: DatabaseRuntime,
) -> None:
    runtime = concurrency_runtime
    fixture = await _prepare_needs_retry(runtime)
    results = await _run_start_race(runtime, key_left="retry-key", key_right="retry-key")

    assert sorted(result.replayed for result in results) == [False, True]
    assert results[0].run.workflow_id == fixture.workflow_id
    assert results[0].run.id == results[1].run.id
    assert await _count_running_runs(runtime) == 1
    assert await _count_workflow_transitions(runtime) == 3


@pytest.mark.asyncio
async def test_different_key_retry_race_has_one_success_and_one_conflict(
    concurrency_runtime: DatabaseRuntime,
) -> None:
    runtime = concurrency_runtime
    fixture = await _prepare_needs_retry(runtime)
    results = await _run_start_race(runtime, key_left="retry-a", key_right="retry-b")

    successful = [result for result in results if not isinstance(result, MeterDeskAPIError)]
    conflicts = [result for result in results if isinstance(result, MeterDeskAPIError)]
    assert len(successful) == 1
    assert successful[0].run.workflow_id == fixture.workflow_id
    assert len(conflicts) == 1
    assert conflicts[0].status_code == 409
    assert await _count_running_runs(runtime) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("first", ["approve", "cancel"])
async def test_approve_cancel_race_is_equivalent_to_a_legal_serial_order(
    concurrency_runtime: DatabaseRuntime,
    first: str,
) -> None:
    fixture = await _prepare_approval(concurrency_runtime)
    first_result, second_result = await _run_blocked_race(
        fixture,
        first=first,
        second="cancel" if first == "approve" else "approve",
    )
    snapshot = await load_database_snapshot(concurrency_runtime, ticket_id=TICKET_ID)

    assert isinstance(first_result, (ApprovalResult, CancelResult))
    assert isinstance(second_result, (ApprovalResult, CancelResult, MeterDeskAPIError))
    workflow = next(row for row in snapshot.workflows if row["id"] == fixture.workflow_id)
    if first == "approve":
        assert second_result.status_code == 409
        assert workflow["status"] == "mock_executed"
        assert len(snapshot.mutations) == 1
    else:
        assert second_result.status_code == 409
        assert workflow["status"] == "cancelled"
        assert snapshot.approvals[0]["status"] == "withdrawn"
        assert snapshot.mutations == ()


@pytest.mark.asyncio
@pytest.mark.parametrize("first", ["reject", "cancel"])
async def test_reject_cancel_race_has_no_mutation_and_one_terminal_winner(
    concurrency_runtime: DatabaseRuntime,
    first: str,
) -> None:
    fixture = await _prepare_approval(concurrency_runtime)
    first_result, second_result = await _run_blocked_race(
        fixture,
        first=first,
        second="cancel" if first == "reject" else "reject",
    )
    snapshot = await load_database_snapshot(concurrency_runtime, ticket_id=TICKET_ID)

    assert isinstance(first_result, (ApprovalResult, CancelResult))
    assert isinstance(second_result, (ApprovalResult, CancelResult, MeterDeskAPIError))
    assert second_result.status_code == 409
    assert snapshot.mutations == ()
    workflow = next(row for row in snapshot.workflows if row["id"] == fixture.workflow_id)
    if first == "reject":
        assert workflow["status"] == "rejected"
        assert snapshot.approvals[0]["status"] == "rejected"
    else:
        assert workflow["status"] == "cancelled"
        assert snapshot.approvals[0]["status"] == "withdrawn"


@pytest.mark.asyncio
@pytest.mark.parametrize("first", ["cancel", "finalize"])
async def test_cancel_finalize_to_awaiting_approval_is_a_serializable_state_transition(
    concurrency_runtime: DatabaseRuntime,
    first: str,
) -> None:
    fixture = await _prepare_running(concurrency_runtime)
    first_result, second_result = await _run_blocked_race(
        fixture,
        first=first,
        second="finalize" if first == "cancel" else "cancel",
        finalize_target="awaiting_approval",
    )
    snapshot = await load_database_snapshot(concurrency_runtime, ticket_id=TICKET_ID)
    workflow = next(row for row in snapshot.workflows if row["id"] == fixture.workflow_id)

    if first == "cancel":
        assert isinstance(first_result, CancelResult)
        assert isinstance(second_result, MeterDeskAPIError)
        assert second_result.status_code == 409
        assert workflow["status"] == "cancelled"
        assert snapshot.approvals == ()
    else:
        assert isinstance(first_result, FinalizeResult)
        assert isinstance(second_result, CancelResult)
        assert workflow["status"] == "cancelled"
        assert snapshot.approvals[0]["status"] == "withdrawn"
        run = next(row for row in snapshot.runs if row["id"] == fixture.run_id)
        assert run["status"] == "completed"


@pytest.mark.asyncio
@pytest.mark.parametrize("first", ["cancel", "finalize"])
async def test_cancel_finalize_to_completed_no_action_has_one_terminal_winner(
    concurrency_runtime: DatabaseRuntime,
    first: str,
) -> None:
    fixture = await _prepare_running(concurrency_runtime)
    first_result, second_result = await _run_blocked_race(
        fixture,
        first=first,
        second="finalize" if first == "cancel" else "cancel",
        finalize_target="completed_no_action",
    )
    snapshot = await load_database_snapshot(concurrency_runtime, ticket_id=TICKET_ID)
    workflow = next(row for row in snapshot.workflows if row["id"] == fixture.workflow_id)
    assert isinstance(first_result, (CancelResult, FinalizeResult))
    assert isinstance(second_result, MeterDeskAPIError)
    assert second_result.status_code == 409
    assert workflow["status"] == ("cancelled" if first == "cancel" else "completed_no_action")
    assert snapshot.approvals == ()


@dataclass(frozen=True)
class ApprovalResult:
    status: str = "approved"


@dataclass(frozen=True)
class CancelResult:
    status: str = "cancelled"


@dataclass(frozen=True)
class FinalizeResult:
    status: str


async def _run_start_race(runtime: DatabaseRuntime, *, key_left: str, key_right: str):
    async with (
        runtime.session_factory() as left_session,
        runtime.session_factory() as right_session,
    ):
        left = asyncio.create_task(
            SqlAlchemyMeterDeskRepository(left_session).start_or_replay_run(
                ticket_id=TICKET_ID,
                idempotency_key=key_left,
                source="p0-03-concurrency",
                model="deterministic-test-model",
                prompt_version="p0-03-evidence-v1",
            )
        )
        right = asyncio.create_task(
            SqlAlchemyMeterDeskRepository(right_session).start_or_replay_run(
                ticket_id=TICKET_ID,
                idempotency_key=key_right,
                source="p0-03-concurrency",
                model="deterministic-test-model",
                prompt_version="p0-03-evidence-v1",
            )
        )
        return await asyncio.wait_for(
            asyncio.gather(left, right, return_exceptions=True),
            timeout=5,
        )


async def _run_blocked_race(
    fixture: RaceFixture,
    *,
    first: str,
    second: str,
    finalize_target: str | None = None,
):
    runtime = fixture.runtime
    async with (
        runtime.session_factory() as blocker_session,
        runtime.session_factory() as first_session,
        runtime.session_factory() as second_session,
        runtime.session_factory() as monitor_session,
    ):
        locked = (
            await blocker_session.execute(
                select(CaseWorkflow).where(CaseWorkflow.id == fixture.workflow_id).with_for_update()
            )
        ).scalar_one()
        assert locked.status in {"investigating", "awaiting_approval"}
        first_task = asyncio.create_task(
            _capture_command(
                first_session,
                fixture,
                command=first,
                finalize_target=finalize_target,
            )
        )
        await _wait_for_workflow_lock_waits(monitor_session, expected_count=1)
        second_task = asyncio.create_task(
            _capture_command(
                second_session,
                fixture,
                command=second,
                finalize_target=finalize_target,
            )
        )
        await _wait_for_workflow_lock_waits(monitor_session, expected_count=2)
        await blocker_session.commit()
        first_result, second_result = await asyncio.wait_for(
            asyncio.gather(first_task, second_task), timeout=5
        )
    return first_result, second_result


async def _capture_command(
    session,
    fixture: RaceFixture,
    *,
    command: str,
    finalize_target: str | None,
):
    repository = SqlAlchemyMeterDeskRepository(session)
    try:
        if command == "approve":
            await repository.approve_and_execute(
                approval_id=fixture.approval_id or "missing",
                decision_actor=_actor("p0-03-approver", "P0-03 Approver", "approver"),
                decision_request_id=f"p0-03-race-approve-{fixture.unique}",
                decision_note="Concurrency evidence.",
            )
            return ApprovalResult()
        if command == "reject":
            await repository.reject_approval(
                approval_id=fixture.approval_id or "missing",
                decision_actor=_actor("p0-03-admin", "P0-03 Admin", "admin"),
                decision_request_id=f"p0-03-race-reject-{fixture.unique}",
                decision_note="Concurrency evidence.",
            )
            return ApprovalResult(status="rejected")
        if command == "cancel":
            await repository.cancel_workflow(
                workflow_id=fixture.workflow_id,
                actor=_actor("p0-03-support", "P0-03 Support", "support_operator"),
                request_id=f"p0-03-race-cancel-{fixture.unique}",
                reason="Concurrency evidence cancellation.",
            )
            return CancelResult()
        if command == "finalize":
            assert finalize_target is not None
            await repository.finalize_run(
                agent_run_id=fixture.run_id,
                **_finalize_arguments(fixture.unique, target_status=finalize_target),
            )
            return FinalizeResult(status=finalize_target)
        raise AssertionError(f"Unknown race command: {command}")
    except MeterDeskAPIError as error:
        return error


async def _wait_for_workflow_lock_waits(monitor_session, *, expected_count: int) -> None:
    async with asyncio.timeout(5):
        while True:
            await monitor_session.execute(text("SELECT pg_stat_clear_snapshot()"))
            waiting = (
                await monitor_session.execute(
                    text(
                        "SELECT count(*) FROM pg_stat_activity "
                        "WHERE pid <> pg_backend_pid() "
                        "AND datname = current_database() "
                        "AND wait_event_type = 'Lock' "
                        "AND query LIKE '%case_workflows%' "
                        "AND query LIKE '%FOR UPDATE%'"
                    )
                )
            ).scalar_one()
            if waiting >= expected_count:
                return
            await asyncio.sleep(0.01)


async def _prepare_running(runtime: DatabaseRuntime) -> RaceFixture:
    unique = uuid4().hex
    async with runtime.session_factory() as session:
        repository = SqlAlchemyMeterDeskRepository(session)
        await repository.reset_demo_live_state(TICKET_ID)
        run = await repository.create_agent_run(
            ticket_id=TICKET_ID,
            source="p0-03-concurrency",
            model="deterministic-test-model",
            prompt_version="p0-03-evidence-v1",
        )
    assert run.workflow_id is not None
    return RaceFixture(runtime, run.workflow_id, run.id, None, unique)


async def _prepare_needs_retry(runtime: DatabaseRuntime) -> RaceFixture:
    fixture = await _prepare_running(runtime)
    async with runtime.session_factory() as session:
        await SqlAlchemyMeterDeskRepository(session).fail_run(
            agent_run_id=fixture.run_id,
            error_code="p0-03.test.retryable",
            error_state="Retryable concurrency fixture failure.",
            recoverable=True,
        )
    return fixture


async def _prepare_approval(runtime: DatabaseRuntime) -> RaceFixture:
    fixture = await _prepare_running(runtime)
    async with runtime.session_factory() as session:
        repository = SqlAlchemyMeterDeskRepository(session)
        await repository.finalize_run(
            agent_run_id=fixture.run_id,
            **_finalize_arguments(fixture.unique),
        )
        approvals = await repository.list_approvals(ticket_id=TICKET_ID, status="pending")
    assert len(approvals) == 1
    return RaceFixture(
        runtime,
        fixture.workflow_id,
        fixture.run_id,
        approvals[0].id,
        fixture.unique,
    )


async def _reset(runtime: DatabaseRuntime) -> None:
    async with runtime.session_factory() as session:
        await SqlAlchemyMeterDeskRepository(session).reset_demo_live_state(TICKET_ID)


async def _count_running_runs(runtime: DatabaseRuntime) -> int:
    async with runtime.session_factory() as session:
        return int(
            (
                await session.execute(
                    select(AgentRun).where(
                        AgentRun.ticket_id == TICKET_ID,
                        AgentRun.status == "running",
                    )
                )
            )
            .scalars()
            .all()
            .__len__()
        )


async def _count_workflow_transitions(runtime: DatabaseRuntime) -> int:
    async with runtime.session_factory() as session:
        workflow = (
            await session.execute(select(CaseWorkflow).where(CaseWorkflow.ticket_id == TICKET_ID))
        ).scalar_one()
        return workflow.transition_sequence


def _actor(subject: str, display_name: str, role: str) -> ApprovalDecisionActor:
    return ApprovalDecisionActor(
        subject=subject,
        display_name=display_name,
        role=role,
        source="demo_session",
    )


def _finalize_arguments(
    unique: str,
    *,
    target_status: str = "awaiting_approval",
) -> dict[str, object]:
    arguments: dict[str, object] = {
        "final_outcome": (
            "confirmed_duplicate_charge"
            if target_status == "awaiting_approval"
            else "no_refund_expected_billing_behavior"
        ),
        "internal_resolution": "P0-03 concurrency fixture.",
        "customer_reply": "Draft only.",
        "target_status": target_status,
        "reason_code": "p0_03.concurrency.fixture",
        "reason_detail": "Concurrency evidence fixture.",
        "request_id": f"p0-03-finalize-{unique}",
    }
    if target_status == "awaiting_approval":
        arguments["approval"] = {
            "id": f"APR-P003-RACE-{unique}",
            "title": "P0-03 concurrency approval",
            "action_type": "original_refund",
            "amount_cents": 29000,
            "amount_display": "$290.00",
            "currency": "USD",
            "reason": "Concurrency fixture approval.",
            "blocker": "Mutation blocked until human approval.",
            "policy_citation": "DUP-CHARGE-001 v2026.04",
            "evidence_refs": ["invoice INV-2026-0418"],
            "action_metadata": {"target_charge_id": f"p0-03-race-charge-{unique}"},
            "action_fingerprint": f"p0-03-race-fingerprint:{unique}",
        }
    return arguments
