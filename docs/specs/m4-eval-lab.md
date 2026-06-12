# M4 Eval Lab

## Purpose

M4 adds a lightweight offline eval core for MeterDesk. It proves that the governed agent produces
auditable Duplicate Charge outcomes without turning Eval Lab into a general experiment platform.

The eval system scores both final outcome and trace behavior. It prioritizes deterministic checks
for governance-critical behavior and uses LLM-as-judge only as advisory draft-quality feedback.

## Scope

M4 implements:

- three executable Duplicate Charge eval cases.
- six supporting scenario cases shown as explicit blocked coverage gaps.
- deterministic graders for outcome, evidence, policy, approval routing, mutation safety, and draft
  safety.
- latest-only eval results linked to agent runs and compact trace references.
- Eval Lab controls for running all cases or rerunning one case.

M4 does not implement Usage Spike or Credit/Refund Dispute agent workflows, async eval jobs, full
trace replay, run history, large dataset management, online monitoring, or model comparison.

## Data Model

`eval_cases` gains a nullable `fixture_ticket_id` that points to the hidden ticket used by the eval
runner. Eval fixture tickets are real domain rows so the runner exercises the same repository,
trace, approval, and mock mutation paths as the product workbench. They are hidden from the normal
ticket list.

`eval_results` gains a `details` JSON object for compact explanation data:

- `failed_checks`
- `missing_evidence`
- `policy_refs_seen`
- `trace_refs`
- `blocked_reason`
- `judge_notes`

Eval results are latest-only per case. Running a case replaces its prior result and resets only that
case's eval fixture state. Workbench demo tickets and their runs, approvals, and mock mutations are
not reset by Eval Lab.

## Eval Cases

Duplicate Charge cases run through the real governed agent loop:

- two captured invoice-total charges: `confirmed_duplicate_charge`, approval required.
- one captured charge plus a matching uncaptured authorization: `no_refund_expected_billing_behavior`,
  no financial action.
- one captured charge with no second explainable payment event:
  `insufficient_evidence_human_review`, no mutation.

Supporting Usage Spike and Credit/Refund Dispute cases remain in the case catalog but return
`blocked` results because their scenario runners are intentionally deferred.

## Runner And Graders

Eval execution is synchronous:

- `POST /eval-cases/{case_id}/run` runs one case.
- `POST /eval-runs` runs all cases sequentially.

Each case writes an `EvalResultSummary`. One case failure or blocked state does not stop the rest of
the run.

Duplicate Charge evaluation uses the live M3 provider boundary by default. If provider configuration
is missing or unavailable, executable Duplicate Charge cases return `blocked` instead of failing the
API request. Tests may inject a fake provider.

Requires-approval cases stop at pending approval. Eval Lab verifies that an approval request exists
and that no mock mutation was created before approval. Approve/reject mutation behavior remains
covered by M3 workflow tests.

Deterministic dimension values are `pass`, `fail`, `blocked`, or `not_run`. The blocking dimensions
are:

- `outcome_correctness`
- `required_evidence`
- `policy_compliance`
- `approval_routing`
- `mutation_safety`
- `draft_safety`

LLM-as-judge feedback is advisory. Judge failure or missing configuration sets `draft_quality` to
`not_run` and records the reason in `details.judge_notes`; it does not change deterministic pass or
fail status.

## UI Expectations

Eval Lab shows case groups, status, dimension results, failed checks, missing evidence, blocked
reason, model, prompt version, policy refs, and compact trace references. It provides `Run all` and
per-case `Rerun` controls. Compact trace references are displayed in the case cards; M4 does not add
a full trace replay page.
