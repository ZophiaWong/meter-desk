# MeterDesk Product Scope

## Product Thesis

MeterDesk is an agent-governed billing support SaaS for usage-based API and AI platforms. It helps support and billing operators investigate disputes, cite policy, draft resolutions, and route high-risk financial actions to human approval.

The core product is not customer chat. The core product is a controlled investigation workbench where AI agents operate through permission-scoped tools and leave auditable evidence.

## V1 Golden Path

The v1 golden path is **Duplicate Charge**.

The successful end-to-end flow is:

1. A support operator opens a duplicate charge ticket in the Ticket Workbench.
2. The agent reviews relevant account, invoice, charge, credit, and policy evidence.
3. The agent identifies whether the issue is a duplicate charge, expected billing behavior, or insufficient evidence.
4. The agent drafts an internal resolution and a customer reply.
5. If a refund or credit is warranted, the agent creates an approval request.
6. A human approves or rejects the proposed financial action.
7. Approved actions execute as mock mutations only.
8. The run, tool trace, approval decision, policy citations, and mock mutation are stored for audit and eval.

The golden path should be the most polished demo path in v1. Other scenarios should reuse the same system patterns instead of creating parallel workflows.

## Supporting Scenarios

MeterDesk v1 also supports two secondary scenarios:

- **Usage Spike**: investigate a sudden increase in metered usage, assemble usage evidence, apply usage and billing policy, and route any goodwill credit through approval.
- **Credit/Refund Dispute**: investigate trial credits, cancellation timing, refund eligibility, prior adjustments, and policy disputes.

These scenarios exist to prove that the same agent governance and eval framework generalizes beyond the golden path. They should not expand v1 into a broad billing operations platform.

## Product Surfaces

- **Ticket Workbench**: the main entrypoint for ticket investigation, billing evidence, agent trace, policy context, draft resolution, and approval state.
- **Approval Queue**: a focused queue for reviewing, approving, and rejecting high-risk financial actions.
- **Eval Lab**: a lightweight interface for running offline eval cases and inspecting outcome and trace scores.

Detailed visual design is deferred to a later UI spec. The confirmed direction is Support Workbench, inspired by ticket-first support tools with embedded billing investigation context.

## V1 Positioning

MeterDesk should communicate three capabilities:

- Full-stack AI product shell: a coherent product experience, not a script demo.
- Agent infrastructure core: governed tools, traces, approvals, and durable audit state.
- Applied AI decision quality: policy-grounded reasoning and offline evals.

## Post-M10 Hardening Direction (Partially Implemented)

The approved hardening phase improves engineering evidence without changing the product thesis or
adding a new product line. Planned work may make the existing application easier to build, operate,
recover, audit, and evaluate, but it must preserve:

- Duplicate Charge as the golden path.
- Credit/Refund Dispute and Usage Spike as supporting scenarios.
- the ticket-first Support Workbench, Approval Queue, and Eval Lab surfaces.
- backend authority for evidence, deterministic decisions, approval gates, and mutations.
- draft-only customer replies and mock-only financial mutations.

P0-02 introduces local/demo authentication for trusted approval actors without changing the product
surfaces or creating a real account system. Fixed support operator, approver, and admin identities
exercise server-owned RBAC; this mode is explicitly rejected in production configuration.

Later hardening may introduce background execution, operational telemetry, typed tool/context
contracts, and a repository-local mock billing HTTP service. The HTTP service proves a network
boundary without becoming a real Stripe, payment, support, or accounting integration. Any real
third-party adapter requires a separate product-scope decision before design or implementation.

## Out of Scope

- Real payment system integrations.
- Real Stripe, Zendesk, Slack, Feishu, or enterprise messaging integrations.
- Automatic customer replies.
- Standalone tool registry editor.
- Complex workflow builder.
- Required MCP server implementation.
- pgvector or large-scale retrieval-augmented generation.
- Multi-provider model gateway.
- Enterprise multi-tenant permission systems.
- Trace replay lab.
- Security incident, API key leak, or SLA incident workflows.

## V1 Success Criteria

MeterDesk v1 succeeds when a reviewer can:

- Understand the Duplicate Charge flow without reading code.
- See why the agent reached its recommendation.
- Verify that high-risk actions require human approval.
- Inspect a durable audit trail for agent actions and mock mutations.
- Run offline evals that check both final answers and trace behavior.
