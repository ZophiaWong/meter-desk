from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api_client import authenticate_demo_client
from meterdesk_api.agent.orchestrator import AgentRunOrchestrator
from meterdesk_api.agent.planning import (
    InvestigationPlan,
    InvestigationPlanStep,
    PlanVerifierFeedbackItem,
)
from meterdesk_api.agent.provider import (
    AgentDraftOutput,
    AgentProviderError,
    AgentProviderInput,
    AgentResolutionProvider,
)
from meterdesk_api.agent.runtime import get_agent_provider
from meterdesk_api.errors import MeterDeskAPIError
from meterdesk_api.main import app
from meterdesk_api.repositories import get_repository
from meterdesk_api.seed_data import build_seed_repository


class FakeProvider(AgentResolutionProvider):
    model = "fake-m3-model"

    def __init__(
        self,
        outputs: list[AgentDraftOutput | Exception] | None = None,
        plan_outputs: list[InvestigationPlan | Exception] | None = None,
    ) -> None:
        self.outputs = outputs
        self.plan_outputs = plan_outputs
        self.calls: list[AgentProviderInput] = []
        self.plan_calls: list[object] = []

    async def create_investigation_plan(
        self,
        planner_input,
        verifier_feedback: list[PlanVerifierFeedbackItem] | None = None,
    ) -> InvestigationPlan:
        self.plan_calls.append(
            {"planner_input": planner_input, "verifier_feedback": verifier_feedback or []}
        )
        output = (
            self.plan_outputs.pop(0)
            if self.plan_outputs is not None
            else self._default_plan(planner_input.scenario)
        )
        if isinstance(output, Exception):
            raise output
        return output

    async def create_resolution(self, provider_input: AgentProviderInput) -> AgentDraftOutput:
        self.calls.append(provider_input)
        output = self.outputs.pop(0) if self.outputs is not None else self._default_output()
        if isinstance(output, Exception):
            raise output
        return output

    def _default_plan(self, scenario: str) -> InvestigationPlan:
        if scenario == "credit_refund_dispute":
            return credit_refund_plan()
        return duplicate_charge_plan()

    def _default_output(self) -> AgentDraftOutput:
        return AgentDraftOutput(
            recommendation="Refund the duplicate captured charge after approval.",
            internal_resolution=(
                "Confirmed duplicate payment on INV-2026-0418. Recommend refunding "
                "ch_2026_0418_B after human approval."
            ),
            customer_reply=(
                "Thanks for flagging this. We found two captured payments tied to the same "
                "April invoice. We are sending the duplicate charge for approval and will "
                "keep you updated."
            ),
        )


class DraftOnlyProvider(AgentResolutionProvider):
    model = "draft-only-model"

    async def create_investigation_plan(
        self,
        planner_input,
        verifier_feedback: list[PlanVerifierFeedbackItem] | None = None,
    ) -> InvestigationPlan:
        if planner_input.scenario == "credit_refund_dispute":
            return credit_refund_plan()
        return duplicate_charge_plan()

    async def create_resolution(self, provider_input: AgentProviderInput) -> AgentDraftOutput:
        return AgentDraftOutput(
            recommendation=provider_input.decision_reason,
            internal_resolution=(
                f"{provider_input.decision_outcome} for {provider_input.ticket_id}. "
                f"Policy: {provider_input.policy_citation}."
            ),
            customer_reply=(
                "Thanks for raising this. We reviewed the payment events and confirmed the "
                "second matching event was an authorization, not a captured charge."
            ),
        )


def duplicate_charge_plan() -> InvestigationPlan:
    return InvestigationPlan(
        scenario="duplicate_charge",
        plan_summary="Investigate duplicate-charge evidence and backend refund eligibility.",
        steps=[
            InvestigationPlanStep(
                step_id="evidence",
                action_id="read.billing_evidence",
                evidence_targets=[
                    "account_state",
                    "invoice",
                    "charges",
                    "payment_status",
                    "credit_ledger",
                    "usage",
                    "policy",
                ],
                rationale="Read invoice, charge, credit, usage, and policy evidence.",
                depends_on=[],
            ),
            InvestigationPlanStep(
                step_id="prior",
                action_id="read.prior_financial_actions",
                evidence_targets=["prior_financial_actions"],
                rationale="Check prior financial actions to avoid duplicate refunds.",
                depends_on=[],
            ),
            InvestigationPlanStep(
                step_id="decision",
                action_id="decision.refund_eligibility",
                evidence_targets=["invoice", "charges", "policy", "prior_financial_actions"],
                rationale="Ask the backend decision tool to classify refund eligibility.",
                depends_on=["evidence", "prior"],
            ),
        ],
        evidence_gaps=[],
        stop_conditions=["Stop if required billing evidence is missing."],
    )


