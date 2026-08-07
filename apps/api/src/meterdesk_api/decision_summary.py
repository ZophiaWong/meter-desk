from __future__ import annotations

from meterdesk_api.agent.compliance import RunComplianceChecker
from meterdesk_api.repositories import MeterDeskRepository
from meterdesk_api.schemas import (
    AgentDecisionSummary,
    AgentDecisionSummaryTile,
    AgentRunSummary,
    ApprovalSummary,
    BillingEvidence,
    CaseWorkflowSummary,
    DecisionSummaryState,
    MockMutationSummary,
    TicketDetail,
)


async def build_agent_decision_summary(
    repository: MeterDeskRepository,
    ticket_id: str,
) -> AgentDecisionSummary | None:
    ticket = await repository.get_ticket(ticket_id)
    evidence = await repository.get_billing_evidence(ticket_id)
    if ticket is None or evidence is None:
        return None

    runs = await repository.list_agent_runs(ticket_id)
    approvals = await repository.list_approvals(status=None, ticket_id=ticket_id)
    mutations = await repository.list_mock_mutations(ticket_id=ticket_id)
    workflows = await repository.list_workflows(ticket_id)
    workflow = workflows[-1] if workflows else None
    scoped_runs = (
        [item for item in runs if item.workflow_id == workflow.id] if workflow is not None else runs
    )
    scoped_approvals = (
        [item for item in approvals if item.workflow_id == workflow.id]
        if workflow is not None
        else approvals
    )
    scoped_mutations = (
        [item for item in mutations if item.workflow_id == workflow.id]
        if workflow is not None
        else mutations
    )
    run = scoped_runs[-1] if scoped_runs else None
    approval = scoped_approvals[-1] if scoped_approvals else None
    mutation = scoped_mutations[-1] if scoped_mutations else None
    compliance_status = None
    if run is not None:
        compliance = await RunComplianceChecker(repository).check(run.id)
        compliance_status = compliance.status if compliance is not None else None

    if ticket.scenario != "duplicate_charge":
        return _build_supporting_scenario_summary(
            ticket=ticket,
            evidence=evidence,
            run=run,
            approval=approval,
            mutation=mutation,
            workflow=workflow,
            compliance_status=compliance_status,
        )

    return _build_duplicate_charge_summary(
        ticket=ticket,
        evidence=evidence,
        run=run,
        approval=approval,
        mutation=mutation,
        workflow=workflow,
        compliance_status=compliance_status,
    )


