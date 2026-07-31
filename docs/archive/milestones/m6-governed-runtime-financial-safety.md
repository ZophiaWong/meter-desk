# M6 Governed Runtime + Financial Safety

> **Archive status:** Historical implementation spec from the completed M0-M10 program. It is
> non-authoritative and cannot override `AGENTS.md`, current foundational specs, or an approved
> active workstream spec. Start from the [documentation index](../../README.md).

## Purpose

M6 upgrades MeterDesk's current governance implementation from a V0 trace kernel into a
production-minded governed action runtime for the Duplicate Charge golden path.

The goal is not broader chatbot autonomy. The goal is to ensure each governed agent or backend
action is executed through one policy-aware path with evidence requirements, approval gates,
financial safety checks, and auditable trace metadata.

M6 stayed focused on the existing Duplicate Charge flow. A later implementation unblocked
Credit/Refund Dispute as the second governed workflow; Usage Spike remains a supporting scenario
until its governed loop is explicitly designed and implemented.

## Current Baseline And Required Delta

MeterDesk already has a code-first `ToolPolicy` registry, `GovernanceKernel.record_action`,
`governance_metadata` on tool traces, and a read-only `/governance/tool-policies` matrix used by the
Workbench drawer.

This baseline is useful, but it is still a V0 trace kernel:

- it centralizes policy metadata and trace recording.
- it blocks missing required refs for trace writes.
- it enforces approved approval refs for high-risk trace writes.
- it does not yet wrap action execution itself.
- it does not yet own the transaction boundary for approval creation or mock mutation execution.
- it does not write blocked action attempts as trace records.
- it stores governance metadata as a loose JSON object.
- it does not have a first-class `action_fingerprint` column or DB uniqueness constraints for
  duplicate financial actions.

M6 should preserve the existing registry and drawer direction while hardening the runtime contract.

## Governed Runtime Contract

All Duplicate Charge governed actions must execute through the Governance Kernel:

- billing evidence read.
- prior financial action read.
- refund eligibility decision.
- resolution draft.
- approval request creation.
- approved mock refund mutation.

The kernel owns this sequence:

1. preflight policy lookup and ref validation.
2. approval gate validation when required.
3. action execution.
4. postcondition validation.
5. trace write with governance metadata.

For read, decision, and draft actions, execution may be lightweight and non-transactional when no
financial side effect is possible. For approval creation and mock mutation execution, the kernel must
coordinate a transaction-aware action wrapper.

Services and orchestrators may assemble action inputs. Repository methods should provide atomic
persistence primitives. Permission to create approval requests or execute mock mutations belongs to
the kernel path, not to ad hoc service code.

## ToolPolicy Registry

`policy_id` is a stable action identity and must not include a version suffix such as `-v1`.
`policy_version` is a separate field and should use semantic versioning such as `1.0.0`.

The existing `/governance/tool-policies` response should remain broadly compatible for the Workbench
drawer. It should continue to expose action id, label, category, risk, executor, gate, required refs,
approval requirement, trace requirement, and eval dimensions. New fields should be additive unless a
later UI spec explicitly changes the drawer contract.

Tool policy versions describe the governance contract for tool execution. They are separate from
business policy citations such as `REFUND-DUP-001 v2026.02`.

## Governance Metadata

`governance_metadata` should remain stored as JSONB, but application and API code should treat it as
a typed schema rather than an unconstrained dict.

The typed metadata should preserve existing field names where practical:

- `schema_version`
- `policy_id`
- `policy_version`
- `risk`
- `gate`
- `gate_result`
- `enforcement_outcome`
- `required_ref_categories`
- `satisfied_ref_categories`
- `missing_ref_categories`
- `negative_evidence_refs`
- `trace_required`
- `reason_code`

Negative evidence must be explicit. A prior action check that finds no prior mock refund should
record a structured value such as `no_prior_mock_mutation`, not only a natural-language output
summary. This lets audit and eval distinguish "not checked" from "checked and none found."

## Blocked Action Traces

When the kernel blocks a governed action, it should not execute the action. It should still write a
blocked trace entry to `tool_traces` when an agent run exists.

The blocked trace represents an attempted governed action, not a successful tool execution. Its
metadata should clearly identify the policy, missing refs or failed gate, and reason code. Examples:

- `governance.missing_required_ref`
- `governance.approval_gate_blocked`
- `governance.unknown_policy`

Governance contract violations are system failures, not business outcomes. They must not be
translated into `insufficient_evidence_human_review`.

## Financial Safety

M6 introduces `action_fingerprint` as a first-class field for financial approval and mock mutation
records. It identifies the business financial action, not only the approval request. For the current
Duplicate Charge path, the fingerprint should be derived from stable action inputs such as ticket,
action type, target charge, amount, and currency.

The lifecycle rules are:

- one pending approval per `action_fingerprint`.
- rejected approvals do not permanently block the same fingerprint from being proposed again.
- approved and executed fingerprints cannot be executed again.
- repeated approve calls for the same approval return the existing mutation.
- a different fingerprint may start a separate approval and mutation path.

Database uniqueness constraints are the concurrency safety backstop. The kernel should preflight for
clear operator-facing errors, but DB conflicts must still be translated into stable reason codes such
as `approval.pending_duplicate` or `mutation.duplicate_action` instead of leaking raw 500 errors.

## API, UI, And Error Surface

Governance, approval, provider, and mutation errors should use a stable internal API error shape:

```json
{
  "code": "governance.missing_required_ref",
  "message": "Missing required governance refs.",
  "details": {}
}
```

This does not require a broad public API design. It only standardizes errors for the current internal
FastAPI resources that participate in governed agent execution.

The Workbench should keep the current ticket-first layout. The read-only governance matrix remains
behind the existing Rules Drawer. M6 should not add a standalone Governance page, editable registry,
or trace viewer product surface.

Trace cards may show compact rule-applied metadata, but the full matrix and diagnostic details should
stay behind disclosure UI so the Workbench Safety Rail remains readable.

## Explicit Deferrals

M6 does not add:

- Usage Spike or Credit/Refund Dispute governed loops.
- real payment, support, messaging, or accounting integrations.
- automatic customer replies.
- complete auth, role-based access control, or multi-tenant permission systems.
- editable tool registry or tool marketplace.
- production monitoring platform.
- full audit event log or event sourcing.
- approval decision traces for approve or reject actions.

Approval records remain the source of truth for approve and reject decisions. Governed traces focus
on agent/tool actions and the high-risk mock mutation action.

## Verification Expectations

Tests should cover:

- each registered Duplicate Charge policy.
- allowed action metadata writes.
- blocked traces for missing refs and failed gates.
- typed governance metadata schema.
- negative evidence refs.
- namespaced reason codes.
- approval creation through the kernel path.
- mock mutation execution through the kernel path.
- `action_fingerprint` generation and duplicate prevention.
- DB uniqueness conflicts translated to stable errors.
- Workbench drawer compatibility with the policy matrix.
