---
title: Agent 的工作怎样持续，工具在哪里执行
subtitle: Harness、Durable Object 与执行环境的分工
source_cutoff: 2026-10-13
---

# Agent 的工作怎样持续，工具在哪里执行

同一份资料更新任务，可能读到一半被重启，也可能需要系统包生成预览。前者需要保存工作与恢复入口，后者需要工具运行环境。文件、会话和外部结果分别回答不同问题。

2026-10-13 定向复核 OpenCodeHarness 与 Workers runtime 更新时的连接排空规则；PiHarness 部分保留 2026-10-03 的查阅范围。

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

## Runtime 更新时，连接能多持续多久

2026-10-12 起，Workers 例行 runtime 更新给旧进程的既有请求和连接最多 20 分钟排空，此前为最多 30 秒；新 HTTP 请求转到新 runtime。窗口属于旧进程，不能解释成每条请求都另外获得 20 分钟。[S125] [S126]

崩溃、资源压力和关闭仍可更早中断连接，WebSocket 也需要重连。HTTP 请求结束或客户端断开后，`waitUntil()` 仍只延长最多 30 秒；它与 runtime 更新排空是两项规则。恢复时从已提交状态继续，重建订阅，并对外部动作沿用幂等或结果核对，不能仅根据断线重发整个任务。[S125] [S126]

## `replay: "safe"` 要有工具行为支撑

官方示例把字数统计工具声明为 `replay: "safe"`：相同输入重新计算不会多寄一封信或多扣一笔钱。字段表达重放约定，约定成立仍取决于工具。读取当前时间或不断变化的网页也与纯计算有不同复读含义。[S104]

应用准备一项不可逆动作前，应有稳定的逻辑动作 ID、外部幂等或结果查询；响应丢失后保留[结果未知](../docs/glossary.md#uncertain--结果未知)。恢复工作和重放副作用分别检查，不因为 SDK 保存了 transcript 就自动重做动作。

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
