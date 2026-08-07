"""Case workflow state and transition rules for P0-03.

The workflow is the durable aggregate for one investigation cycle.  An
``AgentRun`` is only an attempt inside that cycle, so retries never invent a
second source of truth for the ticket's state.  This module intentionally
contains no database code; repositories use these rules when executing the
small, atomic commands defined by the P0-03 contract.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class WorkflowStatus(StrEnum):
    INVESTIGATING = "investigating"
    NEEDS_RETRY = "needs_retry"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED_NO_ACTION = "completed_no_action"
    REJECTED = "rejected"
    MOCK_EXECUTED = "mock_executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


INITIAL_WORKFLOW_STATUS: Final[WorkflowStatus] = WorkflowStatus.INVESTIGATING

TERMINAL_WORKFLOW_STATUSES: Final[set[WorkflowStatus]] = {
    WorkflowStatus.COMPLETED_NO_ACTION,
    WorkflowStatus.REJECTED,
    WorkflowStatus.MOCK_EXECUTED,
    WorkflowStatus.FAILED,
    WorkflowStatus.CANCELLED,
}

WORKFLOW_TRANSITIONS: Final[dict[WorkflowStatus, frozenset[WorkflowStatus]]] = {
    WorkflowStatus.INVESTIGATING: frozenset(
        {
            WorkflowStatus.NEEDS_RETRY,
            WorkflowStatus.AWAITING_APPROVAL,
            WorkflowStatus.COMPLETED_NO_ACTION,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        }
    ),
    WorkflowStatus.NEEDS_RETRY: frozenset(
        {
            WorkflowStatus.INVESTIGATING,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        }
    ),
    WorkflowStatus.AWAITING_APPROVAL: frozenset(
        {
            WorkflowStatus.MOCK_EXECUTED,
            WorkflowStatus.REJECTED,
            WorkflowStatus.CANCELLED,
        }
    ),
    WorkflowStatus.COMPLETED_NO_ACTION: frozenset(),
    WorkflowStatus.REJECTED: frozenset(),
    WorkflowStatus.MOCK_EXECUTED: frozenset(),
    WorkflowStatus.FAILED: frozenset(),
    WorkflowStatus.CANCELLED: frozenset(),
}


class WorkflowTransitionError(ValueError):
    """Raised when a workflow command attempts an illegal state transition."""

    def __init__(self, source: str | None, target: str) -> None:
        source_label = "initial" if source is None else source
        super().__init__(f"Illegal workflow transition: {source_label} -> {target}")
        self.source = source
        self.target = target


def _coerce_status(status: str | WorkflowStatus) -> WorkflowStatus:
    if isinstance(status, WorkflowStatus):
        return status
    return WorkflowStatus(status)


def can_transition(
    source: str | WorkflowStatus | None,
    target: str | WorkflowStatus,
) -> bool:
    """Return whether ``source -> target`` is legal.

    ``None`` denotes a new workflow before its first transition.  The only
    legal initial state is ``investigating``.
    """

    try:
        target_status = _coerce_status(target)
        if source is None:
            return target_status is INITIAL_WORKFLOW_STATUS
        source_status = _coerce_status(source)
    except ValueError:
        return False
    return target_status in WORKFLOW_TRANSITIONS[source_status]


def transition_workflow_status(
    source: str | WorkflowStatus | None,
    target: str | WorkflowStatus,
) -> WorkflowStatus:
    """Validate and return the target status for a workflow transition."""

    if not can_transition(source, target):
        raise WorkflowTransitionError(source, str(target))
    return _coerce_status(target)


class CaseWorkflowService:
    """Small domain façade shared by API and repository command paths.

    Persistence is deliberately supplied by the caller.  Keeping validation
    here prevents route/orchestrator code from growing separate transition
    matrices while allowing the SQL repository to own transaction boundaries.
    """

    @staticmethod
    def validate_transition(
        source: str | WorkflowStatus | None,
        target: str | WorkflowStatus,
    ) -> WorkflowStatus:
        return transition_workflow_status(source, target)

    @staticmethod
    def is_terminal(status: str | WorkflowStatus) -> bool:
        return _coerce_status(status) in TERMINAL_WORKFLOW_STATUSES

    @staticmethod
    def initial_status() -> WorkflowStatus:
        return INITIAL_WORKFLOW_STATUS
