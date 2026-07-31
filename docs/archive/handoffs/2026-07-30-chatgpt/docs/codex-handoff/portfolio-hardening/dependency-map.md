# MeterDesk Hardening Dependency Map

## 1. Purpose

本文件定义 P0/P1 workstream 的依赖和实施门槛。它解决两个问题：

1. 哪些工作可以独立进行；
2. 哪些设计必须先确定，否则后续实现会返工。

## 2. Dependency Graph

```text
P0-01 CI and Runtime Baseline
    ├── P0-02 Authentication and Approval RBAC
    ├── P1-04 Persistence Foundation
    │       └── P0-03 Workflow State Consistency
    │               └── P0-04 Async Agent Runtime
    │                       ├── P1-01 Provider Resilience
    │                       └── P0-05 Observability and Cost
    │
    └── reusable container and CI verification surface

P0-03 Workflow State Consistency
    └── P0-06 External Read Integration and Typed Tool Runtime
            └── P1-03 Context and Evidence Model

P0-02 Authentication and Approval RBAC
    ├── P0-04 Async Agent Runtime
    ├── P0-05 Observability and Cost
    └── P0-06 External Read Integration

All completed foundations
    └── P1-02 Eval, Security and Draft Safety Expansion
```

## 3. Recommended Sequence

| Order | Workstream | Why now |
|---:|---|---|
| 1 | P0-01 CI and Runtime Baseline | 为所有后续重构建立 build/test/container safety net |
| 2 | P0-02 Authentication and Approval RBAC | 修复当前 financial governance 最明显的 trust gap |
| 3 | P1-04 Persistence Foundation | 在引入更多状态和并发前修正 engine lifecycle，并建立真实 DB 并发测试入口 |
| 4 | P0-03 Workflow State Consistency | 先决定 completed/waiting_approval/terminal semantics |
| 5 | P0-04 Async Agent Runtime | 在稳定状态机上增加 queue、worker、checkpoint、cancel 和 SSE |
| 6 | P1-01 Provider Resilience | 将 timeout/retry/deadline/cancel 对齐到新 runtime |
| 7 | P0-05 Observability and Cost | 在最终 runtime 边界上埋点，避免重复实现 |
| 8 | P0-06 External Read Integration and Typed Tool Runtime | 基础 runtime、identity 和 telemetry 稳定后再引入真实外部故障面 |
| 9 | P1-03 Context and Evidence Model | 基于 typed tool output 建立 ContextBundle 和 EvidenceRef |
| 10 | P1-02 Eval, Security and Draft Safety Expansion | 对前述新 failure modes 建立最终 regression evidence |

## 4. Required Gates

### Gate A — Reproducible Verification

由 P0-01 提供。

必须满足：

- pull request 自动运行 backend lint/test；
- pull request 自动运行 frontend lint/typecheck/test/build；
- Postgres integration check 自动运行；
- API/Web images 自动构建；
- seeded full-stack smoke test 自动运行；
- CI 不需要真实 LLM key。

未满足 Gate A，不开始大规模状态或权限重构。

### Gate B — Trusted Actor

由 P0-02 提供。

必须满足：

- request body 不再决定 approval actor；
- authentication principal 来自 server-side verification；
- approval endpoint 有 role enforcement；
- persisted audit actor 可追溯；
- 401/403/security tests 存在。

未满足 Gate B，不把 approval event 接入异步 runtime 或 telemetry。

### Gate C — Persistence Foundation

由 P1-04 提供。

必须满足：

- app-level AsyncEngine 生命周期；
- async readiness；
- real Postgres test harness 可复用；
- transaction 与 concurrency tests 可以稳定执行。

未满足 Gate C，不引入 background workers 写同一组 workflow tables。

### Gate D — Explicit Workflow Semantics

由 P0-03 提供。

必须满足：

- AgentRun 和 case workflow 的职责被明确；
- 所有状态值、terminal states 和 transition invariant 被定义；
- approval write failure 不会产生误导性的 completed state；
- retry/replay 的幂等边界明确；
- migration 和兼容策略明确。

未满足 Gate D，不允许“把同步 orchestrator 放进 worker”作为 async implementation。

### Gate E — Recoverable Runtime

由 P0-04 提供。

必须满足：

- start endpoint 返回 `202 Accepted` 和 run/workflow ID；
- queue/worker 与 HTTP lifecycle 分离；
- progress event 可读取；
- cancellation 有明确结果；
- checkpoint/recovery 有 automated evidence；
- duplicate enqueue/retry 不产生 duplicate financial action。

### Gate F — Operational Evidence

由 P1-01 和 P0-05 提供。

必须满足：

- timeout/retry/deadline/cancel 可区分；
- provider/tool latency 可观测；
- token/cost 可记录；
- queue delay 和 approval wait 可测量；
- logs/traces/metrics 可通过 correlation ID 关联。

### Gate G — External Boundary

由 P0-06 提供。

必须满足：

- 仅增加一个 read-only integration；
- adapter 有 typed contract；
- timeout、retry、schema error 和 rate limit 有测试；
- external write 不进入 v1；
- trace propagation 和 error sanitization 生效。

## 5. Parallelization Rules

允许在 P0-01 完成后并行准备、但不建议同时合并：

```text
P0-02 Authentication spec
P1-04 Persistence spec
```

不允许并行实现：

```text
P0-03 Workflow State Consistency
P0-04 Async Agent Runtime
```

原因：Runtime 的 queue payload、event schema、checkpoint 和 resume 都依赖最终状态模型。

不允许同时实现：

```text
P0-04 Async Runtime
P0-06 External Integration
```

原因：两者都会改变 failure surface，难以确定 regression 来源。

不允许把 P1-02 当成最后一次性“补测试”。每个 workstream 自己仍必须添加测试；P1-02 负责扩充
跨系统 adversarial/failure/concurrency suite。

## 6. Re-review Points

以下节点合并后，必须重新读取代码并刷新后续计划：

### After P0-01

重新确认：

- Make targets
- Compose service names
- CI commands
- Docker runtime paths

### After P0-02

重新确认：

- approval request schema
- route dependencies
- frontend action boundary
- persisted actor fields

### After P1-04

重新确认：

- engine/session lifecycle
- repository transaction boundaries
- test fixtures
- DB concurrency helpers

### After P0-03

重新确认：

- run/workflow models
- API response status
- approval linkage
- migration history
- state transitions

### After P0-04

重新确认：

- worker framework
- event/checkpoint model
- retry and cancellation interface
- deployment topology

### After P0-06

重新确认：

- ToolSpec
- adapter outputs
- structured evidence
- context construction inputs

## 7. Plan Freshness Rule

Detailed Implementation Plan 只对以下代码基线有效：

```text
Feature Spec 审阅时的 main
+ 已明确列出的 prerequisite commits
```

如果 plan 中任意一个条件发生变化，Codex 在开始前应要求刷新计划：

- 文件被移动或拆分；
- public schema 已变更；
- repository method signature 已变更；
- migration head 已变化；
- service name 已变化；
- state values 已变化；
- test command 已变化；
- prerequisite PR 尚未合并。

## 8. PR Boundary

默认规则：

```text
1 Feature Spec
    -> 1 Implementation Plan
        -> 1 isolated worktree
            -> 1 reviewable PR
```

一个 workstream 可以拆成多个 PR，但每个 PR 必须产生独立、可测试的行为。不得创建只有
scaffolding、没有使用者和没有验证的长期悬空 abstraction。
