from __future__ import annotations

import pytest

from meterdesk_api.errors import MeterDeskAPIError
from meterdesk_api.repositories import InMemoryMeterDeskRepository
from meterdesk_api.schemas import ApprovalDecisionActor
from meterdesk_api.seed_data import build_seed_repository


def _approver() -> ApprovalDecisionActor:
    return ApprovalDecisionActor(
        subject="approver-1",
        display_name="Approver One",
        role="approver",
        source="demo_session",
    )


def _approval_payload() -> dict[str, object]:
    return {
        "title": "Refund pending approval",
        "action_type": "original_refund",
        "amount_cents": 124800,
        "amount_display": "$1,248.00",
        "currency": "USD",
        "reason": "Duplicate captured charge.",
        "blocker": "Mutation blocked until human approval",
        "policy_citation": "REFUND-DUP-001 v2026.02",
        "evidence_refs": ["invoice INV-2026-0418"],
        "action_metadata": {"target_charge_id": "ch_2026_0418_B"},
    }


async def _fresh_repository() -> InMemoryMeterDeskRepository:
    repository = build_seed_repository()
    await repository.reset_demo_live_state("TCK-1042")
    return repository


@pytest.mark.asyncio
async def test_start_replay_and_retry_keep_one_workflow_cycle() -> None:
    repository = await _fresh_repository()

    first = await repository.start_or_replay_run(
        ticket_id="TCK-1042",
        idempotency_key="request-1",
        source="test",
        model="test-model",
        prompt_version="test-v1",
    )
    replay = await repository.start_or_replay_run(
        ticket_id="TCK-1042",
        idempotency_key="request-1",
        source="test",
        model="test-model",
        prompt_version="test-v1",
    )

    assert first.replayed is False
    assert replay.replayed is True
    assert replay.run.id == first.run.id
    assert len(await repository.list_workflows("TCK-1042")) == 1

    await repository.fail_run(
        agent_run_id=first.run.id,
        error_code="provider.draft_failed",
        error_state="provider unavailable",
    )
    retry = await repository.start_or_replay_run(
        ticket_id="TCK-1042",
        idempotency_key="request-2",
        source="test",
        model="test-model",
        prompt_version="test-v1",
    )
    workflows = await repository.list_workflows("TCK-1042")

    assert retry.replayed is False
    assert retry.run.id != first.run.id
    assert retry.run.workflow_id == first.run.workflow_id
    assert workflows[-1].status == "investigating"
    transitions = await repository.list_workflow_transitions(workflows[-1].id)
    assert [item.to_status for item in transitions] == [
        "investigating",
        "needs_retry",
        "investigating",
    ]


@pytest.mark.asyncio
async def test_finalize_approval_and_execute_commit_one_consistent_workflow() -> None:
    repository = await _fresh_repository()
    started = await repository.start_or_replay_run(
        ticket_id="TCK-1042",
        idempotency_key="request-approval",
        source="test",
        model="test-model",
        prompt_version="test-v1",
    )

    run = await repository.finalize_run(
        agent_run_id=started.run.id,
        final_outcome="confirmed_duplicate_charge",
        internal_resolution="Refund after approval.",
        customer_reply="Draft only.",
        target_status="awaiting_approval",
        reason_code="decision.approval_required",
        reason_detail="Human approval is required.",
        final_trace={
            "category": "draft.resolution",
            "risk": "Low",
            "label": "Drafted resolution",
            "evidence_refs": ["invoice INV-2026-0418"],
            "policy_refs": ["REFUND-DUP-001 v2026.02"],
            "approval_refs": [],
        },
        approval=_approval_payload(),
        approval_trace={
            "category": "approval.create_request",
            "risk": "Medium",
            "label": "Created approval",
            "evidence_refs": ["invoice INV-2026-0418"],
            "policy_refs": ["REFUND-DUP-001 v2026.02"],
            "approval_refs": ["pending"],
        },
    )

    workflow = (await repository.list_workflows("TCK-1042"))[-1]
    approval = (await repository.list_approvals(ticket_id="TCK-1042"))[0]
    traces = await repository.list_traces(run.id)
    assert run.status == "completed"
    assert workflow.status == "awaiting_approval"
    assert approval.workflow_id == workflow.id
    assert [trace.sequence for trace in traces] == [1, 2]
    assert traces[-1].approval_refs == [approval.id]

    result = await repository.approve_and_execute(
        approval_id=approval.id,
        decision_actor=_approver(),
        decision_request_id="decision-1",
        decision_note="Approved.",
        mutation_trace={
            "category": "mutation.mock_refund",
            "risk": "High",
            "label": "Executed mock refund",
            "evidence_refs": approval.evidence_refs,
            "policy_refs": [approval.policy_citation],
            "approval_refs": [approval.id],
        },
    )
    workflow = await repository.get_workflow(workflow.id)
    assert result.executed_now is True
    assert result.approval.status == "approved"
    assert result.mutation.workflow_id == workflow.id
    assert workflow.status == "mock_executed"
    assert len(await repository.list_mock_mutations("TCK-1042")) == 1
    assert [item.to_status for item in await repository.list_workflow_transitions(workflow.id)] == [
        "investigating",
        "awaiting_approval",
        "mock_executed",
    ]


