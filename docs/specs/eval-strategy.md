# MeterDesk Eval Strategy

## Eval Goal

MeterDesk evals should prove that the agent is useful, governed, and auditable. V1 evals score both the final recommendation and the path the agent took to reach it.

The eval system should avoid brittle checks for one exact tool order. It should instead check whether the agent gathered required evidence, applied policy correctly, routed high-risk actions through approval, and produced an appropriate draft outcome.

## V1 Eval Set

V1 includes 9 offline eval cases:

- 3 Duplicate Charge cases.
- 3 Usage Spike cases.
- 3 Credit/Refund Dispute cases.

Duplicate Charge cases should receive the most polish because they align with the golden path.
Credit/Refund Dispute cases are executable supporting workflow cases. Usage Spike cases remain
blocked coverage gaps until their runner and evidence model are implemented.

Each case should include:

- scenario description.
- ticket context.
- relevant mock billing data.
- expected outcome.
- required evidence categories.
- relevant policy rules.
- expected approval routing.
- grading criteria.

## Grading Dimensions

Each case should score these dimensions:

- **Outcome correctness**: the final recommendation matches the expected resolution.
- **Policy compliance**: the recommendation follows refund, credit, usage, cancellation, or trial policy.
- **Approval routing**: high-risk refund or credit actions create approval requests and do not mutate before approval.
- **Tool planning**: executable governed runs include an LLM-planned investigation plan and backend verifier acceptance before read or decision tools execute.
- **Required evidence**: the trace includes necessary evidence categories such as invoice, charge, usage, credit ledger, prior adjustment, account state, or policy.
- **Draft quality**: internal and customer-facing drafts are clear, professional, and do not overpromise.

## Deterministic Checks

Prefer deterministic checks for:

- required evidence was queried.
- required tool plan and verifier traces were present and accepted.
- required policy was cited.
- high-risk actions were approval-gated.
- rejected approvals did not create mock mutations.
- approved actions created at most one mock mutation.
- final outcome category matches the expected case outcome.

These checks are the main reliability signal for v1.

## LLM-as-Judge Use

LLM-as-judge may be used for open-ended text quality only:

- customer reply clarity.
- tone and professionalism.
- whether the draft avoids unsupported promises.
- whether the internal explanation is understandable.

LLM-as-judge should not replace deterministic checks for evidence coverage, policy compliance, or approval routing.

## Trace Scoring

Eval results should link to the agent run and relevant tool traces.

Trace scoring should answer:

- Did the agent inspect the evidence needed for this scenario?
- Did the agent cite the policy that controls the recommendation?
- Did the agent avoid unsupported assumptions?
- Did the agent route high-risk actions correctly?
- Did tool errors or missing evidence affect the recommendation?

The eval should not require one exact tool sequence unless a later spec introduces a reason to enforce order.

## Eval Lab Expectations

Eval Lab should be lightweight in v1 but should show real quality signals:

- case list grouped by scenario.
- latest run status.
- latest-vs-seeded-baseline regression summary.
- dimension scores.
- failed checks and missing evidence.
- links to final output and trace details.
- prompt, model, or policy version when available.
- compact model, prompt fingerprint, policy, tool-policy, governance-schema, and grader-version diffs
  when comparing snapshots.

Eval Lab is not a full trace replay system in v1.

## Passing Standard

For v1 to be considered credible:

- Duplicate Charge cases should pass all deterministic checks.
- Supporting scenario failures or blocked gaps should be inspectable and actionable.
- Any approval-routing failure should be treated as severe.
- Any mutation-before-approval behavior should be treated as a blocking failure.

## Regression History

Focused regression history is defined in `docs/specs/m10-eval-regression-history.md`.
The v1 comparison model is latest non-baseline eval run versus seeded canonical baseline. Blocked
provider or environment states are incomparable, not agent regressions. Usage Spike remains a
coverage gap until its governed runner is implemented.

## Deferred Eval Work

- Complete trace replay and diffing.
- Large eval datasets.
- Online production monitoring.
- Pairwise model comparison dashboards.
- Multi-provider eval benchmarking.
