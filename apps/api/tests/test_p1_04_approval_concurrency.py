import asyncio
import os
from dataclasses import dataclass
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text

from meterdesk_api.agent.approvals import ApprovalDecisionService
from meterdesk_api.db import DatabaseRuntime, create_database_runtime
from meterdesk_api.errors import MeterDeskAPIError
from meterdesk_api.models import AgentRun, ApprovalRequest, MockMutation, ToolTrace
from meterdesk_api.repositories import SqlAlchemyMeterDeskRepository
from meterdesk_api.schemas import (
    ApprovalDecisionActor,
    ApprovalDecisionResponse,
    ApprovalSummary,
    MockMutationSummary,
    ToolTraceSummary,
)

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        os.environ.get("METERDESK_RUN_DB_TESTS") != "1",
        reason="Set METERDESK_RUN_DB_TESTS=1 and run against local Postgres.",
    ),
]


@dataclass(frozen=True)
class ApprovalRaceFixture:
    runtime: DatabaseRuntime
    run_id: str
    approval_id: str
    fingerprint: str


@dataclass(frozen=True)
class PersistedRaceResult:
    approval: ApprovalSummary
    mutations: list[MockMutationSummary]
    traces: list[ToolTraceSummary]


@pytest.fixture
async def approval_race() -> ApprovalRaceFixture:
    runtime = create_database_runtime()
    unique = uuid4().hex
    run_id: str | None = None
    approval_id: str | None = None
    fingerprint = f"p1-04-concurrency:{unique}"

    try:
        async with runtime.session_factory() as session:
            repository = SqlAlchemyMeterDeskRepository(session)
            run = await repository.create_agent_run(
                ticket_id="TCK-1042",
                source="p1-04-postgres-test",
                model="deterministic-test-model",
                prompt_version="p1-04-concurrency-v1",
            )
            run_id = run.id
            approval = await repository.create_approval_request(
                ticket_id="TCK-1042",
                agent_run_id=run.id,
                title="P1-04 concurrent approval proof",
                action_type=f"p1_04_refund_{unique}",
                amount_cents=29000,
                amount_display="$290.00",
                currency="USD",
                reason="Prove deterministic approval terminal-state concurrency.",
                blocker="Mutation blocked until human approval",
                policy_citation="DUP-CHARGE-001 v2026.04",
                evidence_refs=["invoice INV-2026-0418", "charge ch_2026_0418_B"],
                action_metadata={"target_charge_id": f"p1-04-charge-{unique}"},
                action_fingerprint=fingerprint,
            )
            approval_id = approval.id

        yield ApprovalRaceFixture(
            runtime=runtime,
            run_id=run_id,
            approval_id=approval_id,
            fingerprint=fingerprint,
        )
    finally:
        if run_id is not None:
            async with runtime.session_factory() as session:
                async with session.begin():
                    await session.execute(delete(ToolTrace).where(ToolTrace.agent_run_id == run_id))
                    if approval_id is not None:
                        await session.execute(
                            delete(MockMutation).where(
                                MockMutation.approval_request_id == approval_id
                            )
                        )
                        await session.execute(
                            delete(ApprovalRequest).where(ApprovalRequest.id == approval_id)
                        )
                    await session.execute(delete(AgentRun).where(AgentRun.id == run_id))
        await runtime.dispose()


@pytest.mark.asyncio
async def test_concurrent_approve_approve_is_idempotent(
    approval_race: ApprovalRaceFixture,
) -> None:
    winner_actor = _actor("winner-approver", "Winner Approver", "approver")
    loser_actor = _actor("loser-admin", "Loser Admin", "admin")

    winner, loser = await _run_locked_race(
        approval_race,
        winner_decision="approve",
        loser_decision="approve",
        winner_actor=winner_actor,
        loser_actor=loser_actor,
    )
    persisted = await _load_persisted_result(approval_race)

    assert isinstance(winner, ApprovalDecisionResponse)
    assert isinstance(loser, ApprovalDecisionResponse)
    assert winner == loser
    assert persisted.approval.status == "approved"
    assert persisted.approval.decision_actor == winner_actor
    assert persisted.approval.decision_request_id == "req_p1_04_winner_approve"
    assert len(persisted.mutations) == 1
    assert len(persisted.traces) == 1
    assert persisted.traces[0].category == "mutation.mock_credit_or_refund"
    assert persisted.traces[0].error_state is None


@pytest.mark.asyncio
async def test_concurrent_approve_wins_and_reject_conflicts(
    approval_race: ApprovalRaceFixture,
) -> None:
    winner_actor = _actor("winner-approver", "Winner Approver", "approver")

    winner, loser = await _run_locked_race(
        approval_race,
        winner_decision="approve",
        loser_decision="reject",
        winner_actor=winner_actor,
        loser_actor=_actor("loser-admin", "Loser Admin", "admin"),
    )
    persisted = await _load_persisted_result(approval_race)

    assert isinstance(winner, ApprovalDecisionResponse)
    assert isinstance(loser, MeterDeskAPIError)
    assert loser.status_code == 409
    assert loser.code == "approval.terminal_conflict"
    assert persisted.approval.status == "approved"
    assert persisted.approval.decision_actor == winner_actor
    assert persisted.approval.decision_request_id == "req_p1_04_winner_approve"
    assert len(persisted.mutations) == 1
    assert len(persisted.traces) == 1
    assert persisted.traces[0].error_state is None


