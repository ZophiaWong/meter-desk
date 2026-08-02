from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status

from meterdesk_api.agent.approvals import ApprovalDecisionError, ApprovalDecisionService
from meterdesk_api.agent.compliance import RunComplianceChecker
from meterdesk_api.agent.governance import ToolPolicy, list_tool_policy_summaries
from meterdesk_api.agent.orchestrator import AgentLoopError, AgentRunOrchestrator
from meterdesk_api.agent.provider import AgentResolutionProvider
from meterdesk_api.agent.runtime import (
    get_agent_provider,
    get_optional_agent_provider,
    get_optional_eval_judge,
)
from meterdesk_api.auth import (
    get_authenticated_principal,
    require_agent_run,
    require_approval_decision,
    require_eval_run,
)
from meterdesk_api.decision_summary import build_agent_decision_summary
from meterdesk_api.eval.judge import EvalDraftJudge
from meterdesk_api.eval.regression import EvalRegressionService
from meterdesk_api.eval.runner import EvalCaseNotFound, EvalRunner
from meterdesk_api.repositories import get_repository
from meterdesk_api.schemas import (
    AgentDecisionSummary,
    AgentRunSummary,
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalSummary,
    BillingEvidence,
    EvalCaseSummary,
    EvalRegressionSummary,
    EvalResultSnapshotSummary,
    EvalResultSummary,
    EvalRunSummary,
    MockMutationSummary,
    RunComplianceResult,
    TicketDetail,
    TicketSummary,
    ToolTraceSummary,
)

router = APIRouter(
    tags=["m3 resources"],
    dependencies=[Depends(get_authenticated_principal)],
)
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


@router.get("/tickets/{ticket_id}/decision-summary", response_model=AgentDecisionSummary)
async def get_decision_summary(
    ticket_id: str,
    repository=REPOSITORY_DEPENDENCY,
) -> AgentDecisionSummary:
    summary = await build_agent_decision_summary(repository, ticket_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return summary


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
    dependencies=[Depends(require_agent_run)],
)
async def start_agent_run(
    ticket_id: str,
    repository=REPOSITORY_DEPENDENCY,
    provider: AgentResolutionProvider = PROVIDER_DEPENDENCY,
) -> AgentRunSummary:
    orchestrator = AgentRunOrchestrator(repository=repository, provider=provider)
    try:
        run = await orchestrator.run_ticket(ticket_id)
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


@router.get("/agent-runs/{agent_run_id}/compliance", response_model=RunComplianceResult)
async def get_run_compliance(
    agent_run_id: str,
    repository=REPOSITORY_DEPENDENCY,
) -> RunComplianceResult:
    result = await RunComplianceChecker(repository).check(agent_run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return result


@router.get("/approvals", response_model=list[ApprovalSummary])
async def list_approvals(
    status: Literal["pending", "approved", "rejected", "all"] = "pending",
    ticket_id: str | None = None,
    repository=REPOSITORY_DEPENDENCY,
) -> list[ApprovalSummary]:
    status_filter = None if status == "all" else status
    return await repository.list_approvals(status=status_filter, ticket_id=ticket_id)


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=ApprovalDecisionResponse,
    dependencies=[Depends(require_approval_decision)],
)
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


@router.post(
    "/approvals/{approval_id}/reject",
    response_model=ApprovalDecisionResponse,
    dependencies=[Depends(require_approval_decision)],
)
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


@router.get("/eval-runs", response_model=list[EvalRunSummary])
async def list_eval_runs(
    repository=REPOSITORY_DEPENDENCY,
) -> list[EvalRunSummary]:
    return await repository.list_eval_runs()


@router.get("/eval-regression/summary", response_model=EvalRegressionSummary)
async def get_eval_regression_summary(
    repository=REPOSITORY_DEPENDENCY,
) -> EvalRegressionSummary:
    return await EvalRegressionService(repository).latest_summary()


@router.get("/eval-runs/{eval_run_id}/comparison", response_model=EvalRegressionSummary)
async def get_eval_run_comparison(
    eval_run_id: str,
    repository=REPOSITORY_DEPENDENCY,
) -> EvalRegressionSummary:
    if await repository.get_eval_run(eval_run_id) is None:
        raise HTTPException(status_code=404, detail="Eval run not found")
    return await EvalRegressionService(repository).summary_for_run(eval_run_id)


@router.get("/eval-cases/{case_id}/history", response_model=list[EvalResultSnapshotSummary])
async def list_eval_case_history(
    case_id: str,
    repository=REPOSITORY_DEPENDENCY,
) -> list[EvalResultSnapshotSummary]:
    if await repository.get_eval_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Eval case not found")
    snapshots = await repository.list_eval_result_snapshots(case_id=case_id)
    return list(reversed(snapshots))


@router.post(
    "/eval-cases/{case_id}/run",
    response_model=EvalResultSummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_eval_run)],
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
    dependencies=[Depends(require_eval_run)],
)
async def run_all_eval_cases(
    repository=REPOSITORY_DEPENDENCY,
    provider: AgentResolutionProvider | None = OPTIONAL_PROVIDER_DEPENDENCY,
    judge: EvalDraftJudge | None = OPTIONAL_JUDGE_DEPENDENCY,
) -> list[EvalResultSummary]:
    runner = EvalRunner(repository=repository, provider=provider, judge=judge)
    return await runner.run_all()