def credit_refund_plan() -> InvestigationPlan:
    return InvestigationPlan(
        scenario="credit_refund_dispute",
        plan_summary="Investigate credit/refund evidence and backend eligibility.",
        steps=[
            InvestigationPlanStep(
                step_id="evidence",
                action_id="read.credit_refund_evidence",
                evidence_targets=[
                    "account_state",
                    "invoice",
                    "charges",
                    "payment_status",
                    "credit_ledger",
                    "subscription",
                    "policy",
                ],
                rationale="Read credit ledger, subscription, invoice, charge, and policy evidence.",
                depends_on=[],
            ),
            InvestigationPlanStep(
                step_id="prior",
                action_id="read.prior_financial_actions",
                evidence_targets=["prior_financial_actions"],
                rationale="Check prior financial actions to avoid duplicate credits or refunds.",
                depends_on=[],
            ),
            InvestigationPlanStep(
                step_id="decision",
                action_id="decision.credit_refund_eligibility",
                evidence_targets=[
                    "invoice",
                    "charges",
                    "credit_ledger",
                    "subscription",
                    "policy",
                    "prior_financial_actions",
                ],
                rationale="Ask the backend decision tool to classify credit/refund eligibility.",
                depends_on=["evidence", "prior"],
            ),
        ],
        evidence_gaps=[],
        stop_conditions=["Stop if required credit or subscription evidence is missing."],
    )


def unsafe_approval_plan() -> InvestigationPlan:
    return InvestigationPlan(
        scenario="duplicate_charge",
        plan_summary="Unsafe plan that attempts to create approval directly.",
        steps=[
            InvestigationPlanStep(
                step_id="approval",
                action_id="approval.create_request",
                evidence_targets=["invoice", "charges", "policy"],
                rationale="Create approval directly.",
                depends_on=[],
            )
        ],
        evidence_gaps=[],
        stop_conditions=[],
    )


@pytest.fixture(autouse=True)
async def m3_dependency_overrides():
    repository = build_seed_repository()
    await repository.reset_demo_live_state("TCK-1042")
    provider = FakeProvider()

    async def repository_override():
        return repository

    async def provider_override():
        return provider

    app.dependency_overrides[get_repository] = repository_override
    app.dependency_overrides[get_agent_provider] = provider_override
    try:
        yield repository, provider
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_start_agent_run_creates_traces_provider_output_and_pending_approval(
    m3_dependency_overrides,
) -> None:
    _, provider = m3_dependency_overrides
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client)
        start_response = await client.post("/tickets/TCK-1042/agent-runs")
        approvals_response = await client.get("/approvals?ticket_id=TCK-1042&status=all")
        run = start_response.json()
        trace_response = await client.get(f"/agent-runs/{run['id']}/traces")

    assert start_response.status_code == 201
    assert run["ticket_id"] == "TCK-1042"
    assert run["status"] == "completed"
    assert run["model"] == "fake-m3-model"
    assert run["prompt_version"] == "m3-duplicate-charge-v1"
    assert run["final_outcome"] == "confirmed_duplicate_charge"
    assert run["customer_reply"]
    assert "will refund" not in run["customer_reply"].lower()

    assert trace_response.status_code == 200
    assert [trace["category"] for trace in trace_response.json()] == [
        "plan.investigation",
        "plan.verify",
        "read.billing_evidence",
        "read.prior_financial_actions",
        "decision.refund_eligibility",
        "draft.resolution",
        "approval.create_request",
    ]
    assert [trace["governance_metadata"]["gate_result"] for trace in trace_response.json()] == [
        "allowed",
        "allowed",
        "allowed",
        "allowed",
        "allowed",
        "allowed",
        "allowed",
    ]
    assert trace_response.json()[1]["governance_metadata"]["planning"]["status"] == "accepted"
    assert trace_response.json()[1]["governance_metadata"]["planning"]["normalized_action_ids"] == [
        "read.billing_evidence",
        "read.prior_financial_actions",
        "decision.refund_eligibility",
    ]
    assert trace_response.json()[4]["governance_metadata"]["policy_id"] == (
        "decision.refund_eligibility"
    )
    assert len(provider.plan_calls) == 1

    assert approvals_response.status_code == 200
    approvals = approvals_response.json()
    assert len(approvals) == 1
    assert approvals[0]["status"] == "pending"
    assert approvals[0]["agent_run_id"] == run["id"]
    assert approvals[0]["action_metadata"]["target_charge_id"] == "ch_2026_0418_B"
    assert approvals[0]["action_fingerprint"] == (
        "ticket:TCK-1042|action:original_refund|target:ch_2026_0418_B|amount:124800|currency:USD"
    )
    assert trace_response.json()[3]["governance_metadata"]["negative_evidence_refs"] == [
        "no_prior_mock_mutation"
    ]


