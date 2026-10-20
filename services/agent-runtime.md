---
title: Agent 的工作怎样持续，工具在哪里执行
subtitle: Harness、Durable Object 与执行环境的分工
source_cutoff: 2026-10-20
---

# Agent 的工作怎样持续，工具在哪里执行

同一份资料更新任务，可能读到一半被重启，也可能需要系统包生成预览。前者需要保存工作与恢复入口，后者需要工具运行环境。文件、会话和外部结果分别回答不同问题。

2026-10-20 补充 Browser／browserTool 的会话存活与中断边界，并接回 API MCP 事件调查入口；10 月 13 日核对的 OpenCodeHarness 与 runtime 连接排空规则保留原范围，PiHarness 基础机制仍按 2026-10-03 阅读。

## 三种状态，三种职责

| 要留下什么 | 常见归属 | 恢复时先确认 |
|---|---|---|
| 对话、inbox、未完成 turn | harness 的持久状态 | 当时读了什么、下一步是什么 |
| 协调、唤醒与执行代次 | Durable Object / Lifecycle 或自己的任务系统 | 哪次执行还有效 |
| 文件、工具与进程 | Workspace / Containers / Sandbox | 文件还在吗，进程是否重启 |

这是编辑者按职责组织的地图。需要完整 Linux 的工具再进入 Sandbox；普通 API 不因为是 agent 就必须开一个容器。文件快照不会自动保存运行中的进程；[任务恢复模型](../examples/job-state/README.md)则只演示 SQLite 的领取与提交，不能当作云端 harness 的实现。

## PiHarness 多了一条具体实现路线

2026-10-02，Agents SDK 接入 PiHarness。Pi 管 agent loop，transcript、follow-up / steer inbox、model calls 与 tools；PiHarness 给它 DO SQLite 存储，并在有未完成工作时安排 Lifecycle 唤醒。进程内 scheduler 随 eviction 消失后，持久 job 的 alarm 可重新唤醒并打开存储继续。[S104] [S105]

这条路线是 beta，Pi Durable 是 experimental。应用仍自行选择模型、extension registry、工具、客户端入口和权限。不能把“可恢复 turn”理解成已经获得一台 Linux，或所有外部服务都参与同一事务。

## OpenCodeHarness 的会话与工具边界

2026-10-12 发布的 `OpenCodeHarness` 是 experimental 集成，要求 Agents SDK ≥ 0.28.0；当前支持的 OpenCode packages 范围为 `^2.0.24`。它把 OpenCode Workerd host 放进普通的 SQLite-backed Durable Object：OpenCode 负责 loop、transcript、tools 与 session recovery，Lifecycle jobs 负责持久工作和中断后的唤醒。[S132] [S133]

插件随 Worker 打包。原有本地文件、shell 等工具需要移除，或通过插件接上合适的外部执行环境；DO 中保存会话不会同时提供这些能力。客户端可先读 `messages()` 或 `history()` 取得上下文，再订阅事件；要恢复已持久化事件，保存 `event.durable.seq`，重连后将它作为 `session.log()` 的 `after`。这条日志不重放未提交的 live text delta，客户端仍要协调快照与续读。[S133]

## Browser 保存的是活会话，不是快照

2026-10-13 起的 Agents SDK `browserTool` 让 agent 在后续 turn 回到同一个 Browser Run 浏览器。浏览器对象在 Durable Object 外运行，DO 保存 session identifier；DO hibernation 后，只要远端浏览器仍活着，就能重新连接并继续使用 tabs、cookies 与登录状态。SDK 需要 `v0.28.0` 或更高版本，应用要创建 `Browser`、交给 `Lifecycle`，并在 Pi Durable registry 中安装工具。[S143] [S144]

默认 idle timeout 是 **10 分钟**，它不是“永久保存”。到期、关闭或崩溃后，下一次使用会创建新浏览器并返回 `restarted: true`；旧 tabs、cookies 与登录状态已经丢失，工具不会从快照恢复旧会话。`keepAliveMs` 可以调整保活时间，但持续活着的连接仍不等于持久化。所需状态若必须跨浏览器崩溃保留，仍应在应用自己的存储中保存，不能把浏览器 cookie 当数据库。[S144]

### Tab 共享和隔离不是同一件事

Pi 默认给每段 conversation 一个 active tab；sessions、forks 与 subagents 可以操作不同页面，但同一 `Browser` 内 cookies 与 logins 共享。一个 tab scope 不是独立 profile。需要隔离不同用户的登录会话时，应使用不同的 `Browser`，不能只换 scope。[S144]

同一 conversation 内的 browser calls 顺序执行。模型可用 `sessionId: "active"` 回到自己的 tab；要让多个工具刻意共享 tab，可传相同 `scope`。AI SDK 与 TanStack AI 在省略 `scope` 时共用一个 active tab，传入 conversation identifier 才分开；自定义 harness 可用 `Browser.connect({ scope })` 取得 CDP connection、active tab 与 `restarted` 标志。[S144]

### 中断、停止与人工接管

Pi 不会自动重放因 eviction 而中断的 browser call，因为再次提交表单或点击按钮可能产生第二次外部动作。模型会收到 interrupted result，再决定如何继续。**停止 conversation 也不会取消已经开始运行的 browser call**；该调用会完成或等到 `timeoutMs`，默认 **60 秒**。[S144]

因此恢复工作与停止外部动作要分开检查。若要避免重复提交，应用应让动作可识别、可查询或具备幂等语义；收到中断后先核对外部结果，不能把“模型不再说”写成“浏览器已经停止”。[S144]