def _build_duplicate_charge_summary(
    *,
    ticket: TicketDetail,
    evidence: BillingEvidence,
    run: AgentRunSummary | None,
    approval: ApprovalSummary | None,
    mutation: MockMutationSummary | None,
    workflow: CaseWorkflowSummary | None,
    compliance_status: str | None,
) -> AgentDecisionSummary:
    state = _summary_state(workflow=workflow, run=run, approval=approval, mutation=mutation)
    refs = _evidence_refs(evidence)

    if run is None and workflow is None:
        decision_label = "Investigation pending"
        rationale = (
            f"Billing evidence is loaded for {ticket.id}. Run the governed investigation to "
            "produce a trace-backed decision, approval gate, and customer draft."
        )
        tiles = [
            AgentDecisionSummaryTile(
                kind="decision",
                label="Decision",
                title="Investigation pending",
                body="No agent run has produced a trace-backed recommendation yet.",
                tone="neutral",
                refs=[ticket.id],
            ),
            AgentDecisionSummaryTile(
                kind="evidence",
                label="Evidence",
                title="Evidence loaded",
                body="Invoice, charge, usage, credit, and policy evidence are ready for review.",
                tone="info",
                refs=refs,
            ),
            AgentDecisionSummaryTile(
                kind="risk_gate",
                label="Risk gate",
                title="Risk gate pending",
                body=(
                    "Refund or credit mutations remain unavailable until a governed run creates "
                    "an approval request."
                ),
                tone="warning",
                refs=[],
            ),
            AgentDecisionSummaryTile(
                kind="draft",
                label="Draft",
                title="No customer draft yet",
                body="Customer-facing text will remain draft-only after the agent run.",
                tone="neutral",
                refs=[],
            ),
        ]
    elif workflow is not None and workflow.status == "needs_retry":
        decision_label = "Retry investigation"
        rationale = workflow.status_reason or "The investigation can be retried."
        tiles = [
            AgentDecisionSummaryTile(
                kind="decision",
                label="Decision",
                title="Investigation needs retry",
                body=rationale,
                tone="warning",
                refs=[run.id] if run is not None else [workflow.id],
            ),
            AgentDecisionSummaryTile(
                kind="evidence",
                label="Evidence",
                title="Evidence remains available",
                body=f"{evidence.invoice.id} and related billing records are still available.",
                tone="info",
                refs=refs,
            ),
            AgentDecisionSummaryTile(
                kind="risk_gate",
                label="Risk gate",
                title="No financial action",
                body="Retry the investigation before proposing a financial action.",
                tone="neutral",
                refs=[],
            ),
            AgentDecisionSummaryTile(
                kind="draft",
                label="Draft",
                title="Draft unavailable",
                body="The previous attempt did not produce a final customer draft.",
                tone="neutral",
                refs=[],
            ),
        ]
    elif workflow is not None and workflow.status == "investigating":
        decision_label = "Investigation running"
        rationale = (
            f"The governed investigation for {ticket.id} is running. Evidence is visible, but "
            "no decision, approval request, or customer draft has been finalized yet."
        )
        tiles = [
            AgentDecisionSummaryTile(
                kind="decision",
                label="Decision",
                title="Investigation running",
                body="The agent run has not finalized a trace-backed recommendation yet.",
                tone="info",
                refs=[run.id] if run is not None else [workflow.id],
            ),
            AgentDecisionSummaryTile(
                kind="evidence",
                label="Evidence",
                title="Evidence available",
                body=f"{evidence.invoice.id} and related billing records are available.",
                tone="info",
                refs=refs,
            ),
            AgentDecisionSummaryTile(
                kind="risk_gate",
                label="Risk gate",
                title="Risk gate pending",
                body="No refund or credit approval request has been created yet.",
                tone="warning",
                refs=[],
            ),
            AgentDecisionSummaryTile(
                kind="draft",
                label="Draft",
                title="Customer draft pending",
                body="Customer-facing text remains unavailable until the run completes.",
                tone="neutral",
                refs=[],
            ),
        ]
    elif workflow is not None and workflow.status == "failed":
        decision_label = "Investigation failed"
        rationale = (
            run.error_state
            if run is not None and run.error_state
            else "The governed investigation failed before a decision."
        )
        tiles = [
            AgentDecisionSummaryTile(
                kind="decision",
                label="Decision",
                title="No reliable decision",
                body=rationale,
                tone="danger",
                refs=[run.id] if run is not None else [workflow.id],
            ),
            AgentDecisionSummaryTile(
                kind="evidence",
                label="Evidence",
                title="Evidence remains available",
                body=f"{evidence.invoice.id} and related billing records are still available.",
                tone="info",
                refs=refs,
            ),
            AgentDecisionSummaryTile(
                kind="risk_gate",
                label="Risk gate",
                title="No approval request",
                body=(
                    "No financial action was proposed, so no refund or credit mutation is "
                    "available."
                ),
                tone="neutral",
                refs=[],
            ),
            AgentDecisionSummaryTile(
                kind="draft",
                label="Draft",
                title="No customer draft",
                body="No customer-facing draft was produced by the failed run.",
                tone="neutral",
                refs=[],
            ),
        ]
    elif workflow is not None and workflow.status == "cancelled":
        decision_label = "Investigation cancelled"
        rationale = workflow.status_reason or "The investigation was cancelled before completion."
        tiles = [
            AgentDecisionSummaryTile(
                kind="decision",
                label="Decision",
                title="Investigation cancelled",
                body=rationale,
                tone="warning",
                refs=[run.id] if run is not None else [workflow.id],
            ),
            AgentDecisionSummaryTile(
                kind="evidence",
                label="Evidence",
                title="Evidence remains available",
                body=f"{evidence.invoice.id} and related billing records remain available.",
                tone="info",
                refs=refs,
            ),
            AgentDecisionSummaryTile(
                kind="risk_gate",
                label="Risk gate",
                title="No financial action",
                body="Cancellation prevents any approval or mock mutation from executing.",
                tone="neutral",
                refs=[approval.id] if approval is not None else [],
            ),
            AgentDecisionSummaryTile(
                kind="draft",
                label="Draft",
                title="Draft not sent",
                body="No customer-facing message is sent by a cancelled workflow.",
                tone="neutral",
                refs=[],
            ),
        ]
    elif workflow is None and run is not None and run.status == "running":
        decision_label = "Investigation running"
        rationale = (
            f"The governed investigation for {ticket.id} is running. Evidence is visible, but "
            "no decision, approval request, or customer draft has been finalized yet."
        )
        tiles = [
            AgentDecisionSummaryTile(
                kind="decision",
                label="Decision",
                title="Investigation running",
                body="The agent run has not finalized a trace-backed recommendation yet.",
                tone="info",
                refs=[run.id],
            ),
            AgentDecisionSummaryTile(
                kind="evidence",
                label="Evidence",
                title="Evidence available",
                body=f"{evidence.invoice.id} and related billing records are available.",
                tone="info",
                refs=refs,
            ),
            AgentDecisionSummaryTile(
                kind="risk_gate",
                label="Risk gate",
                title="Risk gate pending",
                body="No refund or credit approval request has been created yet.",
                tone="warning",
                refs=[],
            ),
            AgentDecisionSummaryTile(
                kind="draft",
                label="Draft",
                title="Customer draft pending",
                body="Customer-facing text remains unavailable until the run completes.",
                tone="neutral",
                refs=[],
            ),
        ]
    elif workflow is None and run is not None and run.status == "failed":
        decision_label = "Investigation failed"
        rationale = run.error_state or "The governed investigation failed before a decision."
        tiles = [
            AgentDecisionSummaryTile(
                kind="decision",
                label="Decision",
                title="No reliable decision",
                body=rationale,
                tone="danger",
                refs=[run.id],
            ),
            AgentDecisionSummaryTile(
                kind="evidence",
                label="Evidence",
                title="Evidence remains available",
                body=f"{evidence.invoice.id} and related billing records are still available.",
                tone="info",
                refs=refs,
            ),
            AgentDecisionSummaryTile(
                kind="risk_gate",
                label="Risk gate",
                title="No approval request",
                body=(
                    "No financial action was proposed, so no refund or credit mutation is "
                    "available."
                ),
                tone="neutral",
                refs=[],
            ),
            AgentDecisionSummaryTile(
                kind="draft",
                label="Draft",
                title="No customer draft",
                body="No customer-facing draft was produced by the failed run.",
                tone="neutral",
                refs=[],
            ),
        ]
    elif workflow is not None and run is None:
        decision_label = (
            "Mock mutation executed"
            if workflow.status == "mock_executed"
            else "Historical workflow"
        )
        rationale = workflow.status_reason or "This workflow has no linked agent run."
        tiles = [
            AgentDecisionSummaryTile(
                kind="decision",
                label="Decision",
                title=decision_label,
                body=rationale,
                tone="success" if workflow.status == "mock_executed" else "neutral",
                refs=[workflow.id],
            ),
            AgentDecisionSummaryTile(
                kind="evidence",
                label="Evidence",
                title="Historical evidence",
                body=f"{evidence.invoice.id} and related billing records remain available.",
                tone="info",
                refs=refs,
            ),
            _risk_gate_tile(approval=approval, mutation=mutation),
            AgentDecisionSummaryTile(
                kind="draft",
                label="Draft",
                title="No linked customer draft",
                body="No agent run is linked to this historical workflow.",
                tone="neutral",
                refs=[],
            ),
        ]
    else:
        amount = approval.amount.display if approval is not None else evidence.invoice.total.display
        decision_label = _decision_label(run)
        rationale = (
            workflow.status_reason
            if workflow is not None
            and workflow.status == "completed_no_action"
            and workflow.status_reason
            else _completed_rationale(
                evidence=evidence,
                approval=approval,
                mutation=mutation,
                amount=amount,
            )
        )
        decision_body = (
            "The governed investigation completed without proposing a financial mutation."
            if workflow is not None and workflow.status == "completed_no_action"
            else "The governed decision tool classified the duplicate payment and proposed an "
            "original refund."
        )
        tiles = [
            AgentDecisionSummaryTile(
                kind="decision",
                label="Decision",
                title=decision_label,
                body=decision_body,
                tone="success",
                refs=[run.id] if run is not None else [workflow.id],
            ),
            AgentDecisionSummaryTile(
                kind="evidence",
                label="Evidence",
                title="Invoice and duplicate charge evidence",
                body=(
                    f"{evidence.invoice.id} has captured charges "
                    f"{_format_charge_ids(evidence)} for {evidence.invoice.total.display}."
                ),
                tone="info",
                refs=refs,
            ),
            _risk_gate_tile(approval=approval, mutation=mutation),
            AgentDecisionSummaryTile(
                kind="draft",
                label="Draft",
                title=(
                    "Customer reply prepared"
                    if run is not None and run.customer_reply
                    else "No customer draft"
                ),
                body=(
                    _draft_body(run)
                    if run is not None
                    else "No customer-facing draft was produced."
                ),
                tone="neutral",
                refs=[run.id] if run is not None and run.customer_reply else [],
            ),
        ]

    return AgentDecisionSummary(
        ticket_id=ticket.id,
        state=state,
        decision_label=decision_label,
        rationale=rationale,
        run_id=run.id if run is not None else None,
        workflow_id=workflow.id if workflow is not None else None,
        workflow_version=workflow.version if workflow is not None else None,
        workflow_status_reason_code=(workflow.status_reason_code if workflow is not None else None),
        workflow_status_reason=workflow.status_reason if workflow is not None else None,
        approval_id=approval.id if approval is not None else None,
        mutation_id=mutation.id if mutation is not None else None,
        policy_citation=evidence.policy.citation,
        compliance_status=compliance_status,
        tiles=tiles,
    )


