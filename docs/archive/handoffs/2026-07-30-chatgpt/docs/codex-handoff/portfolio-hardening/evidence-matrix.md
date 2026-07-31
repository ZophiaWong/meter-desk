# MeterDesk Engineering Evidence Matrix

## 1. Purpose

本文件用于把“项目能力声明”映射为可验证证据。它不是 backlog，也不是宣传文案。

每个关键能力至少需要一种 automated evidence。高风险能力还需要 runtime evidence。

状态定义：

- **Existing**：当前仓库已有静态代码证据；仍可能未经过本轮运行验证。
- **Gap**：当前未找到足够证据。
- **Planned**：已有明确 workstream。
- **Verified**：实现后已运行指定验证命令并保存结果。
- **Deferred**：明确不在当前范围。

## 2. Baseline Evidence

| Capability | Current code evidence | Automated evidence | Runtime evidence | Status |
|---|---|---|---|---|
| Ticket-first governed product | README、Workbench、resource APIs | frontend route tests | seeded demo screenshots | Existing |
| Backend deterministic outcome authority | decision tools + orchestrator | decision/orchestrator tests | trace and decision overview | Existing |
| Bounded LLM planning | plan contracts + verifier | plan verifier tests | planning trace | Existing |
| Approval gate | GovernanceKernel + approval service | approval/mutation tests | Approval Queue | Existing |
| Financial action idempotency | action fingerprint + DB constraints | existing API/repository tests | mutation audit | Existing |
| Trace-aware eval | EvalRunner + compliance + snapshots | eval tests | Eval Lab | Existing |
| Usage Spike honesty | blocked coverage gap | eval blocked-case tests | Eval Lab coverage gap | Existing |

“Existing” 只表示代码存在，不表示本轮已经执行通过。

## 3. P0/P1 Target Evidence

