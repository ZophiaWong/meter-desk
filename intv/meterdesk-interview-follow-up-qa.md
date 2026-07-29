# MeterDesk 面试追问清单

这份清单不是背诵稿。准备时先看问题，再用自己的话回答。面试时回答短一点，等对方追问再展开。

## 产品定位

### 你为什么做这个项目？

我想做一个比聊天 demo 更接近真实业务的 AI 产品。账单争议很适合这个方向：它有明确证据、明确政策，也有不能乱来的高风险动作。

MeterDesk 从 ticket 开始，不从聊天框开始。Agent 可以调查、总结、写草稿，但 refund 或 credit 必须先进入人工审批。

### 为什么选 Duplicate Charge 做主路径？

Duplicate Charge 的证据链比较清楚：invoice、charge、amount、status、policy。它适合做 v1 golden path，因为面试官不用懂太多业务背景，也能看出系统有没有真的查证据。

Usage Spike 和 Credit/Refund Dispute 保留为支持场景。它们说明同一套治理模型可以复用，但不会把 v1 撑成一个大而散的 billing CRM。

### 这个项目和普通客服 chatbot 有什么区别？

普通 chatbot 的入口通常是用户输入。MeterDesk 的入口是一张 billing dispute ticket。

更重要的是权限边界。Agent 不能自由调用工具，更不能自己退款。它通过后端受控工具读证据、生成草稿、创建审批请求。涉及钱的 mutation 被单独拦住。

## 架构边界

### 前端、后端、数据库分别负责什么？

Next.js 负责 Workbench、Approval Queue 和 Eval Lab 的页面与交互。

FastAPI 负责 workflow、tool execution、approval、eval runner 和 mock mutation。它是安全边界。

Postgres 保存 ticket、billing evidence、agent runs、tool traces、approvals、mock mutations 和 eval results。这样 demo 不是一次性的页面状态，审计记录能查回来。

### 为什么不让前端直接调用 agent tools？

因为前端不应该成为权限边界。账单证据、approval、mutation 都需要后端统一验证和记录。

如果前端能直接调 tool，trace 和 approval gate 很容易被绕开。MeterDesk 把工具执行放在 FastAPI 里，前端只发起 workflow 或读取状态。

### 为什么 v1 只接一个 OpenAI-compatible provider？

这个项目的重点不是模型网关。v1 要先把 governed workflow 跑顺：工具边界、审批、trace、eval。

多 provider 会引入很多噪音，比如路由、fallback、模型对比。现在保留一个 OpenAI-compatible boundary 就够了，以后要换 provider 也有位置。

## Agent governance

### Agent 到底能做什么，不能做什么？

能做的事：读取证据、引用政策、生成 internal note、生成 customer reply draft、提出 refund 或 credit 请求。

不能做的事：绕过后端直接访问数据、直接执行退款、自动发送客户回复、调用真实支付系统。

这里我更愿意把 agent 当成一个受控 workflow 的参与者，而不是系统的管理员。

### 为什么 decision tool 是 outcome authority？

因为退款金额和 eligibility 不应该靠模型自由判断。模型可以帮助写解释和草稿，但金额、政策命中、是否需要审批这些结论要由后端 deterministic logic 负责。

这样做的好处是可测试，也方便 eval。错了可以定位到规则或数据，而不是只说"模型回答不稳定"。

### LLM 在这个项目里还有什么价值？

它的价值在两块：把 evidence 和 policy 组织成支持人员能读懂的 draft，以及在 M9 里生成 bounded investigation plan。

但它不是最终的权限来源。真正执行工具、验证 plan、创建 approval、执行 mock mutation 的都是后端。

### 什么机制阻止未授权退款？

Refund 或 credit mutation 是 high-risk action。Agent 只能提出 action，FastAPI 创建 approval request。

只要 approval 还是 pending，mutation tool 就是 blocked。Approve 后最多创建一次 mock mutation；reject 后不会创建 mutation。重复 approve 也会返回已有 mutation，不会重复执行。

## Trace 和 audit

### Trace 记录什么？

至少记录 agent run、ticket id、工具类别、权限级别、input summary、output summary、evidence refs、policy refs、approval refs 和 error state。

