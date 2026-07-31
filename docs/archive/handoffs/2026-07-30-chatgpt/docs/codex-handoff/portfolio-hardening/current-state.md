# MeterDesk Current State

审阅日期：2026-07-30<br>
仓库：`ZophiaWong/meter-desk`<br>
分支：`main`<br>
审阅方式：GitHub 静态代码与文档审阅

## 1. Review Limitations

本文件记录代码中可直接确认的事实。审阅期间没有：

- checkout 仓库到本地运行；
- 执行 `make test`、`make test-db` 或 `make lint`；
- 构建 Docker image；
- 启动完整应用；
- 调用真实 LLM provider；
- 验证任何 hosted deployment。

因此：

- “存在测试代码”不等于“当前所有测试均通过”；
- “存在运行命令”不等于“fresh checkout 已验证”；
- “设计支持幂等”不等于“所有真实并发场景已压测”。

## 2. Product and Architecture

当前产品仍是 ticket-first 的 billing support workbench：

- Next.js 负责 UI 和 API consumption；
- FastAPI 负责 workflow、tool execution、approval 和 eval；
- Postgres 保存 domain data、agent runs、traces、approvals、mock mutations 和 eval history；
- LLM provider 只通过 OpenAI-compatible boundary 接入；
- external billing/payment/support systems 仍为 mock-only；
- customer reply 保持 draft-only。

主要来源：

- `README.md`
- `AGENTS.md`
- `docs/specs/system-architecture.md`
- `docs/specs/agent-governance.md`
- `docs/specs/eval-strategy.md`

## 3. Repository Operating Rules

`AGENTS.md` 明确要求：

- 保留 Duplicate Charge golden path；
- 不改成 generic chatbot 或 generic RAG；
- 不添加 real payment mutation；
- 不自动发送 customer reply；
- 不绕过 approval gate；
- 不引入 multi-provider gateway 和 enterprise multi-tenancy；
- 行为变化必须更新测试；
- 改变产品边界、架构、governance 或 eval 时必须更新相关 spec。

这些约束应被所有后续 hardening plan 继承。

## 4. Local Development and Build Surface

### Existing commands

根目录 `Makefile` 当前提供：

```text
make install
make db-up
make dev
make dev-api
make dev-web
make test
make test-db
make lint
make seed
make demo-reset-live
make health
make db-down
```

其中：

- `make test` 运行 backend pytest 和 frontend Vitest；
- `make test-db` 启动 Postgres、运行 migration、seed 和 DB integration check；
- `make lint` 运行 Ruff、format check、ESLint 和 TypeScript typecheck；
- `make dev` 在宿主机同时启动 FastAPI 和 Next.js；
- `make seed` 重建 portfolio demo baseline。

### Current Compose topology

`compose.yaml` 目前只定义：

```text
postgres
```

没有定义：

- API container
- Web container
- migration job
- seed job
- worker
- telemetry service

### Container files

审阅时没有找到：

- `apps/api/Dockerfile`
- `apps/web/Dockerfile`

### GitHub Actions

审阅时 GitHub contents API 没有找到 `.github/workflows` 目录。当前仓库因此没有可确认的：

- pull-request CI
- protected required checks
- container build verification
- automated Postgres integration job
- deployment workflow

## 5. Backend Dependency and Test Surface

`apps/api/pyproject.toml` 当前定义：

- Python `>=3.12`
- FastAPI
- SQLAlchemy async
- psycopg
- Alembic
- pydantic-settings
- Uvicorn
- pytest / pytest-asyncio
- Ruff

Backend 已有较广泛测试文件，包括：

- governed agent loop
- deterministic decisions
- governance kernel
- plan verifier
- approval and mutation safety
- eval lab
- run compliance
- DB integration
- demo readiness

本审阅没有执行这些测试。

## 6. Frontend Dependency and Test Surface

`apps/web/package.json` 当前定义：

- Next.js 15
- React 19
- TypeScript
- Vitest
- Testing Library
- ESLint
- Tailwind CSS

现有 scripts：

```text
npm run dev
npm run build
npm run start
npm run lint
npm test
npm run typecheck
```

主页是 async Server Component，并在 server side 调用 FastAPI health 和 workbench APIs。
`API_BASE_URL` 默认是 `http://localhost:8000`。这意味着容器化时 Web container 应使用内部
service URL，例如 `http://api:8000`，而不是容器自身的 localhost。

## 7. Agent Execution

当前 `POST /tickets/{ticket_id}/agent-runs` 在 FastAPI request 中同步等待：

1. ticket read
2. LLM investigation plan
3. backend plan verification
4. evidence reads
5. deterministic decision
6. LLM draft generation
7. trace writes
8. approval request creation

当前没有：

- queue
- background worker
- queued state
- heartbeat
- lease
- checkpoint
- resume
- cancellation
- backpressure
- SSE progress stream
- runtime deadline propagated across steps

## 8. Planning and Decision Authority

当前 planner 是 bounded planner：

- 只能使用 scenario contract 中允许的 action IDs；
- approval、draft 和 mutation action 被禁止进入 plan；
- backend verifier 检查 scenario、required actions、targets、dependencies 和 order；
- verifier 可以把 feedback 返回给 provider 并重试一次；
- 连续无效计划会使 run 失败。

Deterministic decision tool 负责：

- final outcome
- refund/credit eligibility
- financial amount
- action type
- evidence/policy references

LLM provider 只负责：

- structured investigation plan
- recommendation language
- internal resolution draft
- customer reply draft

