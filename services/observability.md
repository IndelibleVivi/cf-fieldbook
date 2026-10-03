---
title: 沿着一条请求，找到问题发生的地方
subtitle: Cloudflare Traces、SQL 调查、采样与保留
source_cutoff: 2026-10-03
---

# 沿着一条请求，找到问题发生的地方

一页资料架的搜索昨天很快，今天却要十二秒。先保留请求身份、部署版本、时间范围与路径，比较一条慢请求和一条正常请求；再决定要调查入口、程序还是依赖。这里使用合成问题解释调查方法，没有对实际账户发起查询。

## 请求经过哪里，时间就在哪里分段

Cloudflare Traces 为 open beta，可展示支持范围内的安全规则、转换、缓存、路由、Worker 与源站处理。应用里的分块、权限与模型生成仍需自己的记录；没有看到 span，也可能是未采到或尚未覆盖，不能据此判断该步骤没有发生。[S99]

把本机日志中的请求 ID、部署版本和阶段耗时，与平台的 Ray ID / trace 记录关联。原设备关机时，Tunnel 仍不能替它执行程序；这类故障应与 Worker 已运行但依赖缓慢区别开。调查前先画[请求路线](../guides/handbook.md#routes)，别同时修改所有服务。

## 正常流量少采，调查流量单独采

Trace Rules 可覆盖 baseline sampling。官方配置采用第一条匹配规则，顺序影响结果；可以针对 path、hostname 或临时 header 的流量提高比例，调查结束后恢复正常规则。规则的 Save as Draft 不会启用，Deploy 才改变运行流量。[S101]

平台支持 W3C trace context 与 OTLP 导出。默认拒绝入站 trace context；允许后，传入的 trace 身份仍不证明可信调用者。平台 spans 与自己 instrument 的 spans 可以送到相同 backend，是否保存于 Cloudflare 与是否外送分别选择。[S101]

## 一次查询，先选一份 dataset

SQL API beta 给受支持数据集共同的调查入口。当前每个 statement 只允许一个 dataset、一个 account，并需要时间下界；dataset 的字段、保留期与可查范围各有条件。不要把统一 API 读成已经允许任意跨数据集 JOIN。[S103]

可重复的调查顺序是：选择 dataset 与短时间窗 → 按请求身份定位 → 比较成功与失败 → 查对应版本代码 → 缩小候选原因 → 修复后用同条件复查。API 的字段与查询格式沿[官方查询文档](https://developers.cloudflare.com/analytics/sql-api/query-api/)取得，不猜字段名。[S102]

官方 Observability MCP 可以把有权限的遥测交给 agent；Workers 的 SQL binding 可省一套外部 API client。调查工具的读取资格与改生产配置的权限是两件事，接入前限定账号、时间窗和所需字段。[S98]

## Issues 与 Alerts 接住下一次故障

Workers Issues 将错误与部署版本、源码上下文连起来。Alerts 用持续错误、积压或延迟条件把调查入口递给维护者。通知应带请求线索与可采取的动作；截图与告警本身都不能代替因果验证。[S11] [S12] [S98]

为了重现这个方法，可以在另行获准的测试环境制造一次不含私人输入的慢请求或无害错误，对照成功请求，再检查定向采样与恢复。本文只完成官方机制查阅；没有声称这项云端实验已经执行。

## 费用：当前适用与将来生效

<!-- facts: observability-costs -->
固定资料日期：**2026-10-03**。

| 条款 | Free | Paid |
|---|---|---|
| 当前 Workers Logs [S111] | 200,000 events / 日；3 天 | 20,000,000 events / 月；超出 $0.60 / 百万；7 天 |
| 已公布；将在 2026-12-01 生效 [S100] | 0.5 GB 摄取 / 日；7 天 | 50 GB 摄取 + 12 GB-month / billing cycle；超出 $0.25 / GB + $0.10 / GB-month |
<!-- /facts -->

表格读取同一[费用记录](../catalog/observability-pricing.json)与[公告生效事件](../catalog/launches.json)，固定资料日期为 2026-10-03。Paid 的 12 GB-month 采用 pricing docs；两篇发布博客写 10，差异保留。未采样安全数据集使用另一计价，不消费共享包含量；Enterprise 在合同续约时迁移。[S100]

摄取按压缩前的内容及 attributes 计量，采样会影响摄取与保存；查询、dashboard、alerts 没有额外收费。Free 达到每天摄取限额后停止接收新数据，已有数据在其保留期内仍可查。不要把十二月的公布条款提前写成十月已经适用的账单。[S100]

<!-- SOURCES -->

[S100]: https://developers.cloudflare.com/observability/pricing/ "Cloudflare Observability 价格"
[S101]: https://developers.cloudflare.com/observability/traces/configuration/ "Cloudflare Traces 采样与传播配置"
[S102]: https://developers.cloudflare.com/analytics/sql-api/query-api/ "SQL API 查询"
[S103]: https://developers.cloudflare.com/analytics/sql-api/limits/ "SQL API 限制"
[S11]: https://blog.cloudflare.com/real-time-issue-detection/ "Workers Issues 发布"
[S12]: https://developers.cloudflare.com/workers/observability/issues/ "Workers Issues 文档"
[S98]: https://blog.cloudflare.com/one-observability-platform/ "Cloudflare Observability 新平台发布"
[S99]: https://blog.cloudflare.com/cloudflare-tracing/ "Cloudflare Traces 发布"

[S111]: https://developers.cloudflare.com/workers/platform/pricing/ "当前 Workers Logs 计费"
