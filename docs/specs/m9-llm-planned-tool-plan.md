# M9 LLM-Planned, Backend-Verified Tool Plan

## Purpose

M9 makes the live governed agent loop show real LLM investigation planning before backend tools run.
The provider proposes a strict investigation plan, and the backend accepts or blocks it before any
billing evidence read, deterministic decision, approval creation, draft, or mutation path executes.

This does not move billing truth or financial authority to the model. The LLM controls only the
bounded read-and-decision request plan. The backend continues to own tool arguments, deterministic
outcomes, approval routing, compliance checks, and all mock mutations.

## Runtime Contract

The planner receives only ticket context and the scenario contract:

- ticket id, title, summary, and scenario.
- allowed action ids.
- evidence target vocabulary.
- required action ids and required evidence targets.

The planner does not receive full billing evidence before planning. It returns a strict JSON plan
with steps, action ids, evidence targets, rationale, evidence gaps, and stop conditions.

The Plan Contract Verifier is a control-flow verifier. It checks:

- the scenario matches the ticket.
- each action id exists and is allowed for that scenario.
- draft, approval, and mutation actions are not planner-driven.
- required actions are present.
- required evidence targets are covered.
- decision actions occur after required read actions.
- each step includes a rationale.

If a plan is blocked, the verifier returns reason codes to the planner and retries once. A successful
retry records only the final accepted plan and verifier traces, with earlier blocked reasons nested
in planning metadata. Two blocked attempts fail the run before downstream tools execute.

## Scenario Contracts

Duplicate Charge requires:

- `read.billing_evidence`
- `read.prior_financial_actions`
- `decision.refund_eligibility`

Required targets are `account_state`, `invoice`, `charges`, `payment_status`, `credit_ledger`,
`usage`, `policy`, and `prior_financial_actions`.

Credit/Refund Dispute requires:

- `read.credit_refund_evidence`
- `read.prior_financial_actions`
- `decision.credit_refund_eligibility`

Required targets are `account_state`, `invoice`, `charges`, `payment_status`, `credit_ledger`,
`subscription`, `policy`, and `prior_financial_actions`.

Usage Spike remains blocked until its evidence model and governed runner are implemented.

## Trace And Eval

M9 adds two governed actions to the code-first registry:

- `plan.investigation`
- `plan.verify`

Both are low-risk, trace-required actions. Planning details live in typed nested
`governance_metadata.planning` on existing tool traces. No new database table or product surface is
required.

Eval Lab adds a blocking deterministic dimension:

- `tool_planning`

The grader checks plan trace presence, verifier acceptance, required actions and targets, non-empty
rationales, forbidden action absence, and alignment between the normalized plan and subsequent
read/decision traces. LLM-as-judge is not used for planning correctness.

## Deferrals

M9 does not add granular read tools such as `read.invoice` or `read.charge`. The planner may express
fine-grained evidence targets, but the backend maps accepted plans to existing coarse read tools.

M9 does not add a standalone tool registry editor, workflow builder, full trace replay page, real MCP
server, real external integrations, or any real payment mutations.
