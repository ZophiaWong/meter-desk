from __future__ import annotations

from meterdesk_api.repositories import MeterDeskRepository
from meterdesk_api.schemas import ApprovalDecisionResponse


class ApprovalDecisionError(Exception):
    status_code = 400


class ApprovalConflictError(ApprovalDecisionError):
    status_code = 409


class ApprovalNotFoundError(ApprovalDecisionError):
    status_code = 404


class ApprovalDecisionService:
    def __init__(self, repository: MeterDeskRepository) -> None:
        self._repository = repository

    async def approve(
        self,
        approval_id: str,
        *,
        decided_by: str,
        decision_note: str | None,
    ) -> ApprovalDecisionResponse:
        approval = await self._repository.get_approval(approval_id)
        if approval is None:
            raise ApprovalNotFoundError("Approval request not found")
        if approval.status == "rejected":
            raise ApprovalConflictError("Rejected approval requests cannot be approved")
        if approval.status == "approved":
            mutation = await self._repository.get_mock_mutation_by_approval(approval_id)
            return ApprovalDecisionResponse(approval=approval, mock_mutation=mutation)

        approval, mutation = await self._repository.approve_request(
            approval_id=approval_id,
            decided_by=decided_by,
            decision_note=decision_note,
        )
        return ApprovalDecisionResponse(approval=approval, mock_mutation=mutation)

    async def reject(
        self,
        approval_id: str,
        *,
        decided_by: str,
        decision_note: str | None,
    ) -> ApprovalDecisionResponse:
        approval = await self._repository.get_approval(approval_id)
        if approval is None:
            raise ApprovalNotFoundError("Approval request not found")
        if approval.status == "approved":
            raise ApprovalConflictError("Approved approval requests cannot be rejected")
        if approval.status == "rejected":
            return ApprovalDecisionResponse(approval=approval, mock_mutation=None)

        approval = await self._repository.reject_request(
            approval_id=approval_id,
            decided_by=decided_by,
            decision_note=decision_note,
        )
        return ApprovalDecisionResponse(approval=approval, mock_mutation=None)