@pytest.mark.asyncio
async def test_start_agent_run_supports_credit_refund_goodwill_credit_workflow() -> None:
    repository = build_seed_repository()
    await repository.reset_demo_live_state("TCK-1137")
    provider = FakeProvider()

    async def repository_override():
        return repository

    async def provider_override():
        return provider

    app.dependency_overrides[get_repository] = repository_override
    app.dependency_overrides[get_agent_provider] = provider_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client)
        start_response = await client.post("/tickets/TCK-1137/agent-runs")
        approvals_response = await client.get("/approvals?ticket_id=TCK-1137&status=all")
        run = start_response.json()
        trace_response = await client.get(f"/agent-runs/{run['id']}/traces")

    assert start_response.status_code == 201
    assert run["ticket_id"] == "TCK-1137"
    assert run["status"] == "completed"
    assert run["prompt_version"] == "m8-credit-refund-v1"
    assert run["final_outcome"] == "goodwill_credit_requires_approval"
    assert provider.calls[0].action_type == "goodwill_credit"
    assert provider.calls[0].target_credit_id == "cred-ledger-1137"

    assert [trace["category"] for trace in trace_response.json()] == [
        "plan.investigation",
        "plan.verify",
        "read.credit_refund_evidence",
        "read.prior_financial_actions",
        "decision.credit_refund_eligibility",
        "draft.resolution",
        "approval.create_request",
    ]
    assert trace_response.json()[1]["governance_metadata"]["planning"]["status"] == "accepted"
    assert trace_response.json()[4]["governance_metadata"]["policy_id"] == (
        "decision.credit_refund_eligibility"
    )

    approvals = approvals_response.json()
    assert len(approvals) == 1
    assert approvals[0]["status"] == "pending"
    assert approvals[0]["action_type"] == "goodwill_credit"
    assert approvals[0]["amount"]["display"] == "$120.00"
    assert approvals[0]["policy_citation"] == "TRIAL-CREDIT-003 v2026.03"
    assert approvals[0]["action_metadata"] == {
        "action_type": "goodwill_credit",
        "credit_ledger_entry_id": "cred-ledger-1137",
        "subscription_id": "sub-helio-2026",
        "action_basis": "goodwill_credit_requires_approval",
    }
    assert approvals[0]["action_fingerprint"] == (
        "ticket:TCK-1137|action:goodwill_credit|target:cred-ledger-1137|amount:12000|currency:USD"
    )


@pytest.mark.asyncio
async def test_agent_run_final_outcome_comes_from_backend_decision() -> None:
    repository = build_seed_repository()
    orchestrator = AgentRunOrchestrator(repository, DraftOnlyProvider())

    run = await orchestrator.run_duplicate_charge("EVAL-TCK-DUP-002")
    approvals = await repository.list_approvals(
        status=None,
        ticket_id="EVAL-TCK-DUP-002",
    )
    mutations = await repository.list_mock_mutations("EVAL-TCK-DUP-002")

    assert run is not None
    assert run.status == "completed"
    assert run.final_outcome == "no_refund_expected_billing_behavior"
    assert approvals == []
    assert mutations == []


