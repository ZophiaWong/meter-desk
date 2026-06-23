from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status

from meterdesk_api.agent.approvals import ApprovalDecisionError, ApprovalDecisionService
from meterdesk_api.agent.governance import ToolPolicy, list_tool_policy_summaries
from meterdesk_api.agent.orchestrator import AgentLoopError, AgentRunOrchestrator
from meterdesk_api.agent.provider import AgentResolutionProvider
from meterdesk_api.agent.runtime import (
    get_agent_provider,
    get_optional_agent_provider,
    get_optional_eval_judge,
)
from meterdesk_api.eval.judge import EvalDraftJudge
from meterdesk_api.eval.runner import EvalCaseNotFound, EvalRunner
from meterdesk_api.repositories import get_repository
from meterdesk_api.schemas import (
    AgentRunSummary,
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalSummary,
    BillingEvidence,
    EvalCaseSummary,
    EvalResultSummary,
    MockMutationSummary,
    TicketDetail,
    TicketSummary,
    ToolTraceSummary,
)

router = APIRouter(tags=["m3 resources"])
REPOSITORY_DEPENDENCY = Depends(get_repository)
PROVIDER_DEPENDENCY = Depends(get_agent_provider)
OPTIONAL_PROVIDER_DEPENDENCY = Depends(get_optional_agent_provider)
OPTIONAL_JUDGE_DEPENDENCY = Depends(get_optional_eval_judge)


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


@router.post(
    "/tickets/{ticket_id}/agent-runs",
    response_model=AgentRunSummary,
    status_code=status.HTTP_201_CREATED,
)
async def start_agent_run(
    ticket_id: str,
    repository=REPOSITORY_DEPENDENCY,
    provider: AgentResolutionProvider = PROVIDER_DEPENDENCY,
) -> AgentRunSummary:
    orchestrator = AgentRunOrchestrator(repository=repository, provider=provider)
    try:
        run = await orchestrator.run_duplicate_charge(ticket_id)
    except AgentLoopError as error:
        raise error
    if run is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return run


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
    status: Literal["pending", "approved", "rejected", "all"] = "pending",
    ticket_id: str | None = None,
    repository=REPOSITORY_DEPENDENCY,
) -> list[ApprovalSummary]:
    status_filter = None if status == "all" else status
    return await repository.list_approvals(status=status_filter, ticket_id=ticket_id)


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalDecisionResponse)
async def approve_request(
    approval_id: str,
    decision: ApprovalDecisionRequest,
    repository=REPOSITORY_DEPENDENCY,
) -> ApprovalDecisionResponse:
    service = ApprovalDecisionService(repository)
    try:
        return await service.approve(
            approval_id,
            decided_by=decision.decided_by,
            decision_note=decision.decision_note,
        )
    except ApprovalDecisionError as error:
        raise error


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalDecisionResponse)
async def reject_request(
    approval_id: str,
    decision: ApprovalDecisionRequest,
    repository=REPOSITORY_DEPENDENCY,
) -> ApprovalDecisionResponse:
    service = ApprovalDecisionService(repository)
    try:
        return await service.reject(
            approval_id,
            decided_by=decision.decided_by,
            decision_note=decision.decision_note,
        )
    except ApprovalDecisionError as error:
        raise error


@router.get("/mock-mutations", response_model=list[MockMutationSummary])
async def list_mock_mutations(
    ticket_id: str | None = None,
    repository=REPOSITORY_DEPENDENCY,
) -> list[MockMutationSummary]:
    return await repository.list_mock_mutations(ticket_id=ticket_id)


@router.get("/governance/tool-policies", response_model=list[ToolPolicy])
async def list_governance_tool_policies() -> list[ToolPolicy]:
    return list_tool_policy_summaries()


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


@router.post(
    "/eval-cases/{case_id}/run",
    response_model=EvalResultSummary,
    status_code=status.HTTP_201_CREATED,
)
async def run_eval_case(
    case_id: str,
    repository=REPOSITORY_DEPENDENCY,
    provider: AgentResolutionProvider | None = OPTIONAL_PROVIDER_DEPENDENCY,
    judge: EvalDraftJudge | None = OPTIONAL_JUDGE_DEPENDENCY,
) -> EvalResultSummary:
    runner = EvalRunner(repository=repository, provider=provider, judge=judge)
    try:
        return await runner.run_case(case_id)
    except EvalCaseNotFound as error:
        raise HTTPException(status_code=404, detail="Eval case not found") from error


@router.post(
    "/eval-runs",
    response_model=list[EvalResultSummary],
    status_code=status.HTTP_201_CREATED,
)
async def run_all_eval_cases(
    repository=REPOSITORY_DEPENDENCY,
    provider: AgentResolutionProvider | None = OPTIONAL_PROVIDER_DEPENDENCY,
    judge: EvalDraftJudge | None = OPTIONAL_JUDGE_DEPENDENCY,
) -> list[EvalResultSummary]:
    runner = EvalRunner(repository=repository, provider=provider, judge=judge)
    return await runner.run_all()
