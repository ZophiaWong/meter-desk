# MeterDesk P0/P1 Workstreams Overview

## 1. P0-01 — CI and Runtime Baseline

### Problem

当前本地已有 `make test`、`make test-db`、`make lint` 和 seeded demo 命令，但未发现
GitHub Actions、API/Web Dockerfile，且 Compose 只编排 Postgres。Reviewer 无法快速确认
fresh checkout 是否能在标准环境中重复构建和启动。

### Goal

建立无真实 LLM key 依赖的自动化 CI、API/Web production images、完整 seeded Compose
runtime 和 smoke verification。

### In scope

- backend lint/test CI
- frontend lint/typecheck/test/build CI
- Postgres migration/seed/integration CI
- API Dockerfile
- Web Dockerfile
- full-stack Compose
- container smoke script
- Make targets
- runbook and README updates

### Non-goals

- cloud deployment
- image registry publishing
- Kubernetes
- worker
- authentication
- OpenTelemetry
- live provider execution in CI

### Completion evidence

- PR checks
- `make container-smoke`
- clean seeded startup
- API/DB health
- rendered homepage
- no provider secret required

---

## 2. P0-02 — Authentication and Approval RBAC

### Problem

Approval actor 由 request body 的 `decided_by` 提供；frontend 提交硬编码 actor。系统无法证明
谁批准了 financial action，也没有 role enforcement。

### Goal

由 server-side authenticated principal 确定 actor，并限制 `approver`/`admin` 执行
approve/reject。

### In scope

- authenticated principal abstraction
- token verification suitable for local/demo environment
- roles: `support_operator`, `approver`, `admin`
- 401/403 semantics
- removal of client-owned actor identity
- actor subject/role/request ID audit
- frontend authenticated request propagation
- seed/demo identities
- security tests

### Non-goals

- enterprise identity administration UI
- SCIM
- social login
- multi-tenant billing model
- real payment authorization

### Dependencies

- P0-01

### Completion evidence

- forged actor is rejected or ignored
- operator receives 403
- approver/admin succeeds
- persisted actor equals authenticated subject
- existing mutation idempotency remains valid

---

## 3. P1-04 — Persistence Foundation

### Problem

AsyncEngine 当前在 request scope 创建和销毁；readiness 使用同步 probe。后续 workflow/worker
会增加并发写入，需要稳定的 application-level session lifecycle 和真实 Postgres concurrency
test harness。

### Goal

建立 FastAPI lifespan-managed engine/sessionmaker、async readiness 和可复用的 DB concurrency
tests。

### In scope

- app lifespan
- app-level AsyncEngine
- app-level async sessionmaker
- async readiness query
- connection pool configuration
- test overrides
- real Postgres concurrency harness
- approve/approve 和 approve/reject baseline tests

### Non-goals

- 大规模 repository rewrite
- sharding
- read replicas
- distributed transaction
- queue/worker

### Dependencies

- P0-01

### Completion evidence

- engine 在 app shutdown 时统一 dispose
- request 不再创建 engine
- readiness 不调用同步 socket/psycopg probe
- concurrency tests 在真实 Postgres 上运行

---

## 4. P0-03 — Workflow State Consistency

### Problem

AgentRun 当前可能先进入 completed，再尝试创建 approval。系统没有清楚区分“调查完成”和“业务
workflow 完成”，也没有定义 approval write failure 的最终状态。

### Goal

建立明确的 workflow aggregate、state transitions、terminal semantics 和 persistence
boundary。

### Required design decision

必须在实现前选择并记录以下模型之一：

1. `AgentRun` 只表示一次调查，新增 `CaseWorkflow` 管理 approval/mutation lifecycle；或
2. `AgentRun` 扩展为完整 workflow state machine。

推荐优先评估模型 1，因为当前 architecture glossary 已把 AgentRun 定义为一次 investigation
attempt。

### In scope

- state diagram
- state enum
- transition invariants
- approval linkage
- partial-failure semantics
- transaction/outbox decision
- migration
- API and UI state mapping
- transition tests

### Non-goals

- queue
- worker
- SSE
- provider retry redesign

### Dependencies

- P1-04
- P0-02 actor model should be stable before final approval event schema

### Completion evidence

- completed/waiting_approval 含义无歧义
- approval creation failure 可测试
- invalid transitions 被拒绝
- seeded data migrated
- existing decision and governance behavior preserved

---

## 5. P0-04 — Async Agent Runtime

### Problem

Agent execution 和 eval execution 当前发生在 HTTP request 内。长 provider call 会占用 request，
无法 checkpoint、cancel、resume 或 crash recover。

### Goal

把 execution 从 request lifecycle 中分离，建立可恢复的 queued workflow runtime。

### In scope

- `202 Accepted`
- queue and worker
- queued/running/waiting states
- event stream or SSE
- checkpoint
- heartbeat/lease or equivalent stale-job detection
- cancellation
- retry/replay
- idempotent enqueue
- worker integration tests
- container topology update

### Non-goals

- arbitrary workflow builder
- multi-agent scheduler
- Kubernetes
- distributed multi-region runtime
- real financial mutation

### Dependencies

- P0-03
- P1-04
- P0-02

### Completion evidence

