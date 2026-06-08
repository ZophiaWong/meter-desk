from fastapi import APIRouter, Depends, HTTPException

from meterdesk_api.repositories import get_repository
from meterdesk_api.schemas import (
    AgentRunSummary,
    ApprovalSummary,
    BillingEvidence,
    EvalCaseSummary,
    EvalResultSummary,
    MockMutationSummary,
    TicketDetail,
    TicketSummary,
    ToolTraceSummary,
)

router = APIRouter(tags=["m2 resources"])
REPOSITORY_DEPENDENCY = Depends(get_repository)


@router.get("/tickets", response_model=list[TicketSummary])
async def list_tickets(
    repository=REPOSITORY_DEPENDENCY,
) -> list[TicketSummary]:
    return await repository.list_tickets()


@router.get("/tickets/{ticket_id}", response_model=TicketDetail)
async def get_ticket(
    ticket_id: str,
    repository=REPOSITORY_DEPENDENCY,
) -> TicketDetail:
    ticket = await repository.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("/tickets/{ticket_id}/billing-evidence", response_model=BillingEvidence)
async def get_billing_evidence(
    ticket_id: str,
    repository=REPOSITORY_DEPENDENCY,
) -> BillingEvidence:
    evidence = await repository.get_billing_evidence(ticket_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return evidence


@router.get("/tickets/{ticket_id}/agent-runs", response_model=list[AgentRunSummary])
async def list_agent_runs(
    ticket_id: str,
    repository=REPOSITORY_DEPENDENCY,
) -> list[AgentRunSummary]:
    runs = await repository.list_agent_runs(ticket_id)
    if runs is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return runs


@router.get("/agent-runs/{agent_run_id}/traces", response_model=list[ToolTraceSummary])
async def list_traces(
    agent_run_id: str,
    repository=REPOSITORY_DEPENDENCY,
) -> list[ToolTraceSummary]:
    traces = await repository.list_traces(agent_run_id)
    if traces is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return traces


@router.get("/approvals", response_model=list[ApprovalSummary])
async def list_approvals(
    repository=REPOSITORY_DEPENDENCY,
) -> list[ApprovalSummary]:
    return await repository.list_approvals(status="pending")


@router.get("/mock-mutations", response_model=list[MockMutationSummary])
async def list_mock_mutations(
    repository=REPOSITORY_DEPENDENCY,
) -> list[MockMutationSummary]:
    return await repository.list_mock_mutations()


@router.get("/eval-cases", response_model=list[EvalCaseSummary])
async def list_eval_cases(
    repository=REPOSITORY_DEPENDENCY,
) -> list[EvalCaseSummary]:
    return await repository.list_eval_cases()


@router.get("/eval-results", response_model=list[EvalResultSummary])
async def list_eval_results(
    repository=REPOSITORY_DEPENDENCY,
) -> list[EvalResultSummary]:
    return await repository.list_eval_results()
