# MeterDesk 核心能力学习提纲

这份提纲是给录屏和面试追问用的。目标不是把每个概念学成论文水平，而是能用项目里的设计说清楚：为什么这样做，替代方案是什么，风险在哪里。

## 学习顺序

建议按这个顺序复习：

1. 产品定位和账单业务
2. Agent governance
3. Approval gate 和 mock mutation
4. Trace、audit 和 eval
5. Full-stack 边界
6. 面试追问模拟

每天复习一到两块就够。不要一上来背所有细节，先把主线讲顺。

## 一、产品定位和账单业务

你要能讲清 MeterDesk 解决的是哪类问题：

- usage-based API / AI 平台的账单争议。
- v1 主路径是 Duplicate Charge。
- Supporting scenarios 是 Usage Spike 和 Credit/Refund Dispute。
- v1 不做真实支付、不做自动发信、不做通用客服机器人。

需要补的业务概念：

- invoice、charge、payment、credit ledger、usage record、refund、adjustment 的区别。
- 什么算 duplicate charge：同一 invoice 下出现重复 captured charge，金额和 invoice total 对得上。
- 为什么 refund/credit 是 high-risk action。
- 为什么 customer-facing reply 必须是 draft-only。

练习题：

- 用 30 秒解释 Duplicate Charge。
- 用 60 秒解释为什么 Usage Spike 不是 v1 主路径。
- 说清 invoice 和 charge 的区别，不要混着用。

## 二、Agent governance

这个项目的重点不是"我用了 LLM"，而是"LLM 被放在一个受控 workflow 里"。

你要掌握的概念：

- Read tools：读 ticket、invoice、charge、usage、credit、policy。
- Decision tools：判断 eligibility、计算 amount、分类 outcome。
- Draft tools：生成 internal note 和 customer reply draft。
- Approval tools：创建和读取 approval request。
- Mutation tools：只在 approval 后执行 mock refund 或 mock credit。

要能讲清的边界：

- Agent 不直接碰数据库。
- Agent 不直接执行 refund。
- Frontend 不直接调用 tools。
- FastAPI 控制 workflow 和 tool execution。
- Deterministic decision tool 决定 outcome 和金额，LLM 主要负责 draft text。

练习题：

- 为什么不能让模型自己决定 refund amount？
- 如果 provider 输出了错误金额，系统怎么防住？
- 为什么 M9 允许 LLM 规划 investigation，但不允许它规划 mutation？

## 三、Approval gate 和 mock mutation

这一块是录屏里最值得停顿讲的地方。

你要能画出状态：

```text
proposed -> pending approval -> approved -> mock mutation
                          -> rejected -> no mutation
```

要能解释的规则：

- Pending approval 时 mutation blocked。
- Approved request 最多创建一次 mock mutation。
- Rejected request 不创建 mutation。
- Opposite terminal action 返回冲突，比如已 reject 再 approve。
- Mock mutation 也必须记录 ticket、agent run、approval request、amount 和 reason。

常见追问：

- "既然是 mock，为什么还要审批？"
  因为 v1 要把安全模型讲清楚。mock mutation 是产品证据，不是绕过治理的借口。

- "以后接真实支付怎么办？"
  先保留同样的 approval contract 和 idempotency 约束，再处理 auth、webhook、对账和失败补偿。不能直接把 mock mutation 换成真实 API 调用。

## 四、Trace、audit 和 eval

Trace 是这个项目能被信任的基础。

你要知道 trace 里应该有什么：

- agent run id 和 ticket id。
- tool category 和 permission level。
- input summary 和 output summary。
- evidence refs 和 policy refs。
- approval refs。
- error state。
- final recommendation 和 draft outputs。

Eval 要讲得更具体：

- Outcome correctness：最终结论是否正确。
- Required evidence：invoice、charge、policy、credit、usage 等证据是否读到。
- Policy compliance：是否引用正确 policy。
- Approval routing：是否把 refund/credit 送进 approval。
- Tool planning：是否有 plan 和 verifier trace。
- Draft quality：文本是否清楚，是否避免过度承诺。

你需要特别记住：

- Deterministic checks 是主信号。
- LLM-as-judge 只用于 draft quality。
- Mutation-before-approval 是 blocking failure。
- Usage Spike blocked gap 要主动解释，不要假装已完成。

练习题：

