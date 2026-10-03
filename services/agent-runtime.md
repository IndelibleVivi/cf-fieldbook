---
title: Agent 的工作怎样持续，工具在哪里执行
subtitle: Harness、Durable Object 与执行环境的分工
source_cutoff: 2026-10-03
---

# Agent 的工作怎样持续，工具在哪里执行

同一份资料更新任务，可能读到一半被重启，也可能需要系统包生成预览。前者需要保存工作与恢复入口，后者需要工具运行环境。文件、会话和外部结果分别回答不同问题。

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

## `replay: "safe"` 要有工具行为支撑

官方示例把字数统计工具声明为 `replay: "safe"`：相同输入重新计算不会多寄一封信或多扣一笔钱。字段表达重放约定，约定成立仍取决于工具。读取当前时间或不断变化的网页也与纯计算有不同复读含义。[S104]

应用准备一项不可逆动作前，应有稳定的逻辑动作 ID、外部幂等或结果查询；响应丢失后保留[结果未知](../docs/glossary.md#uncertain--结果未知)。恢复工作和重放副作用分别检查，不因为 SDK 保存了 transcript 就自动重做动作。

## 判断是否适合自己的系统

先选一项无私人输入的可重做任务，明确版本、工具权限、持久成果和恢复条件；比较现有实现与 PiHarness 增量。API 变化和实验依赖留在这条实现旁，其他执行路线继续按自己的条件选择。[S105]

本页查阅官方机制，没有安装 SDK、迁移 DO schema、调用模型或进行云端重启实验。实现入口见[官方 Pi 文档](https://developers.cloudflare.com/agents/harnesses/pi/)，已有 Linux 工作空间的解释见[手册](../guides/handbook.md#workspace)。

<!-- SOURCES -->

[S104]: https://developers.cloudflare.com/changelog/post/2026-10-02-pi-harness/ "PiHarness 发布"
[S105]: https://developers.cloudflare.com/agents/harnesses/pi/ "PiHarness 状态与 Lifecycle"
