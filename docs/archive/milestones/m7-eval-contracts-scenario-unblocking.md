# M7 Eval Contracts + Scenario Unblocking

> **Archive status:** Historical implementation spec from the completed M0-M10 program. It is
> non-authoritative and cannot override `AGENTS.md`, current foundational specs, or an approved
> active workstream spec. Start from the [documentation index](../../README.md).

## Purpose

M7 makes evals prove that MeterDesk agent runs are not only outcome-correct, but also governed and
auditable. It consumes the M6 runtime contract instead of redefining it.

The eval system should remain deterministic for governance-critical checks. LLM-as-judge may help
with draft quality and human-readable summaries, but it must not decide whether evidence, policy,
approval, mutation, or governance requirements passed.

M7 also defines how supporting scenarios can move from blocked coverage gaps to executable governed
scenarios without turning MeterDesk into a broad billing CRM. Credit/Refund Dispute now follows this
path; Usage Spike remains blocked.

## Run Compliance Check

M7 introduces a read-only Run Compliance Check for existing agent runs. A suggested internal API is:

```text
GET /agent-runs/{agent_run_id}/compliance
```

The check is computed on demand from current database state. It does not create agent runs, call the
provider, create approval requests, execute mutations, or persist a new compliance table.

The result shape should include:

- status: `passed`, `failed`, or `unsupported`.
- `checked_at`.
- failed checks.
- reason codes.
- affected trace ids.
- missing ref categories.
- policy ids and versions seen.
- high-risk gate count.
- verified governed action count.

Eval results may persist a snapshot of the compliance result because an eval result is itself a
recorded test outcome.

## Compliance Rules

Run Compliance Check must not blindly trust a trace's stored `gate_result`. It should recompute
compliance by reading:

- the current ToolPolicy registry.
- typed governance metadata.
- trace evidence, policy, approval, and negative evidence refs.
- approval records.
- mock mutation records.
- action fingerprints where applicable.

Managed runs must fail if required governance metadata is missing or invalid. Managed runs include
the seeded portfolio baseline, live governed loop runs, and eval fixture runs.

Legacy or unknown-source runs may return `unsupported` when they lack the current metadata schema.
This compatibility path must not allow current seeded, live, or eval fixture runs to escape the
quality gate.

## Eval Dimension Updates

Eval results should add a blocking deterministic dimension:

```text
governance_compliance
```

If the final outcome is correct but `governance_compliance` fails, the whole case fails. Governance
metadata is part of the required behavior, not optional explanation.

`blocked` and `failed` should be distinct:

- `blocked`: the case could not execute because the provider is missing, a scenario runner is not
  implemented, or required environment configuration is absent.
- `failed`: the case executed and produced an incorrect outcome, missing evidence, policy failure,
  approval routing failure, mutation safety failure, draft safety failure, or governance compliance
  failure.

The seeded Duplicate Charge portfolio baseline created by `make seed` must pass Run Compliance
Check. No-key demos should still be able to prove the audit chain for the seeded baseline.

## Workbench And Eval Lab Surface

Workbench should show a compact compliance status for the current run:

- compliance status.
- verified governed action count.
- high-risk gate count.

Details may be expanded inside the existing Rules Drawer. The drawer may show reason codes, affected
trace ids, missing refs, and policy versions. The default Workbench Safety Rail should remain focused
on the current ticket state: run, approval, mutation, trace, and draft.

Compliance failures in Workbench are read-only diagnostic warnings. They do not disable approval
buttons or create a second operation gate. Runtime enforcement still belongs to the Governance Kernel
and DB safety constraints.

Eval Lab should display compliance failures as part of eval details. It should make clear which
checks failed and which traces or records caused the failure.

## LLM Boundary

M7 itself limits LLM use to:

- draft quality review for clarity, tone, and unsupported promises.
- optional human-readable summaries of deterministic failed checks.

LLM output may explain deterministic failures, but it must not generate the pass or fail result for
governance, evidence, policy, approval routing, mutation safety, or action fingerprint checks.

M9 adds a separate bounded planner before governed reads and decisions. Its plan is evaluated by
deterministic `tool_planning` checks and does not decide outcomes, approvals, or mutations.

## Scenario Readiness Matrix

Supporting scenarios should remain blocked until they meet explicit readiness gates. The matrix
lists governed action categories, but does not define detailed tool JSON schemas before a focused
agent/tool spec is requested.

### Credit/Refund Dispute

Credit/Refund Dispute is the second executable governed workflow. It stays a v1 supporting scenario
because it reuses the existing refund, credit, approval, and mutation safety semantics instead of
creating a separate billing CRM path.

Implemented readiness:

- evidence model for trial credit grants, credit consumption, credit expiry, cancellation timing,
  prior adjustments, invoices, and charges.
- explicit policy rules for trial credit expiry, cancellation refund eligibility, and prior
  adjustment limits.
- candidate governed actions:
  - `read.credit_refund_evidence`
  - `read.prior_financial_actions`
  - `decision.credit_refund_eligibility`
  - `draft.resolution`
  - `approval.create_request`
  - `mutation.mock_credit_or_refund`
- deterministic decision tool that owns outcome category, amount, target credit or charge, required
  evidence refs, policy refs, and approval requirement.
- eval fixtures that cover goodwill credit approval, cancellation refund approval, and prior
  adjustment already applied.
- acceptance gates for governance metadata, approval routing, mutation safety, and draft safety.

### Usage Spike

Usage Spike remains valuable because it highlights usage-based billing, but it needs a richer meter
and pricing evidence model before it should become executable.

Required readiness:

- evidence model for usage windows, baseline usage, spike period, meter dimensions, invoice line
  items, unit pricing, account plan, and prior credits.
- explicit policy rules for metered usage billing, overage explanation, anomaly handling, and
  goodwill credit eligibility.
- candidate governed actions:
  - `read.usage_spike_evidence`
  - `read.prior_financial_actions`
  - `decision.usage_spike_resolution`
  - `draft.resolution`
  - `approval.create_request`
  - `mutation.mock_goodwill_credit`
- deterministic decision tool that distinguishes expected billing behavior, anomaly requiring
  human review, and goodwill credit recommendation.
- eval fixtures that cover expected usage spike, possible anomaly, and goodwill credit request.
- acceptance gates for usage evidence coverage, policy compliance, approval routing, mutation
  safety, and draft safety.

## Expansion Priority

Credit/Refund Dispute has been unblocked. The remaining recommended expansion is Usage Spike,
because it adds the more complex usage-meter and pricing explanation surface.

## Verification Expectations

Tests should cover:

- Run Compliance Check pass for seeded Duplicate Charge baseline.
- managed run with missing governance metadata returns failed.
- legacy or unknown run with old metadata returns unsupported.
- compliance recomputation from registry and current DB state.
- high-risk mutation without approved approval fails compliance.
- duplicate action fingerprint fails compliance.
- eval `governance_compliance` is blocking.
- provider missing remains blocked, not failed.
- Usage Spike runner absence remains blocked, not failed.
- Workbench compact compliance status and drawer details.
- Eval Lab compliance details and failed checks.