`browser.liveView()` 返回同一浏览器的 Live View 链接，列出跨 scopes 的 open tabs，供人查看、登录、处理 MFA／CAPTCHA 或敏感输入。它不会启动浏览器；没有打开、已关闭或已过期的浏览器返回 `undefined`。调用入口须先验证访问用户，链接也不代表已有持久快照。`browser.close()` 则明确关闭浏览器。[S144]

下面的合成测试只说明应保留哪些观察，不是已执行的云端测试：

```text
turn 1  request /tabs/a             -> 应命中 open tab
idle    超过 10 分钟或 close/crash  -> 不应假定 tab 仍存在
turn 2  request /tabs/a again       -> 可能得到 restarted: true
stop    conversation                -> 已运行 call 仍可完成到 timeoutMs
```

这些检查分别回答“能否重连”“是否换了浏览器”“停止后是否还运行”。其中任何一项都不能代替对表单是否已提交、登录是否仍有权限的核对。

## Runtime 更新时，连接能多持续多久

2026-10-12 起，Workers 例行 runtime 更新给旧进程的既有请求和连接最多 20 分钟排空，此前为最多 30 秒；新 HTTP 请求转到新 runtime。窗口属于旧进程，不能解释成每条请求都另外获得 20 分钟。[S125] [S126]

崩溃、资源压力和关闭仍可更早中断连接，WebSocket 也需要重连。HTTP 请求结束或客户端断开后，`waitUntil()` 仍只延长最多 30 秒；它与 runtime 更新排空是两项规则。恢复时从已提交状态继续，重建订阅，并对外部动作沿用幂等或结果核对，不能仅根据断线重发整个任务。[S125] [S126]

## `replay: "safe"` 要有工具行为支撑

官方示例把字数统计工具声明为 `replay: "safe"`：相同输入重新计算不会多寄一封信或多扣一笔钱。字段表达重放约定，约定成立仍取决于工具。读取当前时间或不断变化的网页也与纯计算有不同复读含义。[S104]

应用准备一项不可逆动作前，应有稳定的逻辑动作 ID、外部幂等或结果查询；响应丢失后保留[结果未知](../docs/glossary.md#uncertain--结果未知)。恢复工作和重放副作用分别检查，不因为 SDK 保存了 transcript 就自动重做动作。

## MCP 事件与授权要把调查接回调用点

2026-10-13 的 Cloudflare API MCP 更新把 Workers Issues 作为首个 MCP Event 交给客户端。客户端用 `events/list` 发现 `cloudflare.alert.workers_observability_real_time_issue`，用 `events/subscribe` 按 account 或单个 Worker 订阅；Issues 检测到新故障或复发故障时，服务器把签名事件发到客户端 webhook，agent 不必轮询就能开始调查。使用前要在 Worker 启用 Issues，并以 Notifications Write 和 Workers Observability Write 权限连接支持 MCP Events webhook 的客户端。[S145]

2026-10-19 的 API MCP step-up authorization 区分 Minimal scope、`insufficient_scope` 与客户端追加授权。工具错误若表明 scope 不足，应用应把问题转成明确的追加授权或改变动作范围；不能把一次工具错误当作系统已自动提升权限，也不能通过关闭授权检查把失败改成成功。[S146]

接收端应验证来源与签名、限制时间窗并去重；这里引用的是官方公告，没有连接生产 MCP 账户。后续调查可以从[可观测性页](observability.md)入手，但告警事件与请求成功是两类证据。

## 判断是否适合自己的系统

先选一项无私人输入的可重做任务，明确版本、工具权限、持久成果和恢复条件；比较现有实现与所选 harness 的增量。API 变化和实验依赖留在对应实现旁，其他执行路线继续按自己的条件选择。[S105] [S133]

本页查阅官方机制，没有安装 SDK、迁移 DO schema、调用模型或进行云端重启实验。实现入口见[官方 Pi 文档](https://developers.cloudflare.com/agents/harnesses/pi/)，已有 Linux 工作空间的解释见[手册](../guides/handbook.md#workspace)。

<!-- SOURCES -->

[S104]: https://developers.cloudflare.com/changelog/post/2026-10-02-pi-harness/ "PiHarness 发布"
[S105]: https://developers.cloudflare.com/agents/harnesses/pi/ "PiHarness 状态与 Lifecycle"
[S125]: https://developers.cloudflare.com/changelog/post/2026-10-12-longer-runtime-update-grace-period/ "Workers runtime 更新延长连接排空窗口"
[S126]: https://developers.cloudflare.com/workers/platform/limits/ "Workers duration、waitUntil 与 runtime 更新限制"
[S132]: https://developers.cloudflare.com/changelog/post/2026-10-12-opencode-harness/ "实验性 OpenCodeHarness 发布"
[S133]: https://developers.cloudflare.com/agents/harnesses/opencode/ "OpenCodeHarness 存储、工具与事件恢复"
[S143]: https://developers.cloudflare.com/changelog/post/2026-10-13-persistent-browser/ "Agents SDK 跨 turn 的 Browser/browserTool"
[S144]: https://developers.cloudflare.com/agents/tools/browser/ "Browser 会话、tab、中断与 Live View"
[S145]: https://developers.cloudflare.com/changelog/post/2026-10-13-cloudflare-mcp-events/ "Cloudflare API MCP 作为 MCP Events 发送 Workers Issues"
[S146]: https://developers.cloudflare.com/changelog/post/2026-10-19-cloudflare-mcp-step-up/ "Cloudflare API MCP 的 step-up authorization"