@pytest.mark.asyncio
async def test_finalize_validation_failure_leaves_run_workflow_and_artifacts_unchanged() -> None:
    repository = await _fresh_repository()
    started = await repository.start_or_replay_run(
        ticket_id="TCK-1042",
        idempotency_key="request-atomic-failure",
        source="test",
        model="test-model",
        prompt_version="test-v1",
    )

    with pytest.raises(MeterDeskAPIError) as error:
        await repository.finalize_run(
            agent_run_id=started.run.id,
            final_outcome="confirmed_duplicate_charge",
            internal_resolution="Refund after approval.",
            customer_reply="Draft only.",
            target_status="awaiting_approval",
            reason_code="decision.approval_required",
            final_trace={
                "category": "draft.resolution",
                "risk": "Low",
                "label": "Should not persist",
            },
        )

    assert error.value.code == "approval.missing"
    assert (await repository.get_agent_run(started.run.id)).status == "running"
    assert (await repository.get_workflow(started.run.workflow_id)).status == "investigating"
    assert await repository.list_approvals(ticket_id="TCK-1042") == []
    assert await repository.list_traces(started.run.id) == []


@pytest.mark.asyncio
async def test_cancel_withdraws_pending_approval_and_blocks_late_decision() -> None:
    repository = await _fresh_repository()
    started = await repository.start_or_replay_run(
        ticket_id="TCK-1042",
        idempotency_key="request-cancel",
        source="test",
        model="test-model",
        prompt_version="test-v1",
    )
    await repository.finalize_run(
        agent_run_id=started.run.id,
        final_outcome="confirmed_duplicate_charge",
        internal_resolution="Refund after approval.",
        customer_reply="Draft only.",
        target_status="awaiting_approval",
        reason_code="decision.approval_required",
        approval=_approval_payload(),
    )
    approval = (await repository.list_approvals(ticket_id="TCK-1042"))[0]
    workflow = (await repository.list_workflows("TCK-1042"))[-1]

    cancelled = await repository.cancel_workflow(
        workflow_id=workflow.id,
        actor=ApprovalDecisionActor(
            subject="support-1",
            display_name="Support One",
            role="support_operator",
            source="demo_session",
        ),
        request_id="cancel-1",
        reason="Customer withdrew the request.",
    )

    assert cancelled.status == "cancelled"
    assert (await repository.get_approval(approval.id)).status == "withdrawn"
    with pytest.raises(MeterDeskAPIError) as error:
        await repository.approve_and_execute(
            approval_id=approval.id,
            decision_actor=_approver(),
            decision_request_id="late-approval",
            decision_note=None,
        )
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_reject_is_terminal_and_does_not_create_mutation() -> None:
    repository = await _fresh_repository()
    started = await repository.start_or_replay_run(
        ticket_id="TCK-1042",
        idempotency_key="request-reject",
        source="test",
        model="test-model",
        prompt_version="test-v1",
    )
    await repository.finalize_run(
        agent_run_id=started.run.id,
        final_outcome="confirmed_duplicate_charge",
        internal_resolution="Refund after approval.",
        customer_reply="Draft only.",
        target_status="awaiting_approval",
        reason_code="decision.approval_required",
        approval=_approval_payload(),
    )
    approval = (await repository.list_approvals(ticket_id="TCK-1042"))[0]
    rejected = await repository.reject_approval(
        approval_id=approval.id,
        decision_actor=_approver(),
        decision_request_id="reject-1",
        decision_note="Insufficient customer confirmation.",
    )

    assert rejected.status == "rejected"
    assert (await repository.list_mock_mutations("TCK-1042")) == []
    assert (await repository.list_workflows("TCK-1042"))[-1].status == "rejected"
