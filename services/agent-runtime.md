---
title: Agent 的工作怎样持续，工具在哪里执行
subtitle: Harness、Durable Object 与执行环境的分工
source_cutoff: 2026-11-06
---

# Agent 的工作怎样持续，工具在哪里执行

同一份资料更新任务，可能读到一半被重启，也可能需要系统包生成预览。前者需要保存工作与恢复入口，后者需要工具运行环境。文件、会话和外部结果分别回答不同问题。

2026-10-20 补充 Browser／browserTool 的会话存活与中断边界，并接回 API MCP 事件调查入口；10 月 13 日核对的 OpenCodeHarness 与 runtime 连接排空规则保留原范围，PiHarness 基础机制仍按 2026-10-03 阅读。

2026-10-28 定向补入 Computer 的执行恢复、Think 工作区迁移和 Pi 1.4 升级条件；这些是不同层的恢复机制，不能从其中一层推断浏览器调用或外部动作会安全重放。

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

<!-- chapter: pi-14会停放反复崩溃的任务也会改变存储 -->

## Pi 1.5：进度落盘、继续工作与升级条件

11 月 3 日的 Agents SDK **0.33.0** 接入 Pi **1.5**。流式答案与工具输出即时可见，但默认最多约 **1 秒**内批量保存；崩溃可能丢失这段进度。`settings.progress.persistWithinMs` 控制窗口，设为 `0` 逐次写入，存储开销也随之增加。[S209] [S105]

`session.watch()` 替代 `session.events()`，先取得当前 view 再接变化；对象重启须重新开 watch。`session.continue()` 可在 idle session 的既有 transcript 上继续，不追加消息；先查询原 `operationId`，再保留新的 continuation receipt。已经以答案结束的 transcript 返回 `unanswered / nothing_to_answer`，不是无限续跑入口。[S209] [S105]

旧 **Pi 1.4** 的 `parked`／`retry()` 已移除。连续中断达到 `settings.restartLimit`（默认 5）时任务结束：工具得到错误结果，模型请求可使 run 以 `unanswered / restart_limit` 结束；处理原因后再明确继续。`defaults.maxTurns` 限制新 session 的工具轮数。[S209] [S105]

Pi 1.5 会话不能由 **1.4** 读取，之前 1.4 迁移也不能由 **1.3** 读取；回退代码不等于恢复旧 schema。升级前确定存储与恢复安排，本页没有执行安装或迁移。`wait()` 的 signal 只停止等待；`abort()` 等 session idle，忽略 signal 的自定义工具仍可能运行。[S209] [S105] [S178]

### Skills 现在从文件加载

Agents SDK **0.32.0+**、Think **0.23.0+** 可从 Computer Workspace、R2 或代码加载 skills，Think 每轮重新列目录；`/workspace/.agents/skills/` 的文件可在下一轮使用。旧 `agents:skills`、compile、`SkillRegistry`、`skillWorkspace` 移除，`runner()` 改从 `agents/skills/runner` 接入。部分格式违规会带 warning 加载，但缺 description、缺失或不可解析的 frontmatter 等仍会跳过；写入前用 `parseSkill()` 核对；加载成功不证明严格校验或工具权限已经满足。[S210] [S211]

## Computer：重放执行记录，仍要保护外部动作

`@cloudflare/computer` 提供 DO 内的文件工作区；`WorkerJavaScriptBackend` 执行 JavaScript，完整 Linux 仍由 Sandbox 承担。10 月 26 日 **v0.7.0** 增补中断恢复与等待批准，当前文档把它们标为 experimental。[S175] [S176]

| `onInterrupt` | 重启后的处理 | 应先确认 |
|---|---|---|
| `fail`，默认 | 该 run 失败 | 如何报告与接续 |
| `restart` | 从头执行，调用与输出都会再发生 | 整段工作是否可重做 |
| `replay` | 从头运行，已记入 journal 的调用结果复用，再继续执行 | 未记下结果的调用是否可重复 |

**Computer 重放会重复外部动作吗？** 会有这个窗口：外部请求成功、journal 尚未取得结果时中断，恢复仍可能再调用。host module 的 `callId` 跨重跑稳定，可传给支持幂等的服务；不能安全重做的函数可用 `unsafeToRepeat()`，中断时让 run 失败，再核对外部结果。它不能撤回第一次动作。[S175] [S176]

恢复在下一次调用 `workspace.runtime` 时触发；需要主动唤醒时，由 DO alarm 调用 `workspace.runtime.recover()`。`ctx.interrupt()` 可等待应用答复，应用通过 `pending()`／`respond()` 处理；等待不计 timeout，但批准返回后函数会再执行，批准前的工作也必须能重做。[S176]

