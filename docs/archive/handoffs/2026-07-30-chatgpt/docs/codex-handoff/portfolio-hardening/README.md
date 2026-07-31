# MeterDesk Portfolio Hardening

## 1. Objective

本项目将 MeterDesk 从一个完成度较高的 governed agent portfolio product，推进为具备
明确 production evidence 的 AI Agent application。

本轮 hardening 重点证明：

- 代码可以通过自动化 CI 被重复构建和验证；
- 完整应用可以通过容器化方式启动，而不是只依赖开发机命令；
- 高风险 approval actor 来自可信身份，而不是客户端自报；
- Agent workflow 具有明确、一致、可恢复的状态语义；
- 长时间运行的 Agent execution 不阻塞 HTTP request；
- provider、tool、database 和 worker failure 有明确处理方式；
- 系统能够观测 latency、retry、Token、cost 和 approval wait time；
- critical governance behavior 可以通过 deterministic、security、failure 和 concurrency
  tests 验证。

## 2. Target Roles

本轮改造主要服务以下求职方向：

- AI Agent Application Engineer
- LLM Backend Engineer
- AI Full-stack Engineer
- Enterprise AI Engineer
- Agent Workflow Engineer

它不会将 MeterDesk 改造成：

- general-purpose autonomous agent platform
- multi-agent framework
- large-scale RAG system
- model training / post-training project
- real payment processor
- enterprise multi-tenant SaaS platform

## 3. Product Positioning

MeterDesk 的准确定位是：

> A bounded, governed billing-support agent workflow in which the LLM may plan
> within an allowlist and draft language, while the backend remains authoritative
> for evidence access, business decisions, approval gates, and financial mutations.

必须保留以下边界：

1. Duplicate Charge 是 v1 golden path。
2. Credit/Refund Dispute 是 supporting governed workflow。
3. Usage Spike 可以继续作为显式 coverage gap，直到其 runner 被单独批准实现。
4. LLM 不拥有 refund/credit eligibility 或 amount 的最终决定权。
5. Financial mutation 必须经过 human approval。
6. Customer reply 保持 draft-only。
7. 所有 financial mutation 继续为 mock-only。
8. 不为了职位关键词引入 multi-agent、large-scale RAG 或 multi-provider gateway。
9. Seeded replay 与 live provider execution 必须明确区分。
10. 现有 trace、approval、action fingerprint、mutation idempotency 和 deterministic eval
    不能因 hardening 被弱化。

## 4. Package Contents

| 文件 | 作用 |
|---|---|
| `current-state.md` | 记录本轮审阅时仓库的事实状态，不混入解决方案 |
| `dependency-map.md` | 定义 P0/P1 workstream 的依赖、实施顺序和重审节点 |
| `workstreams-overview.md` | 定义全部 P0/P1 的目标、范围、non-goals 和完成证据 |
| `evidence-matrix.md` | 把求职能力声明映射到代码、测试和运行证据 |
| `specs/P0-01-ci-runtime-baseline.md` | 第一项 workstream 的需求真源 |
| `../../superpowers/plans/2026-07-30-meterdesk-ci-runtime-baseline.md` | Codex 执行计划 |
| `codex-execution-prompt.md` | 可直接交给 Codex 的执行提示词 |

## 5. Required Reading Order for Codex

Codex 在实现任何 workstream 前必须按顺序读取：

1. `AGENTS.md`
2. `README.md`
3. `docs/specs/product-scope.md`
4. `docs/specs/system-architecture.md`
5. `docs/specs/agent-governance.md`
6. `docs/specs/eval-strategy.md`
7. `docs/specs/implementation-roadmap.md`
8. 本目录的 `README.md`
9. 本目录的 `current-state.md`
10. 当前 workstream 的 Feature Spec
11. 当前 workstream 的 Implementation Plan

如果 Feature Spec 与旧 roadmap 存在明确冲突，Codex 不得自行选择一方。它应停止冲突部分，
列出冲突和建议，由维护者决定是否先更新上层 spec。

## 6. Planning Model

采用三层规划：

### Layer 1 — Master Roadmap

一次性稳定描述：

