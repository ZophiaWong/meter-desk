# AGENTS.md

This file is the operating guide for AI coding agents working in this repository. Read it before making any change.

## Required Reading Order

1. `README.md`
2. `docs/specs/product-scope.md`
3. `docs/specs/system-architecture.md`
4. `docs/specs/agent-governance.md`
5. `docs/specs/eval-strategy.md`
6. `docs/specs/implementation-roadmap.md`
7. `docs/specs/hardening/roadmap.md`

If a task targets an active workstream, read its focused spec after the files above and treat it as
the local source of truth for that subsystem. Files under `docs/archive/` are historical context only
and must not override current specs or an approved active workstream spec.

## Product Guardrails

- MeterDesk is an agent-governed billing support console for usage-based API and AI platforms.
- The v1 golden path is Duplicate Charge.
- Usage Spike and Credit/Refund Dispute are supporting scenarios, not separate product lines.
- The UI direction is Support Workbench: ticket-first investigation with embedded billing evidence, trace, policy context, and approval status.
- The strongest project signals are permission-scoped tools, approval gates, audit traces, and offline evals.

## Hard Constraints

- Do not turn MeterDesk into a generic support chatbot.
- Do not turn MeterDesk into a generic RAG knowledge base.
- Do not turn MeterDesk into a billing CRM or subscription management suite.
- Do not turn MeterDesk into an observability-only trace viewer.
- Do not add real payment mutations or real external support integrations in v1.
- Do not auto-send customer replies. Customer-facing text is draft-only in v1.
- Do not execute refund or credit mutations without human approval.
- Do not add pgvector, large-scale RAG, multi-provider model gateways, or enterprise multi-tenancy unless a later approved spec explicitly changes scope.
- Do not create detailed tool schema docs until the agent/tool spec is explicitly requested.
- Do not create detailed UI design docs until the UI spec is explicitly requested.

## Implementation Expectations

- Keep frontend, backend, agent orchestration, and mock external systems separated by clear interfaces.
- Store durable state and audit records in Postgres once the app is scaffolded.
- Treat mock billing data as realistic product data, not placeholder filler.
- Preserve traceability for agent runs, tool calls, policy citations, approvals, and mock mutations.
- Route all high-risk actions through approval state before mutation.
- Keep low-risk read and draft actions traceable even when they do not require approval.
- Use one live OpenAI-compatible provider in v1 behind a provider boundary; do not build a multi-provider gateway.
- Keep MCP adapter readiness at the tool-layer boundary; do not require a real MCP server for v1.

## Testing and Eval Expectations

- Add or update tests for behavior changes when implementation exists.
- Keep eval design aligned with `docs/specs/eval-strategy.md`.
- Eval cases should score both final outcome and trace behavior.
- Prefer deterministic checks for required evidence, policy compliance, and approval routing.
- Use LLM-as-judge only for open-ended text quality where deterministic checks are insufficient.

## Repo Workflow

- Keep changes focused on the requested task.
- Do not rewrite unrelated files or clean up unrelated local artifacts.
- Do not commit `.superpowers/`; it is a local brainstorming artifact.
- Do not add `AGENT.md`; this repository uses `AGENTS.md` only.
- Update the relevant spec when a code change intentionally changes product scope, architecture boundaries, agent governance, or eval behavior.
- When handoff or archived material conflicts with `AGENTS.md` or a current foundational spec, pause
  the affected work and ask the maintainer to decide; do not silently choose either side.