def _build_supporting_scenario_summary(
    *,
    ticket: TicketDetail,
    evidence: BillingEvidence,
    run: AgentRunSummary | None,
    approval: ApprovalSummary | None,
    mutation: MockMutationSummary | None,
    workflow: CaseWorkflowSummary | None,
    compliance_status: str | None,
) -> AgentDecisionSummary:
    state = _summary_state(workflow=workflow, run=run, approval=approval, mutation=mutation)
    if workflow is not None:
        decision_label = workflow.status.replace("_", " ").capitalize()
    else:
        decision_label = "Scenario readiness pending" if run is None else _decision_label(run)
    return AgentDecisionSummary(
        ticket_id=ticket.id,
        state=state,
        decision_label=decision_label,
        rationale=(
            workflow.status_reason
            if workflow is not None and workflow.status_reason
            else "This supporting scenario keeps the Workbench shape visible, but it does not "
            "invent a governed decision loop before the scenario is implemented."
        ),
        run_id=run.id if run is not None else None,
        workflow_id=workflow.id if workflow is not None else None,
        workflow_version=workflow.version if workflow is not None else None,
        workflow_status_reason_code=(workflow.status_reason_code if workflow is not None else None),
        workflow_status_reason=workflow.status_reason if workflow is not None else None,
        approval_id=approval.id if approval is not None else None,
        mutation_id=mutation.id if mutation is not None else None,
        policy_citation=evidence.policy.citation,
        compliance_status=compliance_status,
        tiles=[
            AgentDecisionSummaryTile(
                kind="decision",
                label="Decision",
                title=decision_label,
                body="No executable governed scenario runner is attached to this support case yet.",
                tone="neutral",
                refs=[ticket.id],
            ),
            AgentDecisionSummaryTile(
                kind="evidence",
                label="Evidence",
                title="Seeded evidence available",
                body=f"{evidence.invoice.id} and policy context are available for later work.",
                tone="info",
                refs=_evidence_refs(evidence),
            ),
            AgentDecisionSummaryTile(
                kind="risk_gate",
                label="Risk gate",
                title="No financial action proposed",
                body="No refund or credit mutation can execute without a governed approval path.",
                tone="neutral",
                refs=[],
            ),
            AgentDecisionSummaryTile(
                kind="draft",
                label="Draft",
                title="No customer draft",
                body="Customer-facing text remains unavailable until a governed run creates it.",
                tone="neutral",
                refs=[],
            ),
        ],
    )


