# M10 Eval Regression History + Model/Prompt Diff

> **Archive status:** Historical implementation spec from the completed M0-M10 program. It is
> non-authoritative and cannot override `AGENTS.md`, current foundational specs, or an approved
> active workstream spec. Start from the [documentation index](../../README.md).

## Purpose

M10 upgrades Eval Lab from latest-only eval results to lightweight regression history. The goal is
to answer whether governed agent quality improved, regressed, or became incomparable against a
seeded canonical baseline.

This remains a v1 Eval Lab feature, not a general experiment platform. M10 does not add arbitrary
pairwise run comparison, manual baseline promotion, full prompt text diffing, full trace replay,
model leaderboards, multi-provider benchmarking, or online monitoring.

## Data Model

Eval history is snapshot based:

- `eval_suite_runs` records seeded baselines, run-all batches, and standalone case reruns.
- `eval_result_snapshots` stores immutable case-level snapshots for `baseline` and user runs.
- `eval_results` remains the latest-result projection for existing Eval Lab cards and APIs.

Seed data includes one canonical baseline run and one baseline snapshot per eval case. Executable
Duplicate Charge and Credit/Refund Dispute cases have seeded passing baselines. Usage Spike cases
remain seeded blocked coverage gaps and are not counted as agent regressions.

Each result snapshot stores:

- status, summary, dimension scores, failed checks, missing evidence, and policy refs seen.
- compact trace signature: ordered action categories, evidence categories, policy refs, approval
  refs, and governance reason codes.
- planning and compliance snapshots already produced by the eval runner.
- deterministic explanation lines for failure, blocked, or unchanged states.
- version metadata: model, prompt version, prompt fingerprint, domain policy refs, tool policy
  versions, governance schema version, grader version, and result schema version.

Prompt fingerprint is derived from the prompt contract bundle: provider system prompts, structured
response schemas, and scenario plan contracts. M10 does not store full prompt text snapshots.

## Comparison Rules

The backend owns regression comparison. The default comparison target is the latest non-baseline
eval run against the seeded baseline for the same case.

Case labels are deterministic:

- `regressed`: a blocking dimension changed from `pass` to `fail`, or a passed baseline now fails.
- `improved`: a blocking baseline failure now passes, or a coverage gap becomes executable and
  passes.
- `unchanged`: no blocking regression is present.
- `incomparable`: provider, environment, schema, or missing-current-run state prevents agent quality
  comparison.
- `coverage_gap`: the case is intentionally blocked because the scenario runner is not implemented.

Blocked provider or environment states are not agent regressions. Usage Spike remains a visible
coverage gap until its governed runner and evidence model are implemented.

Eval Lab may show aggregate counts and blocking pass rate, but must not collapse governance-critical
dimensions into a single weighted quality score.

## API And UI

New read APIs:

- `GET /eval-regression/summary`
- `GET /eval-runs`
- `GET /eval-runs/{eval_run_id}/comparison`
- `GET /eval-cases/{case_id}/history`

Existing eval execution APIs keep their shape:

- `POST /eval-runs` creates a suite run and current snapshots.
- `POST /eval-cases/{case_id}/run` creates a standalone case rerun and current snapshot.

`/eval-lab` remains the overview surface. It shows latest-vs-baseline counts, blocking pass rate,
compact case labels, and links to a focused run diff route. The detail route shows dimension diffs,
version diffs, trace signature diffs, and deterministic explanations without implementing full
trace replay.

## Verification Expectations

Tests should cover:

- seeded baseline snapshots for executable cases and Usage Spike coverage gaps.
- immutable snapshot history while preserving latest-result projection compatibility.
- latest-vs-baseline regression, improvement, unchanged, incomparable, and coverage-gap labels.
- prompt fingerprint and version diff behavior.
- deterministic explanation output for failures and blocked states.
- frontend overview counts, compact labels, detail links, and diff rendering.