- 用 90 秒解释 Eval Lab，不说"它就是测试页面"。
- 解释为什么 eval 要看 trace path。
- 说出一个 deterministic check 和一个 LLM-as-judge 适合检查的东西。

## 五、Full-stack 边界

这部分要讲得朴素一点。面试官不需要听一串技术名词，他需要知道你为什么这么分层。

项目里的分工：

- Next.js：Workbench、Approval Queue、Eval Lab 的页面和交互。
- FastAPI：workflow、tool execution、approval、eval、mock mutation。
- Postgres：durable state 和 audit history。
- Provider boundary：一个 OpenAI-compatible provider，v1 不做多 provider gateway。
- Mock systems：账单、支付、support 集成都不接真实外部系统。

你要能解释的取舍：

- 为什么不用前端控制业务流程。
- 为什么不做 public external API。
- 为什么不加 LangGraph 或复杂 agent framework。
- 为什么不做 pgvector。
- 为什么 seeded baseline 和 live provider path 要分开讲。

练习题：

- 画一遍请求链路：operator 点击 Run investigation 后发生什么？
- 说清 provider missing 为什么返回 503，而且是在创建 run 之前返回。
- 解释 `make seed` 和 `make demo-reset-live` 的区别。

## 六、录屏练习方法

第一遍不要录屏，只打开页面按顺序讲。卡住的地方记下来。

第二遍录屏，但不要追求完美。录完只看两个点：有没有超时，有没有讲清 approval gate。

第三遍再修口播。别把每句话背死，背死了反而像念稿。记住每个页面只讲一个重点：

- Workbench：证据和决策链。
- Approval Queue：人工审批阻止未授权 mutation。
- Eval Lab：eval 检查 trace，不只看 final answer。

推荐节奏：

- 30 秒讲项目定位。
- 3 分钟讲 Duplicate Charge。
- 1 分钟讲 approval。
- 1 分钟讲 eval。
- 30 秒讲下一步。

## 七、一周复习安排

### 第一天：产品定位

读 `README.md`、`docs/specs/product-scope.md` 和现有 walkthrough。练 30 秒开场。

### 第二天：主路径

只练 `TCK-1042`。能说清 invoice、charge、policy、draft、approval、mutation state。

### 第三天：治理模型

读 `docs/specs/agent-governance.md` 和历史实现规格
`docs/archive/milestones/m3-governed-agent-loop.md`。重点练"agent 能做什么，不能做什么"。

### 第四天：Eval

读 `docs/specs/eval-strategy.md` 和历史实现规格
`docs/archive/milestones/m10-eval-regression-history.md`。练习解释 deterministic checks。

### 第五天：架构

读 `docs/specs/system-architecture.md`。画一遍 Next.js、FastAPI、Postgres、provider boundary 的关系。

### 第六天：追问

拿 `intv/meterdesk-interview-follow-up-qa.md` 自问自答。每个回答尽量控制在 30 到 60 秒。

### 第七天：录屏

录两遍。第一遍允许卡顿，第二遍只修最影响理解的地方。不要为了追求完美反复录十几遍，那会把表达录僵。

## 八、最容易被问倒的点

### "这不就是一个 demo seed 吗？"

回答重点：seed 是稳定演示基线，真实 provider path 仍然存在。两者边界明确。

### "LLM 具体做了什么？"

回答重点：LLM 参与 bounded planning 和 draft text；后端控制工具、decision、approval、mutation。

### "为什么不用真实 Stripe？"

回答重点：真实支付不是 v1 的主要风险。v1 先把 approval contract、idempotency 和 audit trace 跑稳。

### "Eval 为什么可信？"

回答重点：安全相关项用 deterministic checks。LLM judge 不负责审批和证据检查。

### "项目下一步是什么？"

回答重点：优先补 Usage Spike runner，或者强化 policy / eligibility engine。不要说泛泛的"接更多平台"。

## 九、最低掌握线

如果时间很紧，至少把下面几句话讲熟：

> MeterDesk 从 ticket 开始，不从聊天框开始。
>
> Agent 可以调查和起草，但 refund 或 credit mutation 必须走人工审批。
>
> FastAPI 控制 tool execution，Postgres 保存 trace 和 audit state。
>
> Eval Lab 检查 evidence、policy 和 approval routing，不只看最终回答。
>
> Seeded baseline 是稳定演示，live provider path 仍然需要真实配置。

这几句讲顺了，录屏就不会散。
