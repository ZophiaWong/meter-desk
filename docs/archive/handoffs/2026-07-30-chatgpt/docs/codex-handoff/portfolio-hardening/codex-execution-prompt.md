# Codex Execution Prompt — P0-01 CI and Runtime Baseline

Copy the content below into Codex after these files have been added to the repository.

---

You are implementing one bounded MeterDesk hardening workstream: **P0-01 CI and Runtime Baseline**.

Read these files in order:

1. `AGENTS.md`
2. `README.md`
3. `docs/specs/product-scope.md`
4. `docs/specs/system-architecture.md`
5. `docs/specs/agent-governance.md`
6. `docs/specs/eval-strategy.md`
7. `docs/specs/implementation-roadmap.md`
8. `docs/codex-handoff/portfolio-hardening/README.md`
9. `docs/codex-handoff/portfolio-hardening/current-state.md`
10. `docs/codex-handoff/portfolio-hardening/specs/P0-01-ci-runtime-baseline.md`
11. `docs/superpowers/plans/2026-07-30-meterdesk-ci-runtime-baseline.md`

Implement only the selected plan.

## Execution requirements

- Work in an isolated branch or worktree.
- Follow the implementation plan task by task.
- Run every specified pre-implementation/failing check before adding the corresponding behavior.
- Keep commits focused and use the plan's commit boundaries.
- Preserve current product scope.
- Preserve the seeded replay and live-provider distinction.
- Do not inject or require a real provider key in CI or smoke tests.
- Do not modify Agent planning, deterministic decision authority, approval semantics, mutation idempotency,
  governance, trace scoring or eval semantics.
- Do not weaken an assertion or remove a test to make CI pass.
- Do not silently regenerate `uv.lock` or `package-lock.json`.
- Do not introduce authentication, worker/queue, OpenTelemetry, deployment, registry publishing,
  multi-agent, RAG or multi-provider routing.
- Do not add real financial mutations.
- Runtime images must be non-root and must not contain `.env`.
- When the plan conflicts with current code, stop the conflicting portion and report:
  - the exact conflicting file and lines;
  - why the plan is stale;
  - the smallest spec/plan update needed.
- Local private helper names and internal file organization may be adjusted only when public interfaces,
  acceptance criteria and verification commands remain unchanged.

## Verification requirements

Before declaring completion, run:

```bash
make lint
make test
make test-db
make container-build
make container-smoke
git diff --check
git status --short
```

Also push the branch so the GitHub Actions workflow runs. Report the actual result of:

```text
backend-quality
frontend-quality
database-integration
container-smoke
```

## Required final response

Return:

1. Summary of implemented behavior.
2. Files created.
3. Files modified.
4. Exact base image tags.
5. Exact GitHub Action versions.
6. New Make targets.
7. Verification commands with exit status and relevant output.
8. GitHub Actions job results.
9. Confirmation that no provider secret was used.
10. Confirmation that runtime containers are non-root.
11. Deviations from the plan.
12. Known remaining limitations.
13. Commit list.

Do not say “complete”, “fixed” or “all tests pass” without the actual command and workflow evidence.
