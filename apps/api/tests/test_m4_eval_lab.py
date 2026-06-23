from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from meterdesk_api.agent.provider import (
    AgentDraftOutput,
    AgentProviderInput,
    AgentResolutionProvider,
)
from meterdesk_api.agent.runtime import get_optional_agent_provider, get_optional_eval_judge
from meterdesk_api.eval.judge import EvalDraftJudgeInput, EvalDraftJudgeOutput
from meterdesk_api.eval.runner import EvalRunner
from meterdesk_api.main import app
from meterdesk_api.repositories import get_repository
from meterdesk_api.schemas import EvalResultSummary
from meterdesk_api.seed_data import build_seed_repository


class EchoProvider(AgentResolutionProvider):
    model = "fake-eval-model"

    async def create_resolution(self, provider_input: AgentProviderInput) -> AgentDraftOutput:
        action_text = (
            f" Recommend {provider_input.action_type} after human approval."
            if provider_input.action_type
            else " No financial action is recommended."
        )
        return AgentDraftOutput(
            recommendation=f"{provider_input.decision_reason}{action_text}",
            internal_resolution=(
                f"{provider_input.decision_outcome} for {provider_input.ticket_id}. "
                f"Policy: {provider_input.policy_citation}."
            ),
            customer_reply=(
                "Thanks for raising this billing question. We reviewed the invoice, payment "
                "events, and policy context and will keep the response draft pending review."
            ),
        )


class PassingJudge:
    async def judge(self, judge_input: EvalDraftJudgeInput) -> EvalDraftJudgeOutput:
        return EvalDraftJudgeOutput(
            score="pass",
            notes=f"Draft is clear for {judge_input.outcome}.",
        )


@pytest.mark.asyncio
async def test_duplicate_charge_eval_runs_real_agent_and_stops_at_pending_approval() -> None:
    repository = build_seed_repository()
    runner = EvalRunner(repository=repository, provider=EchoProvider())

    result = await runner.run_case("eval-duplicate-charge-001")
    fixture_ticket_id = "EVAL-TCK-DUP-001"
    approvals = await repository.list_approvals(status="pending", ticket_id=fixture_ticket_id)
    mutations = await repository.list_mock_mutations(ticket_id=fixture_ticket_id)
    traces = await repository.list_traces(result.agent_run_id)

    assert result.status == "passed"
    assert result.agent_run_id is not None
    assert result.dimension_scores["outcome_correctness"] == "pass"
    assert result.dimension_scores["required_evidence"] == "pass"
    assert result.dimension_scores["policy_compliance"] == "pass"
    assert result.dimension_scores["approval_routing"] == "pass"
    assert result.dimension_scores["mutation_safety"] == "pass"
    assert result.dimension_scores["governance_compliance"] == "pass"
    assert result.dimension_scores["draft_quality"] == "not_run"
    assert result.details["failed_checks"] == []
    assert result.details["missing_evidence"] == []
    assert result.details["policy_refs_seen"] == ["REFUND-DUP-001 v2026.02"]
    assert result.details["compliance"]["status"] == "passed"
    assert result.details["compliance"]["high_risk_gate_count"] == 1
    assert result.details["compliance"]["verified_governed_action_count"] == 5
    assert result.details["trace_refs"]
    assert approvals and approvals[0].agent_run_id == result.agent_run_id
    assert mutations == []
    assert traces is not None
    assert [trace.category for trace in traces][-1] == "approval.create_request"


@pytest.mark.asyncio
async def test_eval_judge_is_advisory_when_configured() -> None:
    repository = build_seed_repository()
    runner = EvalRunner(repository=repository, provider=EchoProvider(), judge=PassingJudge())

    result = await runner.run_case("eval-duplicate-charge-002")

    assert result.status == "passed"
    assert result.dimension_scores["draft_quality"] == "pass"
    assert result.details["judge_notes"] == [
        "Draft is clear for no_refund_expected_billing_behavior."
    ]


@pytest.mark.asyncio
async def test_supporting_scenario_eval_cases_are_blocked_coverage_gaps() -> None:
    repository = build_seed_repository()
    runner = EvalRunner(repository=repository, provider=EchoProvider())

    result = await runner.run_case("eval-usage-spike-001")

    assert result.status == "blocked"
    assert result.agent_run_id is None
    assert result.dimension_scores["outcome_correctness"] == "blocked"
    assert result.dimension_scores["governance_compliance"] == "blocked"
    assert result.dimension_scores["draft_quality"] == "not_run"
    assert result.details["blocked_reason"] == "Scenario runner is not implemented in M4"
    assert result.details["blocked_code"] == "scenario.runner_not_implemented"
    assert result.details["recommended_next_scenario"] == "credit_refund_dispute"
    assert result.details["readiness_gaps"]