| Requirement | Current state | Target implementation | Required automated evidence | Required runtime evidence | Workstream | Status |
|---|---|---|---|---|---|---|
| PR 自动运行 backend quality checks | 未发现 workflow | GitHub Actions backend job | Ruff + pytest job result | CI summary | P0-01 | Gap |
| PR 自动运行 frontend quality checks | 未发现 workflow | GitHub Actions frontend job | lint + typecheck + Vitest + build | CI summary | P0-01 | Gap |
| Postgres integration 自动验证 | 仅本地 `make test-db` | CI DB integration job | migration + seed + checker | job logs | P0-01 | Planned |
| API image 可重复构建 | 未发现 Dockerfile | pinned multi-stage image | `docker build` | image metadata | P0-01 | Gap |
| Web image 可重复构建 | 未发现 Dockerfile | Next production image | `docker build` | image metadata | P0-01 | Gap |
| Seeded full-stack 可启动 | Compose 只有 Postgres | postgres + migrate + seed + api + web | container smoke script | `/health`, `/health/db`, `/` | P0-01 | Gap |
| CI 不依赖真实 provider key | 本地 checker 支持 missing provider | CI 明确不注入 key | smoke/eval non-live assertions | CI environment summary | P0-01 | Planned |
| Client 不能伪造 approver | `decided_by` 来自 body | server-derived principal | forged actor test | approval audit | P0-02 | Gap |
| Operator 不能 approve/reject | 无 role dependency | RBAC guard | 403 tests | API example | P0-02 | Gap |
| Approval actor 可审计 | string actor，无可信来源 | actor subject + role + request ID | persistence test | approval record | P0-02 | Gap |
| DB engine 为 app lifecycle | request scope create/dispose | lifespan engine/sessionmaker | lifecycle tests | pool metrics later | P1-04 | Gap |
| DB readiness 不阻塞 event loop | sync probe in async endpoint | async connection probe | health tests | readiness result | P1-04 | Gap |
| 并发 approve 最多一个 mutation | 有 constraint，真实并发证据不足 | transaction/locking contract | Postgres concurrent test | DB audit rows | P1-04 | Planned |
| Workflow completed 语义明确 | 调查完成后先写 completed，再建 approval | explicit aggregate/state machine | transition tests | workflow timeline | P0-03 | Gap |
| Approval write failure 不留下误导状态 | 当前有部分状态风险 | atomic/compensated transition | injected failure test | persisted state | P0-03 | Gap |
| Start run 不阻塞 HTTP | 同步 request | `202` + queued execution | API/worker tests | response latency | P0-04 | Gap |
| Worker crash 可恢复 | 无 worker/checkpoint | checkpoint + recovery | crash/restart test | event history | P0-04 | Gap |
| Run 可取消 | 无 cancellation | cancel endpoint/token | cancel transition tests | UI/runtime state | P0-04 | Gap |
| Provider timeout 可分类 | 固定 30s error | timeout taxonomy | timeout tests | failure metric | P1-01 | Gap |
| 429/5xx 有受控 retry | 固定有限 retry | backoff + jitter + deadline | retry classification tests | retry metrics | P1-01 | Gap |
| Cancellation 传播到 provider | 无 | async client + cancel scope | cancellation test | cancelled span | P1-01 | Gap |
| Provider usage 被记录 | 未解析 usage | token/cost record | response mapping tests | run cost | P0-05 | Gap |
| Run latency 可测量 | domain trace，无 OTel | spans + metrics | instrumentation tests | dashboard/trace | P0-05 | Gap |
| Queue delay 可测量 | 无 queue | queued/started timestamps | metric tests | dashboard | P0-05 | Gap |
| Approval wait 可测量 | 有 timestamps，未形成 metric | derived duration metric | calculation tests | dashboard | P0-05 | Planned |
| 真实 read integration | external systems mock-only | one read-only adapter | contract/failure tests | trace sample | P0-06 | Gap |
| Tool contract typed | coarse internal calls | ToolSpec/ToolExecutor | registry/executor tests | tool trace | P0-06 | Planned |
| Evidence ref 结构化 | string prefix convention | typed EvidenceRef | serialization/eval tests | trace payload | P1-03 | Gap |
| Context selection 可审计 | provider input 直接组装 | ContextBundle | builder/redaction tests | context snapshot | P1-03 | Gap |
| Prompt injection 有系统化测试 | allowlist 有局部防护 | adversarial suite | injection cases | eval result | P1-02 | Gap |
| 中英文 draft safety | 英文短语检测为主 | centralized claim/safety policy | bilingual cases | Eval Lab | P1-02 | Gap |
| Indirect promise 可检测 | 覆盖有限 | structured claim + judge supplement | paraphrase cases | eval notes | P1-02 | Gap |
| Failure/concurrency eval | 局部 unit tests | cross-system regression suite | failure/concurrency cases | regression summary | P1-02 | Gap |
| Hosted public live mutation | 不应实现 | 保持 mock-only | governance regression | mock label | Global constraint | Deferred |
| Multi-agent | 无业务必要性 | 不实现 | scope guard | N/A | Global constraint | Deferred |
| Multi-provider gateway | 明确 out of scope | 不实现 | scope guard | N/A | Global constraint | Deferred |

## 4. Evidence Update Protocol

每个 PR 合并前更新对应行：

1. 把 `Target implementation` 改为实际 file/interface。
2. 填入准确 test name。
3. 填入实际 verification command。
4. 如果有 runtime artifact，记录路径或截图。
5. 只有在命令实际运行且结果可复核时，才能标记 `Verified`。
6. 若 acceptance criterion 未完成，保持 `Planned` 或 `Gap`，不要使用模糊的 “mostly done”。

## 5. Resume and Interview Use

只有 `Verified` 行可以直接转成简历量化声明。

示例：

```text
Implemented GitHub Actions gates covering backend lint/tests, frontend
lint/typecheck/tests/build, Postgres migration/seed checks, and full-stack
container smoke verification.
```

以下声明需要额外数字证据后再使用：

```text
production-ready
high availability
low latency
scalable
cost optimized
secure multi-tenant
```