- workstream 列表
- 依赖关系
- 全局约束
- 目标岗位
- completion evidence
- 明确不做的内容

对应文件：

- `dependency-map.md`
- `workstreams-overview.md`
- `evidence-matrix.md`

### Layer 2 — Feature Design Spec

某个 workstream 即将实现时，重新读取当前代码后生成。它固定：

- current behavior
- problem
- target architecture
- domain/state model
- public and cross-layer interfaces
- invariants
- failure semantics
- migration/compatibility
- test requirements
- acceptance criteria

Feature Spec 是该子系统的需求真源。

### Layer 3 — Codex Implementation Plan

根据已经确认的 Feature Spec 生成，固定：

- files in scope
- task boundaries
- cross-task interfaces
- test-first sequence
- verification commands
- commit boundaries
- completion evidence

Implementation Plan 不应提前规定无跨模块影响的 private helper、局部变量和纯内部组织方式。
Codex 可以在不改变 Spec、公开接口、invariant 和 acceptance criteria 的前提下调整这些细节。

## 7. Iterative Handoff Protocol

每个 workstream 使用以下循环：

```text
ChatGPT reads current main
    -> writes or refreshes one Feature Spec
        -> maintainer approves design decisions
            -> ChatGPT writes one Implementation Plan
                -> Codex implements in isolated worktree
                    -> Codex runs verification and opens PR
                        -> ChatGPT reviews diff and evidence
                            -> current-state/evidence-matrix are updated
                                -> next workstream is planned from new main
```

不要一次性让 Codex 实现全部 P0/P1。以下组合尤其禁止在同一个 PR 中出现：

```text
Authentication
+ workflow state redesign
+ async worker
+ OpenTelemetry
+ external integration
+ eval expansion
```

## 8. Global Constraints

所有 workstream 自动继承：

- Python 版本保持 `>=3.12`，除非单独 spec 批准升级。
- Frontend 继续使用 Next.js/React/TypeScript。
- Backend 继续使用 FastAPI/SQLAlchemy/Postgres。
- 保留一个 OpenAI-compatible provider boundary；不构建 multi-provider gateway。
- 不引入真实 payment mutation。
- 不自动发送 customer reply。
- 不允许 frontend 直接执行 backend tools。
- 不允许 planner 直接计划 approval、mutation、customer send 或 external write。
- 不以删除测试、降低 assertion、绕过 governance 或改写 seeded expectations 的方式通过 CI。
- 新增行为必须具有 automated tests。
- Database schema 变化必须使用 Alembic migration。
- 新增 runtime state 必须定义 terminal states、retry semantics 和 idempotency behavior。
- 新增 external dependency 必须定义 timeout、retry、error mapping 和 trace propagation。
- 每个 PR 必须包含实际 verification output 摘要。
- 实现必须聚焦当前 workstream，不顺带重构无关文件。

## 9. Definition of Done for Any Workstream

一项 workstream 只有同时满足以下条件才算完成：

1. Feature Spec 的 acceptance criteria 全部有对应实现。
2. 每个 critical invariant 有 automated evidence。
3. 所有计划中的 verification command 已实际运行。
4. Codex 返回命令和真实结果，而不是只写“tests pass”。
5. 相关 migration、environment、runbook 和 README 已更新。
6. Seeded replay 仍可运行。
7. Live provider boundary 没有被替换成伪 live execution。
8. 没有扩大产品范围。
9. `evidence-matrix.md` 已更新状态和证据位置。
10. Remaining limitations 被明确记录。

## 10. First Detailed Workstream

当前第一份详细实施材料是：

> **P0-01 CI and Runtime Baseline**

选择它的原因：

- 当前已有本地 `make test`、`make test-db` 和 `make lint`，适合转化为 CI contract；
- 当前 `compose.yaml` 只包含 Postgres；
- 当前未发现 API/Web Dockerfile；
- 当前未发现 `.github/workflows`；
- 后续 authentication、state、worker、observability 和 integration 改造都需要可靠的自动化安全网。

P0-01 不改变 Agent 行为、approval 语义或 domain model。它只建立可重复构建、测试、容器启动和
smoke verification 的基础。
