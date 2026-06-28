# M5 Polish + Portfolio Readiness

## Purpose

M5 turns the working MeterDesk vertical slice into a stable interview and portfolio demo. The
default walkthrough must be understandable on a fresh checkout even when no OpenAI-compatible
provider key is configured.

M5 hardened the Duplicate Charge golden path. The current implementation also seeds Credit/Refund
Dispute as a supporting governed workflow. It does not add real integrations, deployment,
production monitoring, or mock-provider execution mode.

## Demo Seed Model

`make seed` produces the portfolio baseline:

- `TCK-1042` has a completed Duplicate Charge agent run.
- `TCK-1137` has a completed Credit/Refund Dispute agent run.
- The run includes stable trace records for evidence gathering, prior action check, deterministic
  refund eligibility, draft creation, and approval request creation.
- The run includes draft-only internal and customer-facing text.
- A pending approval request exists for the proposed original refund.
- A pending approval request exists for the proposed Credit/Refund goodwill credit.
- No visible mock mutation exists before approval.

This seeded run is a walkthrough artifact. It proves MeterDesk's evidence, trace, draft, and
approval surfaces without requiring a live model call during every demo.

Live provider behavior remains unchanged. A real `POST /tickets/{ticket_id}/agent-runs` for
`TCK-1042` or `TCK-1137` still requires provider configuration and still fails with `503` before
creating a run when configuration is missing.

## Live Reset

M5 adds an explicit reset command for live demos:

- `make demo-reset-live` resets only `TCK-1042` runtime state by default.
- `make demo-reset-live TICKET_ID=TCK-1137` resets only the Credit/Refund Dispute runtime state.
- It removes agent runs, traces, approval requests, and mock mutations for that ticket.
- It preserves tickets, customer accounts, billing evidence, policies, eval cases, eval fixtures,
  and unrelated local rows.

After the reset, the selected Workbench ticket returns to the no-run state and the operator can start
the real governed agent loop if provider configuration is present.

## UI Expectations

M5 polishes the existing Workbench, Approval Queue, and Eval Lab surfaces without adding a new
product surface.

The Workbench should make the golden path easy to scan:

- billing evidence explains the duplicate charge.
- the governance panel shows run state, approval gate, trace entries, draft-only output, and mock
  mutation state in a coherent order.
- targeted empty and error states cover no run, provider missing or failed run, pending approval,
  rejected approval, approved mock mutation, and missing evidence fallback.

Eval Lab keeps Usage Spike results visible as `blocked` coverage gaps. Hiding these gaps would
weaken the eval story.

## Interview Documentation

M5 adds `intv/meterdesk-demo-walkthrough.md` for interview use. It should explain:

- fresh setup and baseline demo flow.
- no-key baseline versus live provider path.
- live reset steps.
- approval safety and mock mutation constraints.
- Eval Lab behavior and why Usage Spike cases are blocked.
- architecture and governance talking points likely to come up in an interview.

README should link to the interview walkthrough instead of becoming the full script.

## Verification

M5 tests focus on demo confidence:

- seed creates the completed baseline run, traces, pending approval, draft outputs, and no mutation.
- live reset clears only the selected ticket runtime state, defaulting to `TCK-1042`.
- approval approve/reject behavior remains idempotent and approval-gated.
- frontend routes render the completed sample, reset/no-run state, provider failure state, approval
  states, Credit/Refund ticket switching, and Eval Lab blocked gaps.

The default API test suite must not depend on local provider configuration. Web verification depends
on a working Node/npm environment.