## 9. Workflow State Consistency

当前 `AgentRun` 主要状态包括：

```text
running
completed
failed
```

在 Duplicate Charge 和 Credit/Refund orchestrator 中，当前调用顺序是：

```text
complete_agent_run(...)
record draft trace
create_approval_request(...)
return completed run
```

因此可静态推断出一个一致性风险：

- AgentRun 已写成 `completed`；
- 随后的 approval write 仍可能失败；
- 可能留下 completed run，但缺少应有 approval 的部分状态。

当前代码没有显式定义：

- `completed` 是“Agent 调查结束”还是“case workflow 结束”；
- `waiting_approval` 属于 AgentRun、Ticket 还是另一个 aggregate；
- approval write 失败后的补偿状态；
- workflow version / optimistic locking；
- transactional outbox。

## 10. Authentication and Approval Identity

当前 `ApprovalDecisionRequest` 包含：

```text
decided_by: str = "Demo Operator"
decision_note: str | None
```

Frontend approval actions同样提交硬编码的 `Demo Operator`。

当前 API route 没有可确认的 authentication/authorization dependency。因此：

- client 可以选择 approval actor；
- server 不能证明 actor identity；
- 没有 role enforcement；
- 没有 tenant/account scope enforcement；
- approval gate 在业务上存在，但 actor trust boundary 仍不完整。

## 11. Financial Governance and Idempotency

现有优势：

- tool policy registry 定义 risk、executor、gate 和 evidence requirements；
- high-risk mutation 要求 approved approval reference；
- action fingerprint 表达业务 action identity；
- pending duplicate approval 会被阻断；
- duplicate executed mutation 会被阻断；
- approved action 最多创建一个 mock mutation；
- rejected approval 不创建 mutation；
- mutation 和 approval 会关联到 run、ticket、policy 和 evidence；
- blocked behavior 会写 trace。

当前主要未验证项：

- 真实 Postgres 下 approve/approve 并发；
- approve/reject 并发；
- client timeout 后重试；
- commit 成功但 response 丢失；
- worker crash 后 replay；
- cross-process locking semantics。

## 12. Persistence Lifecycle

当前 `get_session()` 每次调用会：

1. 创建 AsyncEngine；
2. 创建 sessionmaker；
3. yield session；
4. request 结束后 dispose engine。

这意味着连接池不能作为应用级资源稳定复用。

当前 `check_database()` 是 async function，但内部调用同步 socket 和 psycopg probe。

后续 persistence hardening 应考虑：

- FastAPI lifespan 创建/关闭 engine；
- app-level async sessionmaker；
- async readiness probe；
- pool configuration 和 metrics；
- real Postgres concurrency tests。

## 13. Provider Boundary and Resilience

当前 provider：

- 使用 `urllib.request.urlopen`；
- 通过 `asyncio.to_thread` 避免直接阻塞 event loop；
- 固定 30 秒 timeout；
- 支持 structured JSON schema output；
- plan 和 draft validation failure 会映射为 provider error；
- orchestrator 对 plan/draft 有有限 retry。

当前缺少：

- connect/read/write/total timeout taxonomy；
- 429/5xx retry classification；
- exponential backoff 与 jitter；
- execution deadline；
- cancellation propagation；
- circuit breaker；
- provider request ID；
- input/output token usage persistence；
- estimated cost；
- provider latency metrics；
- response body sanitization policy。

## 14. Domain Trace vs Operational Observability

当前 domain trace 可以回答：

- agent 看了什么 evidence；
- 使用了什么 policy；
- planner 提出了什么；
- verifier 接受或阻断了什么；
- backend 做了什么 decision；
- 是否创建 approval；
- mutation 是否被 gate 阻断；
- compliance 是否通过。

当前没有可确认的 operational telemetry：

- OpenTelemetry traces
- request/worker correlation
- queue delay
- provider/tool latency histogram
- retry count
- token usage
- cost
- approval wait duration
- structured application logs
- service-level metrics
- production dashboard

## 15. Eval State

当前 eval strategy 定义 9 个 case：

- 3 Duplicate Charge
- 3 Usage Spike
- 3 Credit/Refund Dispute

当前状态：

- Duplicate Charge 可执行；
- Credit/Refund Dispute 可执行；
- Usage Spike 保持显式 blocked coverage gap；
- critical dimensions 以 deterministic checks 为主；
- LLM-as-judge 只用于 draft quality；
- eval history 保存 baseline/current snapshot、prompt fingerprint、policy/tool version 和 trace
  signature。

主要缺口：

- case 数量仍小；
- failure injection 覆盖有限；
- prompt injection / policy spoofing / PII leakage 未形成系统化 suite；
- bilingual 和 indirect financial promise 覆盖有限；
- latency/cost threshold 未纳入评测；
- concurrency failure 未成为 eval evidence。

## 16. Current Hardening Priority

基于当前代码状态，推荐顺序：

1. P0-01 CI and Runtime Baseline
2. P0-02 Authentication and Approval RBAC
3. P1-04 Persistence Foundation
4. P0-03 Workflow State Consistency
5. P0-04 Async Agent Runtime
6. P1-01 Provider Resilience
7. P0-05 Observability and Cost
8. P0-06 External Read Integration and Typed Tool Runtime
9. P1-03 Context and Evidence Model
10. P1-02 Eval, Security and Draft Safety Expansion

每项合并后应更新本文件；后续 plan 不应继续基于本次静态快照。