@pytest.mark.asyncio
async def test_eval_results_are_latest_only_and_do_not_reset_workbench_ticket_state() -> None:
    repository = build_seed_repository()
    runner = EvalRunner(repository=repository, provider=EchoProvider())
    workbench_run = await repository.create_agent_run(
        ticket_id="TCK-1042",
        source="manual-test",
        model="manual-model",
        prompt_version="manual-v1",
    )

    first = await runner.run_case("eval-duplicate-charge-003")
    second = await runner.run_case("eval-duplicate-charge-003")
    results = await repository.list_eval_results()
    workbench_runs = await repository.list_agent_runs("TCK-1042")

    assert first.id != second.id
    assert [result.case_id for result in results].count("eval-duplicate-charge-003") == 1
    assert results[0].id == second.id
    assert workbench_runs is not None
    assert [run.id for run in workbench_runs] == ["RUN-2042", workbench_run.id]


@pytest.mark.asyncio
async def test_reset_eval_fixture_state_removes_results_linked_to_fixture_runs() -> None:
    repository = build_seed_repository()
    run = await repository.create_agent_run(
        ticket_id="EVAL-TCK-DUP-001",
        source="eval-test",
        model="fake-eval-model",
        prompt_version="m4-eval-v1",
    )
    await repository.replace_eval_result(
        EvalResultSummary(
            id="EVR-test",
            case_id="eval-duplicate-charge-001",
            agent_run_id=run.id,
            status="passed",
            summary="Previous eval result.",
            dimension_scores={},
            details={},
        )
    )

    await repository.reset_eval_fixture_state("EVAL-TCK-DUP-001")

    runs = await repository.list_agent_runs("EVAL-TCK-DUP-001")
    results = await repository.list_eval_results()
    assert runs == []
    assert results == []


@pytest.mark.asyncio
async def test_duplicate_charge_eval_is_blocked_when_provider_is_missing() -> None:
    repository = build_seed_repository()
    runner = EvalRunner(repository=repository, provider=None)

    result = await runner.run_case("eval-duplicate-charge-001")

    assert result.status == "blocked"
    assert result.agent_run_id is None
    assert result.dimension_scores["outcome_correctness"] == "blocked"
    assert result.dimension_scores["governance_compliance"] == "blocked"
    assert result.details["blocked_reason"] == "OpenAI-compatible provider is not configured"


@pytest.mark.asyncio
async def test_governance_compliance_failure_is_blocking_for_eval(monkeypatch) -> None:
    from meterdesk_api.agent.compliance import RunComplianceFailure, RunComplianceResult
    from meterdesk_api.eval import runner as runner_module

    async def failed_check(self, agent_run_id: str) -> RunComplianceResult:
        return RunComplianceResult(
            status="failed",
            checked_at="2026-06-23T00:00:00Z",
            failed_checks=[
                RunComplianceFailure(
                    code="governance.metadata_missing",
                    message="Governance metadata is missing.",
                    affected_trace_ids=["trace-missing"],
                )
            ],
            reason_codes=["governance.metadata_missing"],
            affected_trace_ids=["trace-missing"],
            missing_ref_categories=[],
            policy_versions_seen={},
            high_risk_gate_count=0,
            verified_governed_action_count=0,
        )

    monkeypatch.setattr(runner_module.RunComplianceChecker, "check", failed_check)
    repository = build_seed_repository()
    runner = EvalRunner(repository=repository, provider=EchoProvider())

    result = await runner.run_case("eval-duplicate-charge-001")

    assert result.status == "failed"
    assert result.dimension_scores["governance_compliance"] == "fail"
    assert "governance_compliance" in result.details["failed_checks"]
    assert result.details["compliance"]["reason_codes"] == ["governance.metadata_missing"]


@pytest.mark.asyncio
async def test_eval_lab_api_runs_one_case_and_all_cases() -> None:
    repository = build_seed_repository()

    async def repository_override():
        return repository

    async def provider_override():
        return EchoProvider()

    async def judge_override():
        return None

    app.dependency_overrides[get_repository] = repository_override
    app.dependency_overrides[get_optional_agent_provider] = provider_override
    app.dependency_overrides[get_optional_eval_judge] = judge_override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            single = await client.post("/eval-cases/eval-duplicate-charge-002/run")
            all_cases = await client.post("/eval-runs")
    finally:
        app.dependency_overrides.clear()

    assert single.status_code == 201
    assert single.json()["status"] == "passed"
    assert single.json()["dimension_scores"]["approval_routing"] == "pass"
    assert all_cases.status_code == 201
    results = all_cases.json()
    assert len(results) == 9
    assert {result["status"] for result in results} == {"passed", "blocked"}