@pytest.mark.asyncio
async def test_start_agent_run_is_blocked_while_approval_is_pending() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client)
        first = await client.post("/tickets/TCK-1042/agent-runs")
        second = await client.post("/tickets/TCK-1042/agent-runs")

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json() == {
        "code": "approval.pending_duplicate",
        "message": "A pending financial approval already exists for this action.",
        "details": {
            "action_fingerprint": (
                "ticket:TCK-1042|action:original_refund|target:ch_2026_0418_B|"
                "amount:124800|currency:USD"
            )
        },
        "request_id": second.headers["X-Request-ID"],
    }


@pytest.mark.asyncio
async def test_provider_validation_failure_retries_once_then_persists_failed_run() -> None:
    provider = FakeProvider(
        outputs=[
            AgentProviderError("invalid structured output"),
            AgentProviderError("invalid structured output"),
        ]
    )

    async def provider_override():
        return provider

    app.dependency_overrides[get_agent_provider] = provider_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client)
        response = await client.post("/tickets/TCK-1042/agent-runs")
        approvals = await client.get("/approvals?ticket_id=TCK-1042&status=all")

    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "failed"
    assert run["error_state"] == "Provider failed after retry: invalid structured output"
    assert run["internal_resolution"] is None
    assert approvals.json() == []
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_planner_verifier_retries_once_then_runs_accepted_plan() -> None:
    provider = FakeProvider(plan_outputs=[unsafe_approval_plan(), duplicate_charge_plan()])

    async def provider_override():
        return provider

    app.dependency_overrides[get_agent_provider] = provider_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client)
        response = await client.post("/tickets/TCK-1042/agent-runs")
        run = response.json()
        trace_response = await client.get(f"/agent-runs/{run['id']}/traces")

    assert response.status_code == 201
    assert run["status"] == "completed"
    assert len(provider.plan_calls) == 2
    assert [
        item.model_dump(exclude_none=True) for item in provider.plan_calls[1]["verifier_feedback"]
    ] == [
        {
            "reason_code": "plan.unsafe_financial_action",
            "action_id": "approval.create_request",
            "missing_targets": [],
        },
        {
            "reason_code": "plan.missing_required_action",
            "action_id": "read.billing_evidence",
            "missing_targets": [],
        },
        {
            "reason_code": "plan.missing_required_action",
            "action_id": "read.prior_financial_actions",
            "missing_targets": [],
        },
        {
            "reason_code": "plan.missing_required_action",
            "action_id": "decision.refund_eligibility",
            "missing_targets": [],
        },
        {
            "reason_code": "plan.missing_required_target",
            "missing_targets": [
                "account_state",
                "invoice",
                "charges",
                "payment_status",
                "credit_ledger",
                "usage",
                "policy",
                "prior_financial_actions",
            ],
        },
    ]
    verify_metadata = trace_response.json()[1]["governance_metadata"]["planning"]
    assert verify_metadata["status"] == "accepted"
    assert verify_metadata["attempt_count"] == 2
    assert verify_metadata["blocked_attempt_reason_codes"] == [
        [
            "plan.unsafe_financial_action",
            "plan.missing_required_action",
            "plan.missing_required_target",
        ]
    ]


@pytest.mark.asyncio
async def test_planner_verifier_blocks_run_after_two_invalid_plans() -> None:
    provider = FakeProvider(plan_outputs=[unsafe_approval_plan(), unsafe_approval_plan()])

    async def provider_override():
        return provider

    app.dependency_overrides[get_agent_provider] = provider_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client)
        response = await client.post("/tickets/TCK-1042/agent-runs")
        approvals = await client.get("/approvals?ticket_id=TCK-1042&status=all")
        run = response.json()
        trace_response = await client.get(f"/agent-runs/{run['id']}/traces")

    assert response.status_code == 201
    assert run["status"] == "failed"
    assert run["error_state"] == "Plan verifier blocked investigation plan"
    assert approvals.json() == []
    assert [trace["category"] for trace in trace_response.json()] == [
        "plan.investigation",
        "plan.verify",
    ]
    assert trace_response.json()[1]["error_state"] == "plan.unsafe_financial_action"
    assert trace_response.json()[1]["governance_metadata"]["planning"]["status"] == "blocked"
    assert len(provider.calls) == 0
    assert len(provider.plan_calls) == 2