def _summary_state(
    *,
    workflow: CaseWorkflowSummary | None,
    run: AgentRunSummary | None,
    approval: ApprovalSummary | None,
    mutation: MockMutationSummary | None,
) -> DecisionSummaryState:
    if workflow is not None:
        return workflow.status
    if run is None:
        return "not_started"
    if run.status == "running":
        return "investigating"
    if run.status == "failed":
        return "needs_retry"
    return "completed_no_action"


def _decision_label(run: AgentRunSummary) -> str:
    if run.final_outcome == "confirmed_duplicate_charge":
        return "Duplicate captured charge confirmed"
    if run.final_outcome:
        return run.final_outcome.replace("_", " ").capitalize()
    if run.status == "running":
        return "Investigation running"
    return "Decision recorded"


def _completed_rationale(
    *,
    evidence: BillingEvidence,
    approval: ApprovalSummary | None,
    mutation: MockMutationSummary | None,
    amount: str,
) -> str:
    if mutation is not None:
        return (
            f"Agent confirmed a duplicate captured charge on {evidence.invoice.id}. The {amount} "
            "mock mutation executed after human approval."
        )
    if approval is not None and approval.status == "rejected":
        return (
            f"Agent confirmed a duplicate captured charge on {evidence.invoice.id}, but the "
            "human reviewer rejected the financial action; no mock mutation executed."
        )
    if approval is not None and approval.status == "withdrawn":
        return (
            f"Agent confirmed a duplicate captured charge on {evidence.invoice.id}, but the "
            "approval was withdrawn with workflow cancellation; no mock mutation executed."
        )
    if approval is not None and approval.status == "approved":
        return (
            f"Agent confirmed a duplicate captured charge on {evidence.invoice.id}; the {amount} "
            "refund request is approved and waiting for mock mutation execution."
        )
    if approval is not None:
        return (
            f"Agent confirmed a duplicate captured charge on {evidence.invoice.id} and prepared "
            f"an original refund request. The {amount} mutation remains blocked until human "
            "approval."
        )
    return (
        f"Agent completed the investigation for {evidence.invoice.id}, but no financial approval "
        "request is currently attached."
    )


