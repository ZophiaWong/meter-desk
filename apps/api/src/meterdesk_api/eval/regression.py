from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from meterdesk_api.agent.governance import GOVERNANCE_METADATA_SCHEMA_VERSION
from meterdesk_api.agent.planning import PLAN_CONTRACTS, InvestigationPlan
from meterdesk_api.agent.provider import (
    PLANNER_SYSTEM_PROMPT,
    RESOLUTION_SYSTEM_PROMPT,
    AgentDraftOutput,
)
from meterdesk_api.eval.runner import BLOCKING_DIMENSIONS, DIMENSION_NAMES
from meterdesk_api.repositories import MeterDeskRepository
from meterdesk_api.schemas import (
    EvalCaseRegressionSummary,
    EvalCaseSummary,
    EvalDimensionDiff,
    EvalRegressionSummary,
    EvalResultSnapshotSummary,
    EvalResultSummary,
    EvalVersionDiff,
    ToolTraceSummary,
)

BASELINE_RUN_ID = "EVAL-RUN-BASELINE-M10"
BASELINE_NAME = "M10 seeded canonical baseline"
GRADER_VERSION = "m10-regression-v1"
RESULT_SCHEMA_VERSION = "eval-result-snapshot-v1"


def build_prompt_fingerprint() -> str:
    payload = {
        "planner_system_prompt": PLANNER_SYSTEM_PROMPT,
        "resolution_system_prompt": RESOLUTION_SYSTEM_PROMPT,
        "investigation_plan_schema": InvestigationPlan.model_json_schema(),
        "agent_draft_output_schema": AgentDraftOutput.model_json_schema(),
        "plan_contracts": {
            scenario: asdict(contract) for scenario, contract in sorted(PLAN_CONTRACTS.items())
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_version_snapshot(
    *,
    result: EvalResultSummary,
    traces: list[ToolTraceSummary],
) -> dict[str, Any]:
    compliance = result.details.get("compliance") if isinstance(result.details, dict) else None
    tool_policy_versions = {}
    if isinstance(compliance, dict) and isinstance(compliance.get("policy_versions_seen"), dict):
        tool_policy_versions = compliance["policy_versions_seen"]
    return {
        "model": result.details.get("model"),
        "prompt_version": result.details.get("prompt_version"),
        "prompt_fingerprint": build_prompt_fingerprint(),
        "policy_refs_seen": result.details.get("policy_refs_seen", []),
        "tool_policy_versions": tool_policy_versions or _tool_policy_versions_from_traces(traces),
        "governance_schema_version": GOVERNANCE_METADATA_SCHEMA_VERSION,
        "grader_version": GRADER_VERSION,
        "result_schema_version": RESULT_SCHEMA_VERSION,
    }


def build_trace_signature(traces: list[ToolTraceSummary]) -> dict[str, Any]:
    evidence_categories = sorted(_evidence_categories_seen(traces))
    policy_refs: list[str] = []
    approval_refs: list[str] = []
    reason_codes: list[str] = []
    ordered_categories: list[str] = []
    for trace in traces:
        ordered_categories.append(trace.category)
        policy_refs.extend(trace.policy_refs)
        approval_refs.extend(trace.approval_refs)
        reason_code = trace.governance_metadata.get("reason_code")
        if isinstance(reason_code, str):
            reason_codes.append(reason_code)
    return {
        "ordered_categories": ordered_categories,
        "evidence_categories": evidence_categories,
        "policy_refs": list(dict.fromkeys(policy_refs)),
        "approval_refs": list(dict.fromkeys(approval_refs)),
        "governance_reason_codes": list(dict.fromkeys(reason_codes)),
    }


def build_snapshot_explanations(result: EvalResultSummary) -> list[str]:
    if result.status == "passed":
        return ["Deterministic eval checks passed."]
    blocked_code = result.details.get("blocked_code") if isinstance(result.details, dict) else None
    if result.status == "blocked":
        if isinstance(blocked_code, str):
            return [f"Eval is blocked by {blocked_code}."]
        return ["Eval is blocked before agent quality can be judged."]
    failed_checks = (
        result.details.get("failed_checks", []) if isinstance(result.details, dict) else []
    )
    missing_evidence = (
        result.details.get("missing_evidence", []) if isinstance(result.details, dict) else []
    )
    explanations = [f"Failed deterministic checks: {', '.join(failed_checks)}."]
    if missing_evidence:
        explanations.append(f"Missing required evidence: {', '.join(missing_evidence)}.")
    return explanations


def snapshot_from_result(
    *,
    eval_run_id: str,
    result: EvalResultSummary,
    snapshot_type: str,
    traces: list[ToolTraceSummary] | None = None,
    created_at: datetime | None = None,
) -> EvalResultSnapshotSummary:
    trace_list = traces or []
    return EvalResultSnapshotSummary(
        id=f"EVS-{result.id}",
        eval_run_id=eval_run_id,
        result_id=result.id,
        case_id=result.case_id,
        agent_run_id=result.agent_run_id,
        snapshot_type=snapshot_type,
        status=result.status,
        summary=result.summary,
        dimension_scores=result.dimension_scores,
        details=result.details,
        trace_signature=build_trace_signature(trace_list),
        version_snapshot=build_version_snapshot(result=result, traces=trace_list),
        explanations=build_snapshot_explanations(result),
        created_at=created_at or datetime.now(UTC),
    )


class EvalRegressionService:
    def __init__(self, repository: MeterDeskRepository) -> None:
        self._repository = repository

    async def latest_summary(self) -> EvalRegressionSummary:
        latest_run = await self._repository.get_latest_eval_run()
        return await self.summary_for_run(latest_run.id if latest_run else None)

    async def summary_for_run(self, eval_run_id: str | None) -> EvalRegressionSummary:
        cases = await self._repository.list_eval_cases()
        baseline_run = await self._repository.get_eval_run(BASELINE_RUN_ID)
        latest_run = await self._repository.get_eval_run(eval_run_id) if eval_run_id else None
        baseline_by_case = {
            snapshot.case_id: snapshot
            for snapshot in await self._repository.list_eval_result_snapshots(
                snapshot_type="baseline"
            )
        }
        current_by_case = {}
        if latest_run is not None:
            current_by_case = {
                snapshot.case_id: snapshot
                for snapshot in await self._repository.list_eval_result_snapshots(
                    eval_run_id=latest_run.id,
                    snapshot_type="current",
                )
            }

        case_summaries = [
            self._compare_case(
                eval_case=eval_case,
                baseline=baseline_by_case.get(eval_case.id),
                current=current_by_case.get(eval_case.id),
            )
            for eval_case in cases
        ]
        counts = {
            "regressed": 0,
            "improved": 0,
            "unchanged": 0,
            "incomparable": 0,
            "coverage_gap": 0,
        }
        for case in case_summaries:
            counts[case.label] += 1

        passed = sum(1 for case in case_summaries if case.current_status == "passed")
        executed = sum(1 for case in case_summaries if case.current_status in {"passed", "failed"})
        return EvalRegressionSummary(
            baseline_run_id=baseline_run.id if baseline_run else None,
            baseline_name=baseline_run.baseline_name if baseline_run else None,
            latest_run_id=latest_run.id if latest_run else None,
            latest_run_type=latest_run.run_type if latest_run else None,
            latest_run_completed_at=latest_run.completed_at if latest_run else None,
            counts=counts,
            blocking_pass_rate=f"{passed}/{executed}" if executed else "0/0",
            cases=case_summaries,
        )

    def _compare_case(
        self,
        *,
        eval_case: EvalCaseSummary,
        baseline: EvalResultSnapshotSummary | None,
        current: EvalResultSnapshotSummary | None,
    ) -> EvalCaseRegressionSummary:
        if baseline is None:
            return _case_summary(
                eval_case,
                baseline,
                current,
                "incomparable",
                ["No seeded baseline snapshot is available for this case."],
            )
        if current is None:
            if baseline.status == "blocked":
                return _case_summary(
                    eval_case,
                    baseline,
                    current,
                    "coverage_gap",
                    [baseline.details.get("blocked_reason", baseline.summary)],
                )
            return _case_summary(
                eval_case,
                baseline,
                current,
                "incomparable",
                ["No current eval snapshot has been recorded for this case."],
            )
        if _schema_version(baseline) != _schema_version(current):
            return _case_summary(
                eval_case,
                baseline,
                current,
                "incomparable",
                ["Baseline and current snapshots use different result schema versions."],
            )
        blocked_code = current.details.get("blocked_code")
        if current.status == "blocked":
            if blocked_code == "scenario.runner_not_implemented":
                return _case_summary(
                    eval_case,
                    baseline,
                    current,
                    "coverage_gap",
                    [current.details.get("blocked_reason", current.summary)],
                )
            return _case_summary(
                eval_case,
                baseline,
                current,
                "incomparable",
                [
                    f"Current run is blocked by {blocked_code or 'eval.blocked'}; "
                    "not counted as an agent regression."
                ],
            )

        dimension_diffs = _dimension_diffs(baseline, current)
        version_diffs = _version_diffs(baseline, current)
        trace_diff = _trace_diff(baseline, current)
        if any(
            diff.dimension in BLOCKING_DIMENSIONS
            and diff.baseline == "pass"
            and diff.current == "fail"
            for diff in dimension_diffs
        ) or (baseline.status == "passed" and current.status == "failed"):
            return _case_summary(
                eval_case,
                baseline,
                current,
                "regressed",
                _regression_explanations(dimension_diffs, current),
                dimension_diffs=dimension_diffs,
                version_diffs=version_diffs,
                trace_diff=trace_diff,
            )
        if any(
            diff.dimension in BLOCKING_DIMENSIONS
            and diff.baseline == "fail"
            and diff.current == "pass"
            for diff in dimension_diffs
        ) or (baseline.status in {"failed", "blocked"} and current.status == "passed"):
            return _case_summary(
                eval_case,
                baseline,
                current,
                "improved",
                ["Current snapshot improves at least one blocking baseline failure."],
                dimension_diffs=dimension_diffs,
                version_diffs=version_diffs,
                trace_diff=trace_diff,
            )
        return _case_summary(
            eval_case,
            baseline,
            current,
            "unchanged",
            ["No blocking regression versus seeded baseline."],
            dimension_diffs=dimension_diffs,
            version_diffs=version_diffs,
            trace_diff=trace_diff,
        )


def _case_summary(
    eval_case: EvalCaseSummary,
    baseline: EvalResultSnapshotSummary | None,
    current: EvalResultSnapshotSummary | None,
    label: str,
    explanations: list[str],
    *,
    dimension_diffs: list[EvalDimensionDiff] | None = None,
    version_diffs: list[EvalVersionDiff] | None = None,
    trace_diff: dict[str, Any] | None = None,
) -> EvalCaseRegressionSummary:
    return EvalCaseRegressionSummary(
        case_id=eval_case.id,
        scenario=eval_case.scenario,
        title=eval_case.title,
        label=label,
        baseline_status=baseline.status if baseline else None,
        current_status=current.status if current else None,
        baseline_snapshot_id=baseline.id if baseline else None,
        current_snapshot_id=current.id if current else None,
        dimension_diffs=dimension_diffs or [],
        version_diffs=version_diffs or [],
        trace_diff=trace_diff or {"added_categories": [], "removed_categories": []},
        explanations=explanations,
    )


def _dimension_diffs(
    baseline: EvalResultSnapshotSummary,
    current: EvalResultSnapshotSummary,
) -> list[EvalDimensionDiff]:
    diffs: list[EvalDimensionDiff] = []
    for dimension in DIMENSION_NAMES:
        baseline_value = baseline.dimension_scores.get(dimension)
        current_value = current.dimension_scores.get(dimension)
        if baseline_value != current_value:
            diffs.append(
                EvalDimensionDiff(
                    dimension=dimension,
                    baseline=baseline_value,
                    current=current_value,
                )
            )
    return diffs


def _version_diffs(
    baseline: EvalResultSnapshotSummary,
    current: EvalResultSnapshotSummary,
) -> list[EvalVersionDiff]:
    fields = (
        "model",
        "prompt_version",
        "prompt_fingerprint",
        "policy_refs_seen",
        "tool_policy_versions",
        "governance_schema_version",
        "grader_version",
        "result_schema_version",
    )
    diffs: list[EvalVersionDiff] = []
    for field in fields:
        baseline_value = baseline.version_snapshot.get(field)
        current_value = current.version_snapshot.get(field)
        if baseline_value != current_value:
            diffs.append(
                EvalVersionDiff(field=field, baseline=baseline_value, current=current_value)
            )
    return diffs


def _trace_diff(
    baseline: EvalResultSnapshotSummary,
    current: EvalResultSnapshotSummary,
) -> dict[str, Any]:
    baseline_categories = baseline.trace_signature.get("ordered_categories", [])
    current_categories = current.trace_signature.get("ordered_categories", [])
    return {
        "added_categories": [
            category for category in current_categories if category not in baseline_categories
        ],
        "removed_categories": [
            category for category in baseline_categories if category not in current_categories
        ],
        "baseline_ordered_categories": baseline_categories,
        "current_ordered_categories": current_categories,
    }


def _regression_explanations(
    dimension_diffs: list[EvalDimensionDiff],
    current: EvalResultSnapshotSummary,
) -> list[str]:
    blocking = [
        f"{diff.dimension}: {diff.baseline} -> {diff.current}"
        for diff in dimension_diffs
        if diff.dimension in BLOCKING_DIMENSIONS
    ]
    if blocking:
        return [f"Blocking dimension regression: {', '.join(blocking)}."]
    failed_checks = current.details.get("failed_checks", [])
    if failed_checks:
        return [f"Current run failed deterministic checks: {', '.join(failed_checks)}."]
    return ["Current run regressed versus seeded baseline."]


def _schema_version(snapshot: EvalResultSnapshotSummary) -> str | None:
    value = snapshot.version_snapshot.get("result_schema_version")
    return value if isinstance(value, str) else None


def _tool_policy_versions_from_traces(traces: list[ToolTraceSummary]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for trace in traces:
        version = trace.governance_metadata.get("policy_version")
        if isinstance(version, str):
            versions[trace.category] = version
    return versions


def _evidence_categories_seen(traces: list[ToolTraceSummary]) -> set[str]:
    categories: set[str] = set()
    for trace in traces:
        if trace.category == "read.billing_evidence":
            categories.update(
                {
                    "account_state",
                    "charges",
                    "credit_ledger",
                    "invoice",
                    "payment_status",
                    "policy",
                    "usage",
                }
            )
        if trace.category == "read.credit_refund_evidence":
            categories.update(
                {
                    "account_state",
                    "charges",
                    "credit_ledger",
                    "invoice",
                    "payment_status",
                    "policy",
                    "subscription",
                }
            )
        for evidence_ref in trace.evidence_refs:
            normalized = evidence_ref.lower()
            if normalized.startswith("invoice "):
                categories.add("invoice")
            if normalized.startswith("charge "):
                categories.update({"charges", "payment_status"})
            if normalized.startswith("credit "):
                categories.add("credit_ledger")
            if normalized.startswith("usage "):
                categories.add("usage")
            if normalized.startswith("subscription "):
                categories.add("subscription")
            if normalized.startswith("prior_adjustment "):
                categories.add("prior_adjustment")
            if normalized.startswith("policy "):
                categories.add("policy")
        if trace.policy_refs:
            categories.add("policy")
    return categories