实验边界会影响选型：replay 的 `fetch` 会缓冲响应，默认每个 body 上限 **1 MiB**；路径必须保持一致，改变 runtime 条件或不兼容的 package 升级会使中断 run 失败。journal 暂占 DO 存储，不能据此承诺任意任务、任意升级后都能恢复。[S176]

### Think 旧工作区为什么会变空

10 月 20 日 Think 与 Agent Skills 改用 Computer；`@cloudflare/shell` 和 Think 的 `createExecuteTool` 停止维护。新旧文件表格式不同，**没有自动迁移**：直接升级会看到新空工作区，旧数据仍在原表。需要保留文件时先按官方迁移脚本复制和核对；这不等于重建旧进程。[S177]

## OpenCodeHarness 的会话与工具边界

2026-10-12 发布的 `OpenCodeHarness` 是 experimental 集成，要求 Agents SDK ≥ 0.28.0；当前支持的 OpenCode packages 范围为 `^2.0.24`。它把 OpenCode Workerd host 放进普通的 SQLite-backed Durable Object：OpenCode 负责 loop、transcript、tools 与 session recovery，Lifecycle jobs 负责持久工作和中断后的唤醒。[S132] [S133]

插件随 Worker 打包。原有本地文件、shell 等工具需要移除，或通过插件接上合适的外部执行环境；DO 中保存会话不会同时提供这些能力。客户端可先读 `messages()` 或 `history()` 取得上下文，再订阅事件；要恢复已持久化事件，保存 `event.durable.seq`，重连后将它作为 `session.log()` 的 `after`。这条日志不重放未提交的 live text delta，客户端仍要协调快照与续读。[S133]

## Browser 保存的是活会话，不是快照

2026-10-13 起的 Agents SDK `browserTool` 让 agent 在后续 turn 回到同一个 Browser Run 浏览器。浏览器对象在 Durable Object 外运行，DO 保存 session identifier；DO hibernation 后，只要远端浏览器仍活着，就能重新连接并继续使用 tabs、cookies 与登录状态。SDK 需要 `v0.28.0` 或更高版本，应用要创建 `Browser`、交给 `Lifecycle`，并在 Pi Durable registry 中安装工具。[S143] [S144]

默认 idle timeout 是 **10 分钟**，它不是“永久保存”。到期、关闭或崩溃后，下一次使用会创建新浏览器；当前工具通过 `notice` 告知旧状态已丢失，不再将旧版 `restarted: true` 当作现行工具结果字段。旧 tabs、cookies 与登录状态不会从快照恢复。`keepAliveMs` 可以调整保活时间，所需长期状态仍应由应用保存。[S144]

### Tab 共享和隔离不是同一件事

Pi 默认给每段 conversation 一个 active tab；sessions、forks 与 subagents 可以操作不同页面，但同一 `Browser` 内 cookies 与 logins 共享。一个 tab scope 不是独立 profile。需要隔离不同用户的登录会话时，应使用不同的 `Browser`，不能只换 scope。[S144]

同一 conversation 内的 browser calls 顺序执行。模型可用 `sessionId: "active"` 回到自己的 tab；要让多个工具刻意共享 tab，可传相同 `scope`。自定义 harness 通过当前 `browser.session()` 接入；locking session 应在 `finally` 中 `close()`，signal abort 不会自行释放这个应用持有的锁。不要继续套用旧 `Browser.connect()` 的结果协议。[S144]

### 中断、停止与人工接管

Pi 不会自动重放因 eviction 而中断的 browser call，因为再次提交表单或点击按钮可能产生第二次外部动作。模型收到 interrupted result 再决定继续；每次调用默认 `timeoutMs` 为 **60 秒**。[S144]

**停止对话会取消浏览器调用吗？** 11 月 6 日查阅的当前文档与 Pi 1.5 公告已更新：Pi、AI SDK 和 TanStack AI adapter 接到 harness abort 后，等待 tab 的调用退出，运行中的调用以错误结束并释放 tab。这替代本页旧版“不取消已运行调用”的说明；自定义 session 的锁仍须按上一节关闭。[S209] [S144]

已经执行的点击、提交和外部动作不会撤回。应用仍要保存可识别的动作、查询结果或使用幂等；取消与恢复分别检查，不以工具返回错误推定外部动作未发生。[S144]

`browser.liveView()` 返回同一浏览器的 Live View 链接，列出跨 scopes 的 open tabs，供人查看、登录、处理 MFA／CAPTCHA 或敏感输入。它不会启动浏览器；没有打开、已关闭或已过期的浏览器返回 `undefined`。调用入口须先验证访问用户，链接也不代表已有持久快照。`browser.close()` 则明确关闭浏览器。[S144]

