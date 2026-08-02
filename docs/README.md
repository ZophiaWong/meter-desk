# MeterDesk Documentation

This index separates current requirements from active delivery guidance, engineering evidence, and
historical context. When documents disagree, do not silently choose one: use the conflict escalation
protocol below.

## Authority Order

1. [`AGENTS.md`](../AGENTS.md) defines repository operating rules and product guardrails.
2. The foundational specs define the current product and system contracts:
   - [Product Scope](specs/product-scope.md)
   - [System Architecture](specs/system-architecture.md)
   - [Agent Governance](specs/agent-governance.md)
   - [Eval Strategy](specs/eval-strategy.md)
3. [Implementation Roadmap](specs/implementation-roadmap.md) identifies the current delivery phase.
4. [Post-M10 Hardening Roadmap](specs/hardening/roadmap.md) defines the active workstream sequence and gates.
5. The active workstream feature spec defines its accepted requirements. The current workstream is
   [P0-02 Authentication and Approval RBAC](specs/hardening/p0-02-authentication-approval-rbac.md).
6. A fresh implementation plan may sequence an approved feature spec, but cannot change its public
   contracts, invariants, or acceptance criteria.
7. [Engineering Evidence Matrix](evidence/engineering-evidence-matrix.md) records evidence status; it
   does not define requirements.
8. [`docs/archive/`](archive/README.md) preserves history and is never authoritative.

## Current Phase

The M0-M10 vertical product program is complete. MeterDesk is now in a post-M10 portfolio-hardening
phase focused on reproducible runtime evidence, trusted approval identity, explicit workflow state,
recoverable execution, operational evidence, typed tool boundaries, and stronger regression proof.

Hardening preserves the Duplicate Charge golden path, draft-only customer replies, human approval
for financial actions, mock-only mutations, one OpenAI-compatible provider boundary, and the current
v1 product surfaces.

## Conflict Escalation

If handoff material, an archived document, `AGENTS.md`, or a foundational spec conflicts:

1. pause the affected change;
2. report the exact documents and sections, conflict category, downstream impact, available
   resolutions, and a recommendation;
3. wait for the maintainer's decision;
4. record the decision in the relevant active spec or archive notice before continuing.

Unaffected work may continue only when it does not leave the active documentation in a partial or
internally inconsistent state.

## Supporting Material

- [`docs/diagrams/`](diagrams/README.md) contains architecture and demo diagrams.
- [Seeded Container Demo Runbook](runbooks/container-demo.md) documents the local container runtime,
  its reset boundary, and cleanup safety.
- [`docs/screenshots/`](screenshots/) contains current portfolio screenshots.
- [`docs/troubleshooting/`](troubleshooting/) contains focused local-development guidance.
- [`intv/`](../intv/) contains interview preparation and demo material.