@pytest.mark.asyncio
async def test_concurrent_reject_wins_and_approve_records_blocked_trace(
    approval_race: ApprovalRaceFixture,
) -> None:
    winner_actor = _actor("winner-admin", "Winner Admin", "admin")

    winner, loser = await _run_locked_race(
        approval_race,
        winner_decision="reject",
        loser_decision="approve",
        winner_actor=winner_actor,
        loser_actor=_actor("loser-approver", "Loser Approver", "approver"),
    )
    persisted = await _load_persisted_result(approval_race)

    assert isinstance(winner, ApprovalDecisionResponse)
    assert isinstance(loser, MeterDeskAPIError)
    assert loser.status_code == 409
    assert loser.code == "approval.terminal_conflict"
    assert persisted.approval.status == "rejected"
    assert persisted.approval.decision_actor == winner_actor
    assert persisted.approval.decision_request_id == "req_p1_04_winner_reject"
    assert persisted.mutations == []
    assert len(persisted.traces) == 1
    assert persisted.traces[0].category == "mutation.mock_credit_or_refund"
    assert persisted.traces[0].error_state == "approval.terminal_conflict"
    assert persisted.traces[0].governance_metadata["gate_result"] == "blocked"


async def _run_locked_race(
    race: ApprovalRaceFixture,
    *,
    winner_decision: str,
    loser_decision: str,
    winner_actor: ApprovalDecisionActor,
    loser_actor: ApprovalDecisionActor,
) -> tuple[
    ApprovalDecisionResponse | MeterDeskAPIError, ApprovalDecisionResponse | MeterDeskAPIError
]:
    async with (
        race.runtime.session_factory() as winner_session,
        race.runtime.session_factory() as loser_session,
        race.runtime.session_factory() as monitor_session,
    ):
        locked = (
            await winner_session.execute(
                select(ApprovalRequest)
                .where(ApprovalRequest.id == race.approval_id)
                .with_for_update()
            )
        ).scalar_one()
        assert locked.status == "pending"

        loser_pid = (await loser_session.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        loser_task = asyncio.create_task(
            _capture_decision(
                ApprovalDecisionService(SqlAlchemyMeterDeskRepository(loser_session)),
                decision=loser_decision,
                approval_id=race.approval_id,
                actor=loser_actor,
                request_id=f"req_p1_04_loser_{loser_decision}",
            )
        )
        try:
            await _wait_for_lock_wait(monitor_session, loser_pid)
            winner = await _capture_decision(
                ApprovalDecisionService(SqlAlchemyMeterDeskRepository(winner_session)),
                decision=winner_decision,
                approval_id=race.approval_id,
                actor=winner_actor,
                request_id=f"req_p1_04_winner_{winner_decision}",
            )
            loser = await asyncio.wait_for(loser_task, timeout=5)
        finally:
            if not loser_task.done():
                loser_task.cancel()
                await asyncio.gather(loser_task, return_exceptions=True)

    return winner, loser


async def _capture_decision(
    service: ApprovalDecisionService,
    *,
    decision: str,
    approval_id: str,
    actor: ApprovalDecisionActor,
    request_id: str,
) -> ApprovalDecisionResponse | MeterDeskAPIError:
    try:
        if decision == "approve":
            return await service.approve(
                approval_id,
                decision_actor=actor,
                decision_request_id=request_id,
                decision_note=f"{actor.display_name} approved the P1-04 race.",
            )
        return await service.reject(
            approval_id,
            decision_actor=actor,
            decision_request_id=request_id,
            decision_note=f"{actor.display_name} rejected the P1-04 race.",
        )
    except MeterDeskAPIError as error:
        return error


async def _wait_for_lock_wait(monitor_session, backend_pid: int) -> None:
    async with asyncio.timeout(5):
        while True:
            wait_event_type = (
                await monitor_session.execute(
                    text("SELECT wait_event_type FROM pg_stat_activity WHERE pid = :backend_pid"),
                    {"backend_pid": backend_pid},
                )
            ).scalar_one()
            if wait_event_type == "Lock":
                return
            await asyncio.sleep(0.01)


async def _load_persisted_result(race: ApprovalRaceFixture) -> PersistedRaceResult:
    async with race.runtime.session_factory() as session:
        repository = SqlAlchemyMeterDeskRepository(session)
        approval = await repository.get_approval(race.approval_id)
        mutations = list(
            (
                await session.execute(
                    select(MockMutation).where(MockMutation.approval_request_id == race.approval_id)
                )
            ).scalars()
        )
        traces = await repository.list_traces(race.run_id)

    assert approval is not None
    assert traces is not None
    return PersistedRaceResult(
        approval=approval,
        mutations=[_mutation_summary(mutation) for mutation in mutations],
        traces=traces,
    )


def _mutation_summary(mutation: MockMutation) -> MockMutationSummary:
    return MockMutationSummary.model_validate(
        {
            "id": mutation.id,
            "ticket_id": mutation.ticket_id,
            "approval_request_id": mutation.approval_request_id,
            "agent_run_id": mutation.agent_run_id,
            "mutation_type": mutation.mutation_type,
            "status": mutation.status,
            "amount": {
                "amount_cents": mutation.amount_cents,
                "currency": mutation.currency,
                "display": mutation.amount_display,
            },
            "reason": mutation.reason,
            "action_metadata": mutation.action_metadata,
            "action_fingerprint": mutation.action_fingerprint,
            "executed_at": mutation.executed_at,
            "executed_at_display": mutation.executed_at_display,
        }
    )


def _actor(subject: str, display_name: str, role: str) -> ApprovalDecisionActor:
    return ApprovalDecisionActor(
        subject=subject,
        display_name=display_name,
        role=role,
        source="demo_session",
    )
