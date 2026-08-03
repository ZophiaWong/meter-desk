from __future__ import annotations

from meterdesk_api.agent.governance import GovernanceKernel
from meterdesk_api.errors import MeterDeskAPIError
from meterdesk_api.repositories import MeterDeskRepository
from meterdesk_api.schemas import ApprovalDecisionActor, ApprovalDecisionResponse


class ApprovalDecisionError(MeterDeskAPIError):
    status_code = 400
    code = "approval.decision_error"
    message = "Approval decision failed."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            status_code=self.status_code,
            code=self.code,
            message=message or self.message,
        )


class ApprovalConflictError(ApprovalDecisionError):
    status_code = 409
    code = "approval.terminal_conflict"
    message = "Approval request is already terminal."


class ApprovalNotFoundError(ApprovalDecisionError):
    status_code = 404
    code = "approval.not_found"
    message = "Approval request not found."


class ApprovalDecisionService:
    def __init__(self, repository: MeterDeskRepository) -> None:
        self._repository = repository

    async def approve(
        self,
        approval_id: str,
        *,
        decision_actor: ApprovalDecisionActor,
        decision_request_id: str,
        decision_note: str | None,
    ) -> ApprovalDecisionResponse:
        return await GovernanceKernel(self._repository).execute_approved_mock_refund(
            approval_id=approval_id,
            decision_actor=decision_actor,
            decision_request_id=decision_request_id,
            decision_note=decision_note,
        )

    async def reject(
        self,
        approval_id: str,
        *,
        decision_actor: ApprovalDecisionActor,
        decision_request_id: str,
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
            decision_actor=decision_actor,
            decision_request_id=decision_request_id,
            decision_note=decision_note,
        )
        return ApprovalDecisionResponse(approval=approval, mock_mutation=None)