Trace 应该能回答三个问题：agent 看了什么，做了什么，为什么提出这个建议。

### 为什么不做完整 trace replay？

v1 先不做 trace replay。现在更需要的是能解释和能 eval 的 trace。

完整 replay 会带来更多 UI 和数据设计工作，但不一定提高这个阶段的面试说服力。所以我把它放到 out of scope。

### Seeded baseline 会不会显得不真实？

Seeded baseline 是为了稳定演示，不是假装无 key 也跑了模型。

README 和 walkthrough 里已经把边界写清楚：无 key baseline 是已写入数据库的 completed audit trail；真实 provider 路径需要配置 key，然后用 `make demo-reset-live` 清空运行态再跑。

## Eval

### Eval Lab 检查什么？

它检查 final outcome，也检查 trace path。

比如 Duplicate Charge 不是只看最后说"应该退款"。它还要看 invoice、charge、policy 这些证据有没有被读取，approval request 有没有创建，approval 前有没有避免 mutation。

### 为什么 deterministic checks 比 LLM-as-judge 更重要？

账单安全相关的问题不应该交给 judge 模型主观打分。

Evidence coverage、policy citation、approval routing、mutation-before-approval 这些都可以做确定性检查。LLM-as-judge 只适合看 draft 文本是否清楚、语气是否专业、有没有过度承诺。

### Usage Spike blocked gap 怎么解释？

我会直接说它还没实现 governed runner。

这不是 Duplicate Charge 的失败，也不是 eval 系统坏了。它说明 Eval Lab 会把覆盖缺口暴露出来。对面试来说，这比把未完成能力藏起来更可信。

## 数据和业务

### Duplicate Charge 怎么判断？

判断起点是同一张 invoice 下出现两笔 captured charges，金额都等于 invoice total，并且没有已有 refund 或 adjustment 覆盖掉这笔问题。

判断时还需要引用 refund policy，比如 `REFUND-DUP-001 v2026.02`。

### Credit/Refund Dispute 为什么是支持场景？

它涉及 trial credit、subscription/cancellation timing、prior adjustment 和 refund policy，业务复杂一点。

我把它放在支持路径里，是为了说明治理模型能复用。但 v1 不把它扩成独立产品线。

### 为什么所有 mutation 都是 mock-only？

v1 的目标是把治理流程跑清楚，不是接真实支付系统。

真实支付会引入 auth、合规、幂等、失败补偿、对账和人工操作流程。现在做 mock mutation，反而能把系统边界讲清楚：即使是 mock，也必须走审批。

## 取舍

### 为什么不做 pgvector 或大规模 RAG？

当前 policy 是显式记录和 eligibility check。账单退款这种场景不适合一开始就把判断交给向量检索。

RAG 可以以后加，但不能替代政策引用、审批和确定性检查。

### 为什么不先做更漂亮的 UI？

因为这个项目最值钱的地方不是 UI 装饰，而是治理链路能跑通。

M5 做了 Support Workbench 方向的 polish，但不会为了视觉效果牺牲 trace、approval 和 eval 的清晰度。

### 如果继续做，你会先做什么？

我会优先做两件事之一。

第一，补 Usage Spike governed runner，让 Eval Lab 里的 blocked gap 变成可执行场景。

第二，把 policy / eligibility engine 拆得更清楚，让不同 billing policy 的可测试性更强。

我不会先接真实支付系统。那会把项目带到另一个风险面，和现在的面试目标不匹配。

## 反问时可以主动补充

如果面试官对工程质量感兴趣，可以补一句：

> 我在这个项目里最刻意控制的是权限边界。LLM 的能力很强，但我不想让它成为最终的业务权限来源。它可以计划、总结和起草；后端负责验证、执行和记录。

如果面试官对产品判断感兴趣，可以补一句：

> 账单支持不是一个适合"自动化到底"的场景。真正有价值的是把证据找齐、把判断讲清楚，然后让高风险动作进入人工审批。

如果面试官对后续规划感兴趣，可以补一句：

> 下一步我会补 Usage Spike，不是因为它最炫，而是因为它能检验这套 governance 和 eval 是否真的能迁移到另一类 billing dispute。