@pytest.mark.asyncio
async def test_missing_provider_config_returns_503_without_creating_run() -> None:
    async def missing_provider_override():
        raise MeterDeskAPIError(
            status_code=503,
            code="provider.not_configured",
            message="OpenAI-compatible provider is not configured.",
        )

    app.dependency_overrides[get_agent_provider] = missing_provider_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client)
        response = await client.post("/tickets/TCK-1042/agent-runs")
        runs = await client.get("/tickets/TCK-1042/agent-runs")

    assert response.status_code == 503
    assert response.json() == {
        "code": "provider.not_configured",
        "message": "OpenAI-compatible provider is not configured.",
        "details": {},
        "request_id": response.headers["X-Request-ID"],
    }
    assert runs.json() == []


@pytest.mark.asyncio
async def test_unsupported_scenario_has_no_side_effects() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client)
        response = await client.post("/tickets/TCK-1098/agent-runs")
        runs = await client.get("/tickets/TCK-1098/agent-runs")

    assert response.status_code == 422
    assert response.json()["code"] == "agent.unsupported_scenario"
    assert runs.json() == []


@pytest.mark.asyncio
async def test_reject_does_not_create_mutation_and_allows_rerun() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client)
        await client.post("/tickets/TCK-1042/agent-runs")
        approvals = await client.get("/approvals?ticket_id=TCK-1042&status=all")
        approval_id = approvals.json()[0]["id"]

        reject = await client.post(
            f"/approvals/{approval_id}/reject",
            json={"decided_by": "Demo Operator", "decision_note": "Needs finance review."},
        )
        mutations = await client.get("/mock-mutations?ticket_id=TCK-1042")
        rerun = await client.post("/tickets/TCK-1042/agent-runs")

    assert reject.status_code == 200
    assert reject.json()["approval"]["status"] == "rejected"
    assert reject.json()["approval"]["decided_by"] == "Demo Operator"
    assert mutations.json() == []
    assert rerun.status_code == 201


@pytest.mark.asyncio
async def test_approve_executes_one_mock_mutation_and_is_idempotent() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await authenticate_demo_client(client)
        run_response = await client.post("/tickets/TCK-1042/agent-runs")
        approvals = await client.get("/approvals?ticket_id=TCK-1042&status=all")
        approval_id = approvals.json()[0]["id"]

        first = await client.post(
            f"/approvals/{approval_id}/approve",
            json={"decided_by": "Demo Operator", "decision_note": "Approved for demo."},
        )
        second = await client.post(
            f"/approvals/{approval_id}/approve",
            json={"decided_by": "Demo Operator"},
        )
        opposite = await client.post(
            f"/approvals/{approval_id}/reject",
            json={"decided_by": "Demo Operator"},
        )
        mutations = await client.get("/mock-mutations?ticket_id=TCK-1042")
        trace_response = await client.get(f"/agent-runs/{run_response.json()['id']}/traces")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["mock_mutation"]["id"] == second.json()["mock_mutation"]["id"]
    assert first.json()["approval"]["status"] == "approved"
    assert opposite.status_code == 409
    assert len(mutations.json()) == 1
    assert mutations.json()[0]["approval_request_id"] == approval_id
    assert first.json()["approval"]["action_fingerprint"] == (
        "ticket:TCK-1042|action:original_refund|target:ch_2026_0418_B|amount:124800|currency:USD"
    )
    assert (
        mutations.json()[0]["action_fingerprint"] == first.json()["approval"]["action_fingerprint"]
    )

    assert trace_response.status_code == 200
    assert trace_response.json()[-1]["category"] == "mutation.mock_refund"
    assert trace_response.json()[-1]["risk"] == "High"
    assert trace_response.json()[-1]["governance_metadata"]["gate_result"] == "allowed"
    assert trace_response.json()[-1]["governance_metadata"]["policy_id"] == "mutation.mock_refund"
