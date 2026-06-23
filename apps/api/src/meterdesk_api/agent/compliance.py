from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from meterdesk_api.agent.governance import (
    GOVERNANCE_METADATA_SCHEMA_VERSION,
    build_governance_metadata_for_trace,
    get_tool_policy,
)
from meterdesk_api.repositories import MeterDeskRepository
from meterdesk_api.schemas import (
    AgentRunSummary,
    ApprovalSummary,
    MockMutationSummary,
    RunComplianceFailure,
    RunComplianceResult,
    ToolTraceSummary,
)

MANAGED_RUN_SOURCES = {"m5_seeded_demo", "m3_governed_loop"}
REQUIRED_METADATA_FIELDS = {
    "schema_version",
    "policy_id",
    "policy_version",
    "risk",
    "gate",
    "gate_result",
    "enforcement_outcome",
    "required_ref_categories",
    "satisfied_ref_categories",
    "missing_ref_categories",
    "negative_evidence_refs",
    "trace_required",
    "reason_code",
}


class RunComplianceChecker:
    def __init__(self, repository: MeterDeskRepository) -> None:
        self._repository = repository

    async def check(self, agent_run_id: str) -> RunComplianceResult | None:
        run = await self._repository.get_agent_run(agent_run_id)
        if run is None:
            return None

        traces = await self._repository.list_traces(agent_run_id) or []
        approvals = await self._repository.list_approvals(status=None)
        mutations = await self._repository.list_mock_mutations()
        managed = run.source in MANAGED_RUN_SOURCES

        failures: list[RunComplianceFailure] = []
        policy_versions_seen: dict[str, str] = {}
        verified_governed_action_count = 0

        no_trace_failure = (
            _failure(
                code=(
                    "governance.trace_missing"
                    if managed
                    else "governance.metadata_unsupported"
                ),
                message="No governed trace records are available for this run.",
            )
            if not traces
            else None
        )
        for trace in traces:
            trace_failures, trace_verified, policy_version = self._check_trace(trace, managed)
            failures.extend(trace_failures)
            if policy_version is not None:
                policy_versions_seen[trace.category] = policy_version
            if trace_verified:
                verified_governed_action_count += 1

        failures.extend(self._check_financial_state(run, traces, approvals, mutations))
        if no_trace_failure is not None:
            failures.append(no_trace_failure)
        status = self._resolve_status(failures, managed)

        return RunComplianceResult(
            status=status,
            checked_at=datetime.now(UTC),
            failed_checks=failures,
            reason_codes=_unique(failure.code for failure in failures),
            affected_trace_ids=_unique(
                trace_id for failure in failures for trace_id in failure.affected_trace_ids
            ),
            missing_ref_categories=_unique(
                category
                for failure in failures
                for category in failure.missing_ref_categories
            ),
            policy_versions_seen=policy_versions_seen,
            high_risk_gate_count=len(
                [
                    approval
                    for approval in approvals
                    if approval.agent_run_id == run.id
                    and approval.status in {"pending", "approved", "rejected"}
                ]
            ),
            verified_governed_action_count=verified_governed_action_count,
        )

    def _check_trace(
        self,
        trace: ToolTraceSummary,
        managed: bool,
    ) -> tuple[list[RunComplianceFailure], bool, str | None]:
        policy = get_tool_policy(trace.category)
        if policy is None:
            return (
                [
                    _failure(
                        code="governance.unknown_policy",
                        message=f"Trace references unknown tool policy {trace.category}.",
                        affected_trace_ids=[trace.id],
                    )
                ],
                False,
                None,
            )

        metadata = trace.governance_metadata or {}
        if not metadata:
            return (
                [
                    _failure(
                        code=(
                            "governance.metadata_missing"
                            if managed
                            else "governance.metadata_unsupported"
                        ),
                        message="Governance metadata is missing.",
                        affected_trace_ids=[trace.id],
                    )
                ],
                False,
                None,
            )
        schema_version = metadata.get("schema_version")
        if schema_version != GOVERNANCE_METADATA_SCHEMA_VERSION:
            return (
                [
                    _failure(
                        code=(
                            "governance.metadata_schema_invalid"
                            if managed
                            else "governance.metadata_unsupported"
                        ),
                        message="Governance metadata schema is unsupported.",
                        affected_trace_ids=[trace.id],
                    )
                ],
                False,
                None,
            )

        missing_fields = sorted(REQUIRED_METADATA_FIELDS - metadata.keys())
        if missing_fields:
            return (
                [
                    _failure(
                        code="governance.metadata_invalid",
                        message="Governance metadata is missing required structured fields.",
                        affected_trace_ids=[trace.id],
                        missing_ref_categories=missing_fields,
                    )
                ],
                False,
                _string_or_none(metadata.get("policy_version")),
            )

        expected_metadata = build_governance_metadata_for_trace(
            policy_id=policy.id,
            evidence_refs=trace.evidence_refs,
            policy_refs=trace.policy_refs,
            approval_refs=trace.approval_refs,
            negative_evidence_refs=_string_list(metadata.get("negative_evidence_refs")),
        )
        recomputed_missing = _string_list(expected_metadata.get("missing_ref_categories"))
        if recomputed_missing:
            return (
                [
                    _failure(
                        code="governance.missing_required_ref",
                        message="Trace is missing required governance refs.",
                        affected_trace_ids=[trace.id],
                        missing_ref_categories=recomputed_missing,
                    )
                ],
                False,
                policy.version,
            )

        mismatch_fields = [
            field
            for field in (
                "policy_id",
                "policy_version",
                "risk",
                "gate",
                "required_ref_categories",
                "satisfied_ref_categories",
                "missing_ref_categories",
                "trace_required",
            )
            if metadata.get(field) != expected_metadata.get(field)
        ]
        if mismatch_fields:
            return (
                [
                    _failure(
                        code="governance.metadata_mismatch",
                        message="Stored governance metadata does not match current registry.",
                        affected_trace_ids=[trace.id],
                        missing_ref_categories=mismatch_fields,
                    )
                ],
                False,
                policy.version,
            )

        reason_code = _string_or_none(metadata.get("reason_code"))
        if trace.error_state or metadata.get("gate_result") == "blocked":
            return (
                [
                    _failure(
                        code=reason_code or trace.error_state or "governance.blocked_trace",
                        message="Trace records a blocked governed action.",
                        affected_trace_ids=[trace.id],
                    )
                ],
                False,
                policy.version,
            )

        return [], True, policy.version

    def _check_financial_state(
        self,
        run: AgentRunSummary,
        traces: list[ToolTraceSummary],
        approvals: list[ApprovalSummary],
        mutations: list[MockMutationSummary],
    ) -> list[RunComplianceFailure]:
        failures: list[RunComplianceFailure] = []
        approvals_by_id = {approval.id: approval for approval in approvals}

        pending_by_fingerprint: dict[str, list[ApprovalSummary]] = defaultdict(list)
        for approval in approvals:
            if approval.status == "pending":
                pending_by_fingerprint[approval.action_fingerprint].append(approval)
        for fingerprint, duplicates in pending_by_fingerprint.items():
            if len(duplicates) > 1:
                failures.append(
                    _failure(
                        code="approval.pending_duplicate",
                        message="Multiple pending approvals share the same action fingerprint.",
                        approval_ids=[approval.id for approval in duplicates],
                        action_fingerprints=[fingerprint],
                    )
                )

        executed_by_fingerprint: dict[str, list[MockMutationSummary]] = defaultdict(list)
        for mutation in mutations:
            if mutation.status == "mock_executed":
                executed_by_fingerprint[mutation.action_fingerprint].append(mutation)
        for fingerprint, duplicates in executed_by_fingerprint.items():
            if len(duplicates) > 1:
                failures.append(
                    _failure(
                        code="mutation.duplicate_action",
                        message="Multiple executed mock mutations share one action fingerprint.",
                        mutation_ids=[mutation.id for mutation in duplicates],
                        action_fingerprints=[fingerprint],
                    )
                )

        run_approvals = [approval for approval in approvals if approval.agent_run_id == run.id]
        run_mutations = [
            mutation
            for mutation in mutations
            if mutation.agent_run_id == run.id or mutation.ticket_id == run.ticket_id
        ]
        approval_trace_refs = {
            approval_ref
            for trace in traces
            if trace.category == "approval.create_request"
            for approval_ref in trace.approval_refs
        }
        mutation_trace_refs = {
            approval_ref
            for trace in traces
            if trace.category == "mutation.mock_refund"
            for approval_ref in trace.approval_refs
        }

        for approval in run_approvals:
            if approval.id not in approval_trace_refs:
                failures.append(
                    _failure(
                        code="approval.trace_missing",
                        message="Approval request is not linked from an approval trace.",
                        approval_ids=[approval.id],
                        action_fingerprints=[approval.action_fingerprint],
                    )
                )
            linked_mutations = [
                mutation for mutation in mutations if mutation.approval_request_id == approval.id
            ]
            if approval.status == "pending" and linked_mutations:
                failures.append(
                    _failure(
                        code="mutation.before_approval",
                        message="Pending approval already has a mock mutation.",
                        approval_ids=[approval.id],
                        mutation_ids=[mutation.id for mutation in linked_mutations],
                        action_fingerprints=[approval.action_fingerprint],
                    )
                )
            if approval.status == "rejected" and linked_mutations:
                failures.append(
                    _failure(
                        code="mutation.after_rejection",
                        message="Rejected approval has a mock mutation.",
                        approval_ids=[approval.id],
                        mutation_ids=[mutation.id for mutation in linked_mutations],
                        action_fingerprints=[approval.action_fingerprint],
                    )
                )
            if approval.status == "approved":
                if len(linked_mutations) != 1:
                    failures.append(
                        _failure(
                            code="mutation.missing_for_approved_approval",
                            message="Approved approval must have exactly one mock mutation.",
                            approval_ids=[approval.id],
                            action_fingerprints=[approval.action_fingerprint],
                        )
                    )
                elif approval.id not in mutation_trace_refs:
                    failures.append(
                        _failure(
                            code="mutation.trace_missing",
                            message="Executed mutation is not linked from a mutation trace.",
                            approval_ids=[approval.id],
                            mutation_ids=[linked_mutations[0].id],
                            action_fingerprints=[approval.action_fingerprint],
                        )
                    )

        for mutation in run_mutations:
            if mutation.status != "mock_executed":
                continue
            if mutation.approval_request_id is None:
                failures.append(
                    _failure(
                        code="mutation.approval_missing",
                        message="Mock mutation is missing an approval request.",
                        mutation_ids=[mutation.id],
                        action_fingerprints=[mutation.action_fingerprint],
                    )
                )
                continue
            approval = approvals_by_id.get(mutation.approval_request_id)
            if approval is None:
                failures.append(
                    _failure(
                        code="mutation.approval_missing",
                        message="Mock mutation references an unknown approval request.",
                        approval_ids=[mutation.approval_request_id],
                        mutation_ids=[mutation.id],
                        action_fingerprints=[mutation.action_fingerprint],
                    )
                )
                continue
            if approval.status != "approved":
                failures.append(
                    _failure(
                        code="mutation.approval_not_approved",
                        message="Mock mutation does not reference an approved approval.",
                        approval_ids=[approval.id],
                        mutation_ids=[mutation.id],
                        action_fingerprints=[mutation.action_fingerprint],
                    )
                )
            if approval.action_fingerprint != mutation.action_fingerprint:
                failures.append(
                    _failure(
                        code="mutation.fingerprint_mismatch",
                        message="Approval and mutation action fingerprints do not match.",
                        approval_ids=[approval.id],
                        mutation_ids=[mutation.id],
                        action_fingerprints=[
                            approval.action_fingerprint,
                            mutation.action_fingerprint,
                        ],
                    )
                )

        return failures

    def _resolve_status(
        self,
        failures: list[RunComplianceFailure],
        managed: bool,
    ) -> str:
        if not failures:
            return "passed"
        if not managed and all(
            failure.code
            in {
                "governance.metadata_unsupported",
                "governance.metadata_schema_invalid",
            }
            for failure in failures
        ):
            return "unsupported"
        return "failed"


def _failure(
    *,
    code: str,
    message: str,
    affected_trace_ids: list[str] | None = None,
    missing_ref_categories: list[str] | None = None,
    approval_ids: list[str] | None = None,
    mutation_ids: list[str] | None = None,
    action_fingerprints: list[str] | None = None,
) -> RunComplianceFailure:
    return RunComplianceFailure(
        code=code,
        message=message,
        affected_trace_ids=affected_trace_ids or [],
        missing_ref_categories=missing_ref_categories or [],
        approval_ids=approval_ids or [],
        mutation_ids=mutation_ids or [],
        action_fingerprints=action_fingerprints or [],
    )


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _unique(values) -> list:
    return list(dict.fromkeys(values))
