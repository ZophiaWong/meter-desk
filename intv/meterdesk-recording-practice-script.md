# MeterDesk 录屏练习稿

这份稿子按 6 到 8 分钟设计。录屏时不要追求把每个面板都点完，重点是让面试官看懂三件事：这是一个真实产品切片，agent 被后端治理，退款和 credit 不会绕过人工审批。

录屏前先跑一遍：

```bash
make db-up
make seed
make dev
```

打开三个页面：

- Workbench: `http://localhost:3000`
- Approval Queue: `http://localhost:3000/approvals`
- Eval Lab: `http://localhost:3000/eval-lab`

## 录屏节奏

### 0:00-0:35 开场

画面停在 Workbench 首页或 `TCK-1042`。

口播：

> 这是 MeterDesk，一个给 usage-based API 和 AI 平台用的账单支持工作台。
>
> 我做它不是想再放一个聊天框。真正要处理的问题是：当用户说自己被重复扣费时，agent 能不能读账单证据、引用退款政策、生成处理建议，同时又不能自己执行退款。
>
> 所以这个 demo 我会先走 Duplicate Charge 主路径，然后看审批门，最后看 Eval Lab 怎么检查 agent 的行为。

这一段不要展开技术细节。面试官只需要先知道产品边界：ticket-first、billing evidence、approval gate。

### 0:35-2:30 Duplicate Charge 主路径

画面进入 `TCK-1042`。先看 Decision Overview。

口播：

> 这里的入口是一张 billing dispute ticket，不是空白聊天框。
>
> 这张票据是 Duplicate Charge。系统已经把调查结果整理成一条 decision path：先看 evidence，再看 policy，然后是 decision、approval 和 mutation state。

指向 invoice 和 charge evidence。

> 最该看的证据在这里。`INV-2026-0418` 对应两笔 captured charges，而且金额都等于 invoice total。对支持人员来说，这比让 agent 自己解释一大段文字更有用，因为他可以直接看到判断依据。

指向 policy citation。

> 退款判断引用的是 `REFUND-DUP-001 v2026.02`。我这里没有做大规模 RAG，也没有让模型从一堆文档里自由发挥。v1 里 policy 是显式记录，eligibility check 也是后端控制的。

指向 draft。

> Agent 会生成 internal note 和 customer reply draft。customer reply 只是草稿，系统不会自动发给客户。这个限制很刻意，因为账单类场景里，自动承诺退款风险太高。

### 2:30-3:40 解释 approval gate

画面停在 pending approval 或 mutation blocked 的位置。

口播：

> 这里是我最想让面试官看的地方。Agent 可以提出 refund，但它拿不到直接执行退款的权限。
>
> FastAPI 创建的是 approval request。只要审批还没完成，mutation state 就是 blocked。也就是说，系统知道应该退款，但它也知道自己现在还不能退款。

如果页面能看到 trace 或 safety rail，展开一两项就够。

> 底层 trace 会记录这次 run 读了什么 evidence、用了什么 policy、创建了哪个 approval。这个 trace 不是为了好看，是为了事后能回答：agent 到底看过什么，为什么这么判断，有没有绕过安全门。

### 3:40-4:45 Approval Queue

切到 `http://localhost:3000/approvals`。

口播：

> Pending action 不只是在 Workbench 里显示，它会进入独立的 Approval Queue。
>
> 审批动作是人工动作。approve 之后最多创建一次 mock mutation；reject 就关闭请求，不创建 mutation。这里还是 mock-only，不接真实 Stripe 或支付系统。

如果录屏时不想改变 demo 状态，可以只讲，不点击 approve/reject。

> 录屏里我不一定要真的点 approve。重点是讲清楚状态机：pending 时不能 mutation，approved 后只能执行一次，rejected 后不会执行。

### 4:45-6:10 Eval Lab

切到 `http://localhost:3000/eval-lab`。

口播：

> Eval Lab 不是只问“最后回答得像不像”。它会检查 trace 过程。
>
> Duplicate Charge cases 要看 outcome 是否正确，证据有没有读全，policy 有没有引用，涉及退款时有没有进入 approval，而不是提前 mock mutation。

指向 Usage Spike blocked gap。

> Usage Spike 现在还是 blocked coverage gap。这个地方我会主动讲，因为它说明 eval 没把没完成的能力藏起来。Duplicate Charge 是 v1 主路径，Credit/Refund Dispute 是支持路径；Usage Spike 是计划内但还没打通的 runner。

这一段不要讲太久。Eval 的作用是让面试官看到你知道怎么验证 agent，而不是只做一个看起来能跑的 UI。

### 6:10-7:10 支持场景

回到 Workbench，打开 `http://localhost:3000/?ticket=TCK-1137`。

口播：

> 这张票据是 Credit/Refund Dispute。它不是第二个产品线，而是说明同一套治理路径可以复用。
>
> 这里会读取 trial credit、cancellation timing、prior adjustment 和 policy refs。金额计算仍然由 deterministic decision tool 处理，不让模型自己拍脑袋算 refund。

如果时间紧，这段可以删。录屏短一点比讲到后面失控更好。

### 7:10-7:45 收尾

画面回到 Workbench 或架构图。

口播：

> 总结一下，MeterDesk 不是万能客服机器人。它是一个受治理的 billing support workbench。
>
> 我在这个项目里重点处理了几个边界：Next.js 负责界面，FastAPI 控制 workflow 和 tool execution，Postgres 保存 audit state，provider 只在窄边界里生成结构化结果和 draft text。高风险 refund 或 credit 必须走人工审批，eval 也会检查这个过程。
>
> 如果继续做，我会优先补 Usage Spike runner，或者把 policy / eligibility engine 拆得更清楚，而不是先接真实支付系统。

## 录屏前检查

- 页面不要停在 loading 或错误状态。
- `TCK-1042` 能看到 completed baseline run。
- Approval Queue 里能看到 pending approval。
- Eval Lab 能看到 Duplicate Charge、Credit/Refund Dispute 和 Usage Spike blocked gap。
- 浏览器缩放保持 100% 或 90%，不要让文字挤在一起。
- 说到 "mock mutation" 时补一句 "v1 不接真实支付系统"。

## 录屏后自检

看回放时只问四个问题：

- 30 秒内有没有说清楚 MeterDesk 是什么？
- 有没有点到 invoice/charge/policy 这些具体证据？
- 有没有讲清 approval 前不会 mutation？
- 有没有解释 Eval Lab 为什么看 trace，而不只是看最终回答？

如果四个问题都答得上，这版录屏就够用了。