def _risk_gate_tile(
    *,
    approval: ApprovalSummary | None,
    mutation: MockMutationSummary | None,
) -> AgentDecisionSummaryTile:
    if mutation is not None:
        return AgentDecisionSummaryTile(
            kind="risk_gate",
            label="Risk gate",
            title="Approved mock mutation executed",
            body=f"{mutation.id} executed only after approval; action fingerprint is preserved.",
            tone="success",
            refs=[mutation.id],
        )
    if approval is None:
        return AgentDecisionSummaryTile(
            kind="risk_gate",
            label="Risk gate",
            title="No approval request",
            body="No high-risk financial action is available to execute.",
            tone="neutral",
            refs=[],
        )
    if approval.status == "rejected":
        return AgentDecisionSummaryTile(
            kind="risk_gate",
            label="Risk gate",
            title="Financial action rejected",
            body=f"{approval.id} was rejected by a human reviewer; no mock mutation executed.",
            tone="danger",
            refs=[approval.id],
        )
    if approval.status == "withdrawn":
        return AgentDecisionSummaryTile(
            kind="risk_gate",
            label="Risk gate",
            title="Financial action withdrawn",
            body=(
                f"{approval.id} was withdrawn with workflow cancellation; "
                "no mock mutation executed."
            ),
            tone="warning",
            refs=[approval.id],
        )
    if approval.status == "approved":
        return AgentDecisionSummaryTile(
            kind="risk_gate",
            label="Risk gate",
            title="Financial action approved",
            body=f"{approval.id} is approved; mock mutation execution remains tracked separately.",
            tone="success",
            refs=[approval.id],
        )
    return AgentDecisionSummaryTile(
        kind="risk_gate",
        label="Risk gate",
        title="Refund blocked for approval",
        body=f"{approval.id} is pending human approval; no mock mutation has executed.",
        tone="warning",
        refs=[approval.id],
    )


def _draft_body(run: AgentRunSummary) -> str:
    if not run.customer_reply:
        return "No customer-facing draft was produced by this run."
    return f"Draft only - not sent. {run.customer_reply}"


def _evidence_refs(evidence: BillingEvidence) -> list[str]:
    return [
        evidence.invoice.id,
        *[charge.id for charge in evidence.charges],
        evidence.policy.citation,
    ]


def _format_charge_ids(evidence: BillingEvidence) -> str:
    return " and ".join(charge.id for charge in evidence.charges)