- start endpoint returns quickly
- worker performs execution
- progress is observable
- cancellation is terminal and safe
- crash recovery test passes
- duplicate delivery does not duplicate approval or mutation

---

## 6. P1-01 — Provider Resilience

### Problem

Provider 使用固定 timeout 和有限 retry，缺少 error taxonomy、deadline、backoff、jitter、
cancellation 和 usage metadata。

### Goal

建立与 async runtime 对齐的 provider client contract。

### In scope

- async HTTP client
- connect/read/write/total timeouts
- retryable vs non-retryable error mapping
- 429/5xx backoff with jitter
- overall deadline
- cancellation propagation
- provider request ID
- sanitized error body
- structured usage metadata
- tests with fake provider server

### Non-goals

- multi-provider routing
- automatic provider fallback
- model leaderboard
- prompt redesign

### Dependencies

- P0-04

### Completion evidence

- timeout classes可区分
- 4xx schema/input error不盲目 retry
- 429/5xx按 policy retry
- deadline/cancel终止调用
- request/usage metadata被保存

---

## 7. P0-05 — Observability and Cost

### Problem

现有 trace 是业务审计 trace，不是完整的 operational telemetry。当前无法系统回答 latency、
retry、Token、cost、queue delay 和 approval wait。

### Goal

建立 domain IDs 与 OpenTelemetry/metrics/logs 的关联。

### In scope

- request ID / trace ID / run ID correlation
- spans for API, worker, planning, tools, provider, approval
- structured logs
- provider/tool latency
- queue delay
- retries
- input/output tokens
- estimated cost
- approval wait duration
- metrics endpoint or collector
- local observability runbook
- dashboard evidence

### Non-goals

- full production SRE platform
- 24/7 alerting
- multi-region SLO
- arbitrary trace replay UI

### Dependencies

- P0-04
- P1-01
- P0-02

### Completion evidence

- one run can be followed across API/worker/provider
- token/cost persisted or emitted
- metrics have stable names
- sensitive prompt/evidence content is not logged by default
- dashboard or trace screenshot exists

---

## 8. P0-06 — External Read Integration and Typed Tool Runtime

### Problem

所有外部系统仍为 in-process/mock data，无法证明 external API auth、timeout、rate limit、
schema drift 和 contract test 能力。

### Goal

增加一个 read-only external adapter，并把 tool execution 收敛为 typed contract。

### Recommended scope

优先选择其一：

- Stripe test-mode read adapter；或
- 独立 billing HTTP service（仓库内可启动）；或
- ticket service read adapter。

如果 public demo 和 secret 管理成本较高，优先独立 billing HTTP service。它仍能证明 network
boundary，而不依赖第三方账号。

### In scope

- `ToolSpec`
- `ToolRegistry`
- `ToolExecutor`
- typed inputs/outputs
- risk metadata
- timeout/retry policy
- adapter auth
- contract tests
- error mapping
- trace propagation
- one read-only integration

### Non-goals

- payment write
- customer message send
- planner-driven approval/mutation
- generic plugin marketplace
- broad MCP server

### Dependencies

- P0-03
- P0-04
- P0-05
- P0-02

### Completion evidence

- adapter timeout/rate-limit/schema failure tests
- trace links external request to run
- planner can only invoke allowed read action
- external write remains impossible

---

## 9. P1-03 — Context and Evidence Model

### Problem

当前 provider context 由 orchestrator 直接组装，evidence refs 使用字符串前缀。系统难以说明
context selection、exclusion、redaction、version 和 token budget。

### Goal

把执行 context 变成可审计、版本化的一等对象。

### In scope

- typed `EvidenceRef`
- evidence source/version/digest
- `ContextBundle`
- selected and excluded evidence
- selection reasons
- redactions
- trust classification
- token estimate/budget
- context hash
- persisted context snapshot
- eval compatibility

### Non-goals

- conversational long-term memory
- vector memory
- generic context management platform
- large-scale RAG

### Dependencies

- P0-06 typed tool output
- P0-05 telemetry

### Completion evidence

- context can be reconstructed
- PII redaction is tested
- stale policy/evidence version is detectable
- eval no longer依赖 string prefix 猜 evidence type

---

## 10. P1-02 — Eval, Security and Draft Safety Expansion

### Problem

现有 deterministic eval 设计较强，但 case 数量、security、failure、bilingual、indirect promise
和 concurrency evidence 仍不足。

### Goal

建立覆盖新增 production failure modes 的 regression suite。

### In scope

- 30+ focused cases, not a large benchmark
- prompt injection
- policy spoofing
- PII leakage
- malformed provider output
- provider/tool timeout
- retry exhaustion
- concurrent approval
- duplicate delivery
- worker crash/recovery
- Chinese and English drafts
- indirect financial promises
- latency/cost threshold checks
- CI critical subset + optional broader suite

### Non-goals

- public benchmark
- multi-provider leaderboard
- full trace replay
- large judge-heavy dataset

### Dependencies

- all previous workstreams whose behavior is evaluated

### Completion evidence

- critical failures block CI
- provider/environment outage is not mislabeled as model regression
- security failures have stable reason codes
- concurrency and recovery cases produce deterministic results
- draft safety logic is centralized rather than duplicated
