import pytest

from meterdesk_api.workflows import (
    TERMINAL_WORKFLOW_STATUSES,
    WorkflowStatus,
    WorkflowTransitionError,
    can_transition,
    transition_workflow_status,
)


def test_workflow_statuses_are_the_p0_03_vocabulary() -> None:
    assert {status.value for status in WorkflowStatus} == {
        "investigating",
        "needs_retry",
        "awaiting_approval",
        "completed_no_action",
        "rejected",
        "mock_executed",
        "failed",
        "cancelled",
    }


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("investigating", "needs_retry"),
        ("investigating", "awaiting_approval"),
        ("investigating", "completed_no_action"),
        ("investigating", "failed"),
        ("investigating", "cancelled"),
        ("needs_retry", "investigating"),
        ("needs_retry", "failed"),
        ("needs_retry", "cancelled"),
        ("awaiting_approval", "mock_executed"),
        ("awaiting_approval", "rejected"),
        ("awaiting_approval", "cancelled"),
    ],
)
def test_legal_workflow_transitions_are_accepted(source: str, target: str) -> None:
    assert can_transition(source, target)
    assert transition_workflow_status(source, target) == WorkflowStatus(target)


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("investigating", "mock_executed"),
        ("investigating", "rejected"),
        ("needs_retry", "awaiting_approval"),
        ("awaiting_approval", "completed_no_action"),
        ("completed_no_action", "investigating"),
        ("rejected", "investigating"),
        ("mock_executed", "awaiting_approval"),
        ("failed", "investigating"),
        ("cancelled", "investigating"),
    ],
)
def test_illegal_workflow_transitions_are_rejected(source: str, target: str) -> None:
    assert not can_transition(source, target)
    with pytest.raises(WorkflowTransitionError):
        transition_workflow_status(source, target)


def test_terminal_statuses_have_no_outgoing_transitions() -> None:
    assert TERMINAL_WORKFLOW_STATUSES == {
        WorkflowStatus.COMPLETED_NO_ACTION,
        WorkflowStatus.REJECTED,
        WorkflowStatus.MOCK_EXECUTED,
        WorkflowStatus.FAILED,
        WorkflowStatus.CANCELLED,
    }
    for status in TERMINAL_WORKFLOW_STATUSES:
        assert not can_transition(status, WorkflowStatus.INVESTIGATING)


def test_technical_failure_and_valid_no_action_are_distinct() -> None:
    assert can_transition("investigating", "needs_retry")
    assert can_transition("investigating", "completed_no_action")
    assert WorkflowStatus.COMPLETED_NO_ACTION != WorkflowStatus.NEEDS_RETRY
