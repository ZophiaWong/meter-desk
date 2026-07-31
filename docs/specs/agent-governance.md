# MeterDesk Agent Governance

## Governance Goal

MeterDesk agents should accelerate billing investigation without gaining uncontrolled authority. The agent may read evidence, apply policy, draft recommendations, and request approval. It may not execute high-risk financial actions unless a human approves them.

## Tool Permission Categories

V1 tools should be described by category until a detailed tool schema spec is requested:

- **Read tools**: retrieve ticket, account, invoice, charge, usage, credit ledger, prior adjustment, subscription, pricing, and policy evidence.
- **Decision tools**: check refund or credit eligibility, calculate proposed amounts, and classify the resolution path.
- **Draft tools**: produce internal resolution notes, approval summaries, and customer reply drafts.
- **Approval tools**: create approval requests and read approval state.
- **Mutation tools**: apply approved mock refunds or credits and record mock mutation results.

Tool names, JSON schemas, and exact payloads are deferred. The category boundaries are not deferred.

Current governed action ids include Duplicate Charge and Credit/Refund Dispute paths:

- `plan.investigation`
- `plan.verify`
- `read.billing_evidence`
- `read.credit_refund_evidence`
- `read.prior_financial_actions`
- `decision.refund_eligibility`
- `decision.credit_refund_eligibility`
- `draft.resolution`
- `approval.create_request`
- `mutation.mock_refund`
- `mutation.mock_credit_or_refund`

## Risk Levels

- **Low risk**: read evidence, summarize evidence, cite policy, draft internal notes, and draft customer replies. These actions do not require approval but must be traced.
- **Medium risk**: calculate a proposed refund or credit amount, classify eligibility, and create an approval request. These actions do not mutate billing state but must be traceable and reviewable.
- **High risk**: refund or credit mutation, even when mocked. These actions require explicit human approval before execution.

## Approval Gate

High-risk actions must follow this lifecycle:

1. The agent proposes a financial action with amount, reason, evidence, and policy citation.
2. FastAPI creates an approval request.
3. The action remains blocked while approval is pending.
4. A human approves or rejects the request.
5. Approved requests may execute one mock mutation.
6. Rejected requests must not execute a mutation.
7. The approval decision and resulting mock mutation are recorded in the audit trail.

The agent must not bypass approval by calling mutation tools directly.

## Draft-Only Customer Replies

Customer-facing text is draft-only in v1.

- The agent may draft a reply.
- The UI may display and edit the draft.
- The system must not send email, chat, ticket replies, Slack messages, Feishu messages, or any other customer communication.
- The draft must avoid promising refunds or credits before approval.

## Policy Citation Rules

Agent recommendations should cite policy when policy determines the outcome.

Policy citations should include:

- policy identifier.
- policy version or effective date when available.
- short reason the policy applies.
- relationship to the evidence collected.

Policy handling in v1 is explicit policy text plus eligibility checks. Do not add vector search or large-scale RAG as a shortcut.

## Trace Requirements

Every agent run should preserve enough trace context for audit and eval:

- agent run identifier.
- ticket identifier.
- model and prompt version when available.
- LLM investigation plan, tool rationale, evidence targets, and verifier accept/block result.
- tool category and permission level.
- input summary.
- output summary.
- evidence references.
- policy references.
- approval references.
- error state when a tool fails.
- final recommendation and draft outputs.

Trace records should make it possible to explain what the agent saw, what it did, what it proposed, and what the human approved.

## Mock Mutation Constraints

Mock refund and credit mutations must:

- require an approved approval request.
- record the approved amount and reason.
- link back to the ticket, agent run, evidence, and approval request.
- avoid duplicate execution for the same approval.
- be visibly mock-only in UI and data.

Mock mutations are product evidence for governance behavior. They are not a path toward real payment processing in v1.

## Post-M10 Hardening Direction (Planned)

Later workstreams may strengthen governance only through focused specs and automated evidence:

- approval actors must come from a server-verified principal, not a client-selected request field.
- approval roles and audit identity must be enforced and persisted at the backend boundary.
- queued, retried, cancelled, or replayed execution must not duplicate approvals or mutations.
- workflow states and terminal outcomes must distinguish investigation completion, approval waiting,
  rejection, cancellation, failure, and executed mock mutation where applicable.
- provider and tool failures must use stable categories, bounded retries, deadlines, sanitization,
  and trace propagation.
- typed tool contracts must retain risk, evidence, gate, executor, and trace requirements.
- context construction must record selected/excluded evidence, versions, redactions, and trust
  classification without granting the model new financial authority.

The planned network boundary is a repository-local read-only mock billing service. It does not
authorize real external reads or writes. Detailed tool schemas remain deferred until the focused
typed-tool workstream is explicitly designed and approved.

## Failure Handling

If the agent lacks required evidence, it should say so and avoid unsupported recommendations.

If policy is ambiguous, the agent should draft a conservative resolution and request human review.

If a tool fails, the trace should record the failure and the final recommendation should not pretend the missing evidence was checked.