下面的合成测试只说明应保留哪些观察，不是已执行的云端测试：

```text
turn 1  request /tabs/a             -> 应命中 open tab
idle    超过 10 分钟或 close/crash  -> 不应假定 tab 仍存在
turn 2  request /tabs/a again       -> notice 提示旧浏览器状态丢失
abort   harness browser call        -> 错误结束并释放 tab，已发生动作保留
```

这些检查分别回答“能否重连”“是否换了浏览器”“停止后是否还运行”。其中任何一项都不能代替对表单是否已提交、登录是否仍有权限的核对。

### 不公开 dev server，也能在浏览器预览

Agents SDK **0.31.0+** 的 internal hostnames 将 `preview.internal` 等请求交给 agent 的 Workspace／Sandbox 或 service-bound Worker；目标映射可跨 turn、浏览器重启和 redeploy 保存，但不保存浏览器旧状态或进程。当前最多 8 个 hostnames，仅 HTTP port 80、不支持 HTTPS／WebSocket。普通 hostname guardrails 不应用于内部 host；`allowedDomains: []` 可只允许内部站点，应用另外限制目标端口、路径和数据。[S212] [S144]

Browser Run 10 月 30 日默认更新 Chrome **152**，Quick Actions UA 随之改变；11 月 3 日 crawl 增加 URL `outcome` 和最多 50 个 origin 的 robots 诊断。检查成功、拒绝和 timeout 时按各 URL 结果判断，不以任务终态代替。[S220] [S221]

## DO 发布延迟与调用重试

10 月 30 日起，DO 默认 `deferred` 代码更新给 active object 最多 **300 秒**等休眠，仍活跃则 reset；`code_update_strategy` 可明确选择策略。它是 best effort，连续部署可跳过中间版本，不能用来替代 checkpoint，也不能假定部署返回后所有 DO 已运行新代码。[S207] [S208]

11 月 5 日起，stub 的 `fetch()`／RPC 可自动重试特定 `.retryable` 传输错误，默认首次加 4 次、不在首次开始 10 秒后启动新重试。未知接收结果沿同一请求身份去重；`retryable()` 标记则允许已到达的方法再次执行，须先保证幂等。应用错误、overload、HTTP 错误响应及不可重发的 stream／RPC 参数不适用。Wrangler **4.158.0+** 才提供新标记与 stub 配置；外层重试须计入平台次数。[S205] [S206]

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

[S175]: https://developers.cloudflare.com/changelog/post/2026-10-26-computer-durable-javascript/ "Computer v0.7.0：中断恢复与等待批准"
[S176]: https://developers.cloudflare.com/agents/tools/filesystem/ "Computer 文件工作区、replay、批准与实验限制"
[S177]: https://developers.cloudflare.com/changelog/post/2026-10-20-think-computer-workspace/ "Think 改用 Computer 工作区与旧文件迁移"
[S178]: https://developers.cloudflare.com/changelog/post/2026-10-22-pi-harness-pi-1-4/ "Agents SDK 0.30.0 与 Pi 1.4 恢复和 schema 边界"

[S205]: https://developers.cloudflare.com/changelog/post/2026-11-05-durable-objects-automatic-retries/ "Durable Objects 自动重试发布"

[S206]: https://developers.cloudflare.com/durable-objects/best-practices/automatic-retries/ "Durable Objects 自动重试的范围与限制"

[S207]: https://developers.cloudflare.com/changelog/post/2026-10-30-durable-objects-deferred-code-updates/ "Durable Objects 默认延迟代码更新"

[S208]: https://developers.cloudflare.com/durable-objects/deployments/durable-objects-code-updates/ "Durable Objects 代码更新策略"

[S209]: https://developers.cloudflare.com/changelog/post/2026-11-03-pi-harness-pi-1-5/ "Agents SDK 0.33.0 与 Pi 1.5 迁移"

[S210]: https://developers.cloudflare.com/changelog/post/2026-10-29-agent-skills-from-files/ "Agent Skills 从 Workspace 文件加载"

[S211]: https://developers.cloudflare.com/agents/skills/ "Agent Skills 来源、校验与执行"

[S212]: https://developers.cloudflare.com/changelog/post/2026-10-28-browser-internal-hostnames/ "Browser internal hostnames 私有预览"

[S220]: https://developers.cloudflare.com/changelog/post/2026-10-30-chrome-152/ "Browser Run 更新到 Chrome 152"

[S221]: https://developers.cloudflare.com/changelog/post/2026-11-03-crawl-result-diagnostics/ "Browser Run crawl 结果与 robots.txt 诊断"
