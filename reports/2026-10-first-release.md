---
title: Cloudflare 新发布观察 · 2026.10 首发选编
subtitle: 个人开发者与独立创作者参考报告 · 首发选编
edition: 2026.10 · 首发选编 · 选编版
source_cutoff: 2026-10-05
coverage_start: 2026-09-28
coverage_end: 2026-10-05
author: Faye & Cove
github: https://github.com/IndelibleVivi
credits: made by Faye & Cove
status: dated-reference
scope: 混合来源；不含邮件服务；示例不对应私人账户或项目
provenance: 继承 2026-10-02 报告主体、收录 2026-10-03 四组议题、2026-10-05 定点核验；非整篇重新核验
---

# Cloudflare 新发布观察 · 2026.10 首发选编

**2026.10 · 首发选编**  
个人开发者与独立创作者参考报告 · 首发选编 · Faye & Cove

一次运行结束，文件还在。页面关掉，任务能重新接上。报错出现，不必再靠人从日志里拼出故事。这一轮 Cloudflare 发布，把过去需要自己连接的几段工作拉近了。[S04] [S07] [S11]

这份选编从个人使用出发，看新能力能省下什么劳动、适合放在哪里，以及它的开放状态和费用。它在 2026-10-02 报告的主题与深度之上，把 2026-10-03 收录的四组议题（观测与调查、PiHarness、互联网搜索、临时分享）并入相应章节，并在 2026-10-05 对少量可立即核对的事实做了定点检查。具体项目各有历史与约束，文中的场景供读者对照，不是一套必须采用的组合。

> **资料范围**  
> 选编 **不是一次整篇重新核验**，而是三种来源的合成：  
> 1. **继承 2026-10-02 报告主体**：执行环境、维护工具、检索、模型、浏览器与创作、数据服务、费用与开放状态的解释与数字沿用当时来源。  
> 2. **收录 2026-10-03 的四组议题**：Observability / Traces / SQL、PiHarness、Web Search API、Protected Quick Tunnel，按其自身日期并入。  
> 3. **2026-10-05 定点核验**：对严格 Service Token、Tunnel routes 与 connections API 变更、Artifacts 与 Sandbox 的 API 区分等少量条款查阅官方来源并加注，**不代表其余条目在同一天重新核验**。  
> 每处定点核验在正文以“核验于 2026-10-05”标出；未标记者仍按其自身来源日期阅读。截止日表示本次收录的最晚查阅日期。

资料截止 **2026 年 10 月 5 日**，主体覆盖 9 月 28 日至 10 月 2 日的发布，另收录 10 月 2 日公告、10 月 3 日编辑的四组议题；邮件不在本期范围内。决策模型、接入路径与价格的核验范围见[来源说明](../docs/provenance.md)；其余发布信息按各自来源记录阅读。[S01]

> **怎样读这一期**  
> 想试执行环境，读第 2 章；想改善维护与观测，读第 3 章；资料与模型见第 4–5 章；浏览器和创作工具见第 6 章；数据服务见第 7 章；agent 工作状态与执行环境见第 8 章；短期分享见第 9 章。费用、开放状态与申请日期分别在随后几章。使用情境没有默认的“个人最佳技术栈”。

<!-- chapter: changes -->

## 01 / 先看变化，再看产品名

### 执行环境有了下一次

以前，把代码放进一个临时环境，往往意味着运行结束就要重新准备。新的 Containers 快照和 Artifacts 给出了两种不同的延续：一份保存装好依赖的文件环境，一份保存可审查的文件历史。它们让短时执行更容易重复使用，不必顺带成为常驻服务器。[S04] [S05] [S07]

### 平台开始接住维护劳动

`cf` CLI 将资源查询与操作放进更统一的命令入口；Workers Issues 将失败与部署、源码和调用材料关联起来；Traces、SQL API 与统一 Observability 把“留下日志”推进到“沿请求调查”。对独立维护者，最直接的收益可能不是多做一个应用，而是少在控制台和编辑器之间搬一次材料。[S02] [S03] [S11] [S98] [S99]

### 检索与判断变得更专门

AI Search 将图片纳入正式支持的检索路径；Web Search API 把当前互联网检索收进一个经 Gateway 的入口；Clef 则针对有限选项做判断。一个帮助人找回自己的东西，一个帮助程序读外部世界，一个帮助程序选择下一步。它们都值得通过小样本认识，而不是一接入就替换所有模型调用。[S09] [S16] [S106]

### 工作状态与工具环境分开成长

PiHarness 把第三方 harness 的持久 loop 与 inbox 接入 Durable Object SQLite，由 Lifecycle 承接重新唤醒。这给“中断后由谁继续”多了一条具体路线，但它不替代 Sandbox 的工具环境，也不把文件快照变成进程快照。[S104] [S105]

### 变化一览

| 变化 | 原来需要单独拼接的环节 | 现在多出的选择 | 本章 |
|---|---|---|---|
| Containers 快照 / Artifacts | 临时环境结束后重新准备 | 文件基线加可审查文件历史 | 第 2 章 |
| `cf` CLI / Workers Issues / Traces / SQL | 平台与应用记录分散调查 | 按请求定位、定向采样与统一查询 | 第 3 章 |
| AI Search / Web Search API | 各自接检索管线或 provider | 集合检索与互联网检索分列 | 第 4 章 |
| Clef / Jev / AutoRouter | 每个窄判断都写一段生成 | 概率、类别、分数与可换路由 | 第 5 章 |
| Kitesurf / Cloudflare OS / EmDash | 浏览器与创作工具各自为政 | 终端浏览、跨会话工作与可编辑 CMS | 第 6 章 |
| K2 / Basin / KV Instant | 用一种存储承担所有历史 | 事件日志、分析平台与读重型配置分列 | 第 7 章 |
| PiHarness / Sandbox 1.0 | 自己接续 harness 与 DO 生命周期 | 持久工作与工具环境分开成长 | 第 8 章 |
| Protected Quick Tunnel | 临时分享也要安排身份入口 | 短期 URL 加可选邮箱 PIN | 第 9 章 |

本表是编辑判断。手册与主题页已经吸收这批解释；本章保留这一批变化在一个选编里的时间位置，不要求读者从多份补记拼出当前做法。

<!-- chapter: execution -->

## 02 / 能恢复的工作环境

### Containers：把准备工作存下来

9 月 30 日的更新提供了原生 `ctx.container` 控制路线，支持运行时选择已配置的镜像与实例类型，也提供预制系统镜像。需要完整 Linux、编译器或原生依赖的任务，可以据此安排执行环境；普通字段处理和轻量代码，仍可能只需要 Worker 或 Dynamic Worker。[S04] [S59]

**最有价值的是准备昂贵、执行短暂的任务。** 安装依赖、取得特定仓库版本、放好输入样本，有时比检查本身还慢。把这一刻存成基线，下次不必从空目录开始。

快照只保存文件系统，不保存运行进程和内存；它绑定创建时的镜像版本。当前保留期为 30 天，每次恢复刷新期限，暂不支持自定义 TTL，而且需要 `durable_object` 调度。[S05]

<!-- figure: workspace -->

| 希望留下什么 | 用什么保存 | 下次回来得到什么 |
|---|---|---|
| 装好依赖的环境 | 容器文件系统快照 | 文件和环境基线，不是暂停中的进程 |
| 源码、文档的变化 | Artifacts 或现有 Git 仓库 | 可比较的版本历史 |
| 导出文件与媒体 | R2 等对象存储 | 独立于运行环境的产物 |
| 任务完成到哪一步 | 应用状态记录 | 能据此决定如何继续的事实 |

*这是一种职责划分建议，表中的载体并非必须全部采用。*

### Sandbox 1.0：迁移时看行为，不只改包名

1.0 路线由应用编写 Durable Object，通过 `this.ctx.container` 控制环境；`exec()` 接收参数数组，默认不经过 shell，每次调用独立指定工作目录与环境。旧版的持久 shell session、镜像自带工具和生命周期假设不能直接照搬。[S72]

旧 Containers 类与旧 Sandbox SDK 的维护计划节点为 **2026-12-31**。这是迁移需要关注的日期，不是所有旧部署会在当天停止工作的声明。[S04] [S72]

### Artifacts：工作结束以后，文件继续存在

Artifacts 提供 Git 协议和可编程仓库接口，支持创建、分叉及按仓库授权。文件变化可以接入事件订阅，也可与 Workers Builds 组合。它适合留住临时 workspace 产生的成果；人的审阅、正式源码的接受决定和已有协作入口仍可以留在原处。[S07]

一个轻量试法是从同一基线开出两份环境，对同一问题做两个方案，交回补丁、测试结果与产物。比较结束再决定保留哪份文件，而不是先搭一套远程开发平台。

### 一个容易漏看的更新

10 月 1 日的 Durable Objects 更新，让部分等待中的 RPC、容器监视和其他操作在客户端断开后继续阻止空闲回收。兼容日期为 `2026-10-01` 或更晚时默认启用；单项待完成操作最多获得 15 分钟的保活保护，期间仍产生时长费用。它减少中断，但不是跨崩溃恢复机制。[S70]

<!-- chapter: observability -->

## 03 / 少搬一次日志，少猜一个版本

### `cf` CLI：先从看清账户开始

新的 `cf` CLI 已进入公开 beta，提供覆盖更广控制面的命令、搜索和 JSON 输出。现有 Wrangler 项目可以先使用资源命令，不必立即转换全部配置。Wrangler 计划至少维护到 `cf` GA 后 18 个月，目前无需为了尝鲜集体迁移。[S02] [S03]

个人使用可以从只读盘点开始：有哪些 Worker，分别绑定什么资源，哪个版本正在服务哪个入口。等这些关系能被稳定查询，再考虑自动化修改。

### Workers Issues：让一个错误带着上下文到来

Issues 可以聚合同类失败，并关联调用、部署及源码材料，再通过 webhook 或其他集成交给后续工具。公开 beta 期间免费，面向所有 Workers 账户，只处理启用后的新流量。[S11] [S12]

第一次接入，建议让它产出一份调查材料：什么时候发生、对应哪个版本、怎样复现、已有测试是什么。修复仍通过原来的审阅与发布路径。这样先省掉搬运劳动，再决定是否扩大自动化。

使用 Wrangler 时需要 **4.134.0 或更高版本**，并把 `observability.issues.enabled` 写进配置；只在控制台打开，下一次部署可能覆盖。它也不会自动看到没有进入 Worker 的本机脚本或第三方故障。[S12]

### Traces 与 SQL API：从留下日志，到沿请求调查

Traces open beta 把支持的规则、缓存、路由、Worker 与源站处理放进请求时间线；Trace Rules 可单独提高调查流量的采样。SQL API beta 为多种 dataset 提供共同入口，当前仍是每条 statement 一个 dataset，并需要下界时间条件。[S98] [S99] [S102] [S103]

实际选择可以先从一个慢请求开始，保留请求身份与版本，比较正常请求，再决定需不需要接 MCP 或外部 OTLP backend。统一接口降低调查接入成本，应用内部的阶段记录和因果验证仍要自己完成。本文没有进行生产调查实验；完整条件见[当前主题](../services/observability.md)。

### CI：交回能看的结果

Workers Builds 在 Paid 下包含每月 6,000 构建分钟、6 路并发，单次构建仍限 20 分钟。它适合 Worker 和前端的检查、构建与发布，不是通用 macOS／Windows runner。[S35]

比增加一条“构建成功”通知更有用的，是交回一个隔离预览、固定输入下的操作过程，以及导出后能重开的样本。前端的结果应该能看、能按、能比较。

Preview URL 与数据隔离要分别确认。当前 DO 和 Containers 有自动隔离支持；D1、R2、KV、Queues、Vectorize 等若仍指向同一资源，预览会共享相应数据。[S63]

<!-- chapter: retrieval -->

## 04 / 让搜索找回一张图

### AI Search GA 带来的实际变化

10 月 1 日，AI Search 正式发布，支持通过多模态 embedding 索引图片像素；纯文本 embedding 也可使用图片描述路线。两者不是同一种视觉检索。扫描 PDF 可使用 OCR，音频和视频直接摄取仍是后续方向。[S09]

个人资料里经常有这样的东西：记得大致布局，却忘了文件名的截图；记得一句意思，却想不起用词的文章；只有扫描件的材料。对这些输入，先让搜索返回原件与定位，比立即生成一段总结更容易判断质量。

例如，查“主体偏左、文字沿轮廓走的构图”，再放入一张颜色相近、布局不同的反例。这比单查“蓝色海报”更能看出搜索是否理解了关系。文档查询也应包含旧版本和找不到答案的情况。

### 适合省掉什么，不适合省掉什么

AI Search 可以省去一部分分块、索引与检索维护。权限较简单的资料集合，适合先用小样本试。复杂撤回、严格版本控制和自定义混合排序，则可能更适合保留自己的状态库与检索管线。

当前限制也值得提前看：纯文本／代码和启用 OCR 的 PDF 可到 10 MiB；未启用 OCR 的 PDF 及其他受支持格式仍为 4 MiB。自定义元数据字段限 5 个，字符串的可过滤索引覆盖前 64 个 UTF-8 字节。复杂权限不能只靠把一个很长的规则字符串塞进 metadata。[S10]

### 搜索入口统一，证据来源仍有区别

Web Search API beta 经 AI Gateway 搜当前互联网；AI Search 仍面向交给它的集合。应用可从一个 facade 选择 provider，但先读回来源，才能知道摘要有没有漏掉日期和适用条件。[S106]

Provider 表当前将 Exa ZDR 标为 No，而公告称三者均支持；具体差异、费用与响应形式集中在[检索主题](../services/search.md)。没有 provider benchmark，也没有把价格排名当效果排名。[S107]

### 11 月开始采用新账单

新计费自 **2026-11-01**生效，每账户每月包含 500 万摄取 token、10 GB·月存储、1,000 次语义类查询和另 1,000 次全文查询。语义、向量与混合查询属于同一计量组。[S10]

| 超出包含量的项目 | 标价 | 计算时记住 |
|---|---|---|
| 基础摄取 | $0.75／百万 token | 分块重叠重复计入 |
| 图片处理 | 另加 $0.50／百万 token | 与基础摄取共享 500 万额度 |
| 存储 | $2／GB·月 | 不是普通 R2 的单价 |
| 语义类查询 | $0.75／千次 | 不按每个索引另送额度 |
| 全文查询 | $0.10／千次 | 与语义额度分开 |

内部 Workers AI embedding、重排、存储、向量索引与网站抓取已纳入 AI Search；生成答案、查询改写和外部模型仍可能单独计费。不要继续套用旧 beta 账单。[S09] [S10]

<!-- chapter: models -->

## 05 / 有时只需要一个选择

### Clef 与 Jev：先区分模型，再比较入口

这类模型接收 `state` 与有限的 `questions`，直接返回概率、类别或分数。它们适合把“读一段材料、做一个窄判断”从长篇生成中分离出来；不是替整个任务写报告的聊天模型。[S16] [S76]

Cloudflare 自己托管 Clef 与 Clef-flash，也在第三方模型目录中提供 `typesafe/jev`。后者仍属于 TypeSafe 的模型路线，不能把“通过 CF 调用”写成“在 CF 上运行同一套自有模型”。[S17] [S18] [S73]

| 模型／接入 | 输入单价，美元／百万 token | 主要区别 |
|---|---:|---|
| Jev，经 CF | 0.042 | TypeSafe 第三方模型；纯文本判断 |
| Clef-flash | 0.09 | CF 托管；9B；支持图片扩展 |
| Clef | 0.24 | CF 托管；27B；支持图片扩展 |

以上是模型标价，不含充值费、Worker、日志与重试。CF Unified Billing 购买 credits 另收 5%；Workers Paid 的固定费用不等于第三方模型额度。[S73] [S17] [S18] [S80]

上下文不能只写“64k 对 32k”：Clef 两款目录列 65,536；Jev 原厂允许总请求 64k，但 `state + 最长单题` 不超过 32k，CF 与 OpenRouter 的 Jev 目录则标 32,000。应按所选入口限制输入。[S17] [S18] [S74] [S75]

这也不是一个总分即可解决的选择。CF 自测中，Clef 在部分分类指标领先，但 Jev 在 When2Call 与 BRIGHT 两项高于两款 Clef；这些是供应商的实验结果，不是本手册的实测。窄任务先用自己的材料，比较同等错误风险下能自动处理多少，才有工程意义。[S16]

完整的供应路径、费用演算、兼容差异与试验设计，见本资料包的《Clef 与 Jev：模型、入口与判断成本》。配套强化学习目前仍采用设计合作形式，不是普通 Paid 账户默认开放的自助训练。[S16]

### AutoRouter：只在可以换模型的地方换

AI Gateway 的 `cloudflare/auto` 可以在允许的候选模型中路由。beta 期间路由本身免费，实际推理照常计费。可替换的小任务适合试；固定底模的实验或需要稳定行为的会话，应保留明确选择。[S13]

User Insights 则帮助查看流经 Gateway 的调用归属、模型与费用，功能本身免费。它不能看见绕过 Gateway 的调用，异常标记也不会自动阻止请求。[S14]

先看清现有开销，再决定哪些任务值得自动选模型，是更容易解释变化的一种顺序。

> **日志也有自己的价格边界**  
> 首次创建 Gateway 在 2026-09-24 或之后的账户，日志走 Workers Logs 规则；更早客户仍有 Legacy Logs。Unified Billing 充值另收 5%。路由免费、日志免费和推理免费是三件事。[S15]

<!-- chapter: browser -->

## 06 / 浏览器与创作工作台

### Kitesurf：网页进入终端

这次 Kitesurf 更新加入更多网页兼容能力、WebMCP 和终端交互。支持 Kitty 图像协议的终端能显示页面，其他环境有 ANSI 回退，并可回传点击与滚动。当前仍是 beta，开源尚在计划中。[S19]

它适合独立体验：读公开网页、看 agent 所见的页面，或试一个终端交互。若最终用户使用 Safari、Chrome 或手机浏览器，产品验收仍应回到那些实际环境。

### Cloudflare OS：看工作怎样跨会话延续

已有自部署开源版本；10 月 1 日新增的是托管候补，以及仓库、外部工具和导出能力改进。全托管版本还不能视为每个账户已可使用的套餐功能。[S20]

值得借鉴的是文件、授权和长任务怎样组织，人离开后又如何回到工作现场。自部署仍要计算底层存储、推理与维护，不必为了研究它就把关键工作迁过去。

### EmDash：生成之后，还能继续编辑

EmDash 1.0 是基于 Astro 的稳定 CMS，提供插件与管理能力；EmDash Build 则是另一个 alpha 项目：在 Sandbox 中生成网站，以 Artifacts 留下文件变化，最终形成能继续管理的站点。[S21]

对独立作者，重点是内容能否继续编辑、导出和发布；对开发者，可以分别研究 CMS 与生成器。它们不要求读者同时接受同一套工作方式。

<!-- chapter: data -->

## 07 / 三种名字很新、用途很不同的数据服务

### K2：消息处理完，还需要重新读吗？

K2 是带保留期的事件日志，允许不同消费者从各自位置读取和重放。公开 beta 需要 Workers Paid，当前账户可存 10 GB，常规保留上限为 30 天，更长保留需申请。[S22] [S23]

选择点在于历史是否要反复使用。只有一个程序稍后生成缩略图，队列通常更直接；索引、分析与修复程序需要独立回放同一历史时，事件流才有更具体的位置。其有序性仍要结合分区、确认位置和自己的业务关系理解。[S22]

### Basin：面向分析，不是替换每一个数据库

Basin 将 Pipelines、Catalog 与 SQL 整合成正式的数据分析平台，基于 R2 与 Apache Iceberg。已有相应资源可继续工作，名称与接口逐步迁移。[S24] [S33]

较大的事件历史或实验批次值得研究；少量文件和 SQLite 已经够用时，不必为了“有数据”而引入数据湖。分析查询与日常事务状态各有职责。

### KV Instant：先看写入单价

KV Instant 面向小体量、极少写入、极大量读取的配置，目前为私有 beta。它的账单与普通 KV 差别很大：**读取 $0.20／百万次，写入、删除和列举 $0.10／次，存储 $100／MB·月。**[S25]

1,000 次 Class A 操作就是 $100。它不是普通笔记库、聊天历史或频繁变化的任务状态的便宜替代品；名字相近，不能沿用估价。

<!-- chapter: agents -->

## 08 / Harness 状态与 Linux 环境分开成长

### 工作状态、执行环境与文件历史是三件事

同一份资料更新任务，可能读到一半被重启，也可能需要系统包生成预览。前者需要保存对话、未完成工作与下一步；后者需要工具运行环境；两者的产物还要有可继续比较的文件历史。这三件事不能靠一张磁盘快照互相代替，也不能靠仓库的文件来冒充进程状态。[S104] [S105]

### PiHarness 多了一条具体实现路线

PiHarness 为 beta，Pi Durable 为 experimental。Pi 的持久 loop 与 inbox 接入 DO SQLite，Lifecycle 承接重新唤醒；这给第三方 harness 增加了具体云端路线，并不替代 Sandbox 工具环境或既有任务系统。[S104] [S105]

官方 `replay: "safe"` 示例是字数计算。对不可逆动作，继续检查外部幂等与结果查询；不能把工作可恢复读成副作用可任意重放。Clef/Jev 的模型比较不因这条 harness 新闻而变成错误资料。

### 同一个工作区，先核对 SDK 版本

Artifacts 保存可比较的文件历史；Sandbox 提供 Linux 工具环境；PiHarness 或任务系统记录未完成工作。可以为每个任务建立独立仓库，向获准的运行会话发短期、限仓库的写入 token，再把补丁和产物交回审阅。Workers Builds 与 Preview 需要明确配置，推送文件不会自动等于测试通过或接受成果。[S07] [S114]

当前 Artifacts 的 Sandbox 组合示例仍使用旧版 Sandbox SDK；它和 1.0 迁移文档展示的是不同代的运行接口。下面这些名字都属于 **Sandbox 一侧**，不是 Artifacts 的仓库 API。核验于 2026-10-05。[S114] [S115]

| 组合示例中的旧版 Sandbox SDK | Sandbox SDK 1.0 迁移路线 |
|---|---|
| 示例模板固定在 `#v0` | 应用编写自己的 Durable Object |
| `getSandbox()` 取得实例 | 用 `this.ctx.container` 控制环境 |
| `setEnvVars()` 配置环境 | 每次命令明确环境与工作目录 |

1.0 命令使用参数数组，默认不经过 shell；新镜像未必包含旧镜像的全部工具。旧进程不会因 Worker 更新自动替换，容器文件系统快照也不保存进程与内存。迁移时要核对生命周期，不能把两代 API 拼进同一段代码。[S05] [S72]

### 一条判断顺序

先问要留下的是文件、进程、任务状态还是外部结果，再选载体：需要历史的文件放 Artifacts 或现有 Git；需要完整 Linux 的工具环境用 Sandbox 1.0 / Containers；未完成的 agent 工作交给 harness 的持久状态与任务系统。Artifacts 的文件变化不与容器进程或任务状态自动合并，需要自己定义衔接。

<!-- chapter: sharing -->

## 09 / 短期分享不用先变成长服务

### Protected Quick Tunnel：临时分享也要安排身份入口

已经在本机打开的小资料架，只想给两位朋友看，可以先用 Protected Quick Tunnel 的邮箱 PIN，不必先配正式域名。`--allowed-mail` 是可选限制；没有它的普通 Quick Tunnel 仍向拿到 URL 的人开放。[S109] [S110]

```bash
cloudflared tunnel --url http://localhost:8080 --allowed-mail 'alice@example.com,bob@example.com'
```

停止连接器后访问结束。这适合短期 demo；电脑关机或 `cloudflared` 停止后，访问也停止。既有本机服务可以先分享，之后再决定长期域名、Access 和运行位置。[S109]

这是供读者另外执行的网络命令，本仓库没有启动 Tunnel；检查路径见[临时分享](../use-cases/temporary-sharing.md)。Quick Tunnel 面向测试与开发，没有 SLA，当前最多 200 个并发请求，也不支持 SSE。需要长期 hostname、SSE 或稳定运行时，采用正式 Tunnel 与相应 Access / 应用权限；公开静态资料可直接采用静态托管。[S110]

### 长期入口照旧走 Access 与命名 Tunnel

`cloudflared` 主动连接 Cloudflare，再把指定 hostname 的请求送到原应用；它不替原设备运行程序，不备份磁盘。拿到可信身份之后，应用继续决定角色、资源和动作。[S47] [S48]

对机器客户端，Service Tokens 能避免模拟网页登录；严格模式下它的行为有单独约束，见[手册服务令牌章](../guides/handbook.md#access)的定点说明。核验于 2026-10-05。私人服务的替代入口（默认开发域名、其他 Custom Domain、预览地址、源站直连）仍需逐个列出，保护一个域名不会自动证明另一条路也安全。[S49] [S116]

私网路由维护脚本还需核对 2026-10-05 的 API 移除：CIDR 编入 URL 的旧 route 端点退场，Tunnel／Mesh 查询中的内嵌 `connections` 字段改由专用端点取得。这与普通 HTTP ingress 是不同的维护范围，具体路径见[实施参考](../reference/implementation.md#私有路由与连接维护api-变更核验于-2026-10-05)。核验于 2026-10-05；未调用账户接口。[S117]

<!-- chapter: economics -->

## 10 / 把费用放回使用过程

### $5 是起点，不是整个账单

Workers Paid 最低为每账户每月 $5，相应包含量由多个项目共用。浏览器、容器、模型、存储和日志有各自的计量单位。先算工作量，再扣一次共享包含量，比为每个小项目单独套一份“免费额度”更可靠。[S34]

| 常用资源 | 本期记录的包含量 | 主要观察项 |
|---|---|---|
| Workers Paid | 1,000 万请求；3,000 万 CPU 毫秒／月 | 动态请求、实际 CPU [S34] |
| Workers Builds | 6,000 分钟；6 路并发／月 | 重复构建、单次 20 分钟上限 [S35] |
| Containers | 25 GiB·小时内存；375 vCPU·分钟；200 GB·小时磁盘／月 | 启动到关闭的总时长 [S06] |
| Browser Run | 10 浏览器小时／月 | 会话时长、并发 [S36] |
| R2 Standard | 10 GB·月；100 万 Class A；1,000 万 Class B | 文件体量、对象操作 [S38] |
| Vectorize Paid | 5,000 万查询维度；1,000 万存储维度／月 | 条目数还要乘维度 [S40] |
| Workers AI | 每天 10,000 Neurons | 模型之间消耗不同 [S41] |
| Observability（已公布，12-01 生效） | Paid 50 GB 摄取 + 12 GB-month／billing cycle | 未采样安全 dataset 不共享额度 [S100] |

R2 使用自己的免费层；Workers AI 的日额度也不是 Paid 独占。以上不是该账户尚余多少额度的证明。Observability 新版计费自 **2026-12-01** 起适用，此条沿用 2026-10-03 的来源核验范围，在 10 月 5 日选编时仍属未来生效条款；Paid 公布 50 GB 摄取与 12 GB-month 保存包含量，超出为 $0.25 / GB 与 $0.10 / GB-month，Enterprise 在续约时迁移。发布博客写 10 GB-month，当前 pricing docs 写 12，本篇采用文档并保留差异。[S98] [S100]

### 同一个两分钟任务，可以产生不同账单

假设每月 100 次任务，每次执行两分钟，规格为 4 GiB 内存、0.5 vCPU、8 GB 磁盘。若任务结束立即关闭，合计约 13.33 GiB·小时内存、最多 100 vCPU·分钟、26.67 GB·小时磁盘，在当前容器包含量内。[S06]

若每次多空闲十分钟，总内存时间变成 80 GiB·小时，磁盘变成 160 GB·小时。多出的 55 GiB·小时内存按当前单价约 **$0.495**；CPU 不应把空闲时间也按满载算。例子未计模型、DO、网络与日志。[S06]

<!-- figure: runtime-cost -->

| 每次任务的生命周期 | 每月运行时长 | 每月内存用量 |
|---|---:|---:|
| 执行 2 分钟后关闭 | 3.33 小时 | 13.33 GiB·小时 |
| 执行 2 分钟，再空闲 10 分钟 | 20 小时 | 80 GiB·小时 |

*同一规格、同一任务数的示例演算；不是真实账户用量。*

另外两笔可复算的例子：11 月 AI Search 新计费下，600 万纯文本摄取 token、2 GB·月、3,000 次语义查询、500 次全文查询，且没有图片处理与生成，超额合计 **$2.25**；Artifacts 每月 20,000 次操作、3 GB·月，超额合计 **$2.50**。[S10] [S08]

### 把这些日期留在日历里

| 日期 | 变化 | 需要做的事 |
|---|---|---|
| 2026-09-24 起 | 新 Gateway 客户日志规则变化 | 看首次 Gateway 创建日期 [S15] |
| 2026-10-14／15 | Artifacts 计费日期有一天官方冲突 | 价格页写 14 日，博文写 15 日；预算按较早日准备 [S07] [S08] |
| 2026-11-01 | AI Search 新计费 | 重新估摄取、查询与额外模型费 [S10] |
| 2026-12-01 | 统一 Observability 新计费 | Paid 按 50 GB 摄取 + 12 GB-month，超出另计 [S100] |
| 2026-12-31 | 旧容器类／Sandbox SDK 维护节点 | 安排迁移验证，不解释为当日停机 [S04] |
| `cf` GA 后至少 18 个月 | Wrangler 计划维护期 | GA 日期未定，不猜具体停用日 [S02] |

账单提醒用于发现趋势；真正限制开销，还要靠任务截止时间、最大并发、调用次数和数据保留期。提醒不等于自动封顶。

<!-- chapter: adoption -->

## 11 / 发布状态速查

GA 表示该产品正式发布；不意味着相关的 SDK、托管版和地区全部同步开放。下面保留各自状态，便于回查。

### 可以调用、安装或进入公开测试

| 能力 | 本期状态与入口 | 来源 |
|---|---|---|
| `cf` CLI | 公开 beta，可与现有 Wrangler 项目并行使用资源命令 | [S02] [S03] |
| Workers Issues | 公开 beta；配置启用后处理新流量 | [S12] |
| Cloudflare Traces / SQL API | open beta / beta；dataset 与账号条件分别核对 | [S99] [S103] |
| Containers／快照 | 新调度为公开 beta 路线；Paid；快照需 DO 调度 | [S04] [S05] |
| Sandbox SDK 1.0 | 新接口与迁移文档已提供；底层仍有 beta 状态 | [S59] [S72] |
| Artifacts | 公开 beta，Paid | [S07] [S08] |
| AI Search | GA，11 月新计费 | [S09] [S10] |
| Web Search API | 公开 beta；经 AI Gateway，需 credits 或 provider key | [S106] [S107] |
| Clef／Clef-flash | Workers AI 模型可调用 | [S17] [S18] |
| AutoRouter／User Insights | 路由 beta；使用分析已开放 | [S13] [S14] |
| PiHarness／Pi Durable | beta / experimental | [S104] [S105] |
| Kitesurf | beta，Playground／终端 | [S19] |
| EmDash 1.0／Build | CMS 稳定版／生成器 alpha | [S21] |
| K2／Basin | 事件流公开 beta／分析平台 GA | [S23] [S24] |
| Protected Quick Tunnel | 可选 `--allowed-mail`；无 SLA | [S109] [S110] |

### 申请、候补与其他值得留意的发布

Cloudflare OS 托管版候补、KV Instant 私有 beta、Clef 强化学习设计合作及 Monetization Gateway 封闭 beta，各有独立申请条件。Monetization Gateway 使用 HTTP 402 为 API／MCP 等访问计费，当前面向符合条件的美国卖家；登记候补不等于已经得到可用服务。[S20] [S25] [S16] [S30]

其他发布可按现有技术栈选择：Workers OAuth Provider v1 提供授权与资源服务拆分等能力；Rust／Emscripten 扩大运行时实验；Forge 从 API 规范生成可维护接口；Vinext 1.0 面向 Next.js 的 Vite 迁移；Threat Signals 提供一个安全情报 RSS 的免费分析入口、最长保存 30 天。[S71] [S26] [S27] [S28] [S29]

Registrar 的程序化入口，以及 Workers 的 ML-KEM／ML-DSA opt-in 接口，也在本轮发布范围内。搜索域名不等于授权购买，实验密码接口不等于整套系统已完成后量子迁移。企业功能、研究原型与申请中的 CA 不作为个人套餐现成福利计算。[S01] [S33]

### 一次核验的边界

选编中的 URL 与日期是编辑时查阅的记录，不是访问时自动重测；正文标“核验于 2026-10-05”的仅限该处条款。开放状态可能在阅读时已改变，涉及预算或生产前应重新查看对应官方页面。

<!-- chapter: programmes -->

## 12 / 申请与比赛，先读条件

**Git 平台比赛**的截止为 **2026-10-14 23:59 PDT**。正式规则要求美国或加拿大合法居民、起始时满 18 岁，使用 Workers 与 Artifacts，支持多个 agent 并行工作，并提交源码、运行说明及 5–10 分钟演示。源码许可限 MIT、Apache-2.0 或指定 BSD；第一名的 $25,000 是 Cloudflare credits，不是现金。现场展示和其他条件仍应读完整规则。[S32]

**The Cold Start**面向位于美国或加拿大、融资少于 $1,000 万的早期创业公司，申请截止日期为 **2026-10-02**，奖项为 $500,000 Cloudflare credits。选编于 2026-10-05 编辑，原公布截止日已过，未核实延期；这里保留历史条件，不作当前开放推荐。[S31]

对多数个人试验，公开入口上的一次完整使用已经足以积累判断。是否改许可证、经营商业项目或参加比赛，应与作品计划有关，不必由 credits 金额决定。

<!-- chapter: scenarios -->

## 13 / 使用场景，不是项目处方

每个人的项目、数据和维护习惯不同。以下只是编辑提出的试验情境，没有云端实测结论，也不是一套推荐组合。

**想少搬一次日志。** 用一个测试 Worker 的无害失败，检查 Issues 能否连起错误、版本与复现材料；再从一个实际慢请求开始，比较正常与异常请求，判断 Traces 是否足以定位，还是要接应用内阶段记录。先减少调查准备，自动修复和自动发布以后分别决定。

**想找回自己的视觉材料。** 选 30–50 张获准使用的图，保留来源，用真实查询比较多模态与图片描述。加入颜色相似、构图不同的反例，判断是否真的找回了原件。

**想比较两种实现。** 从同一文件基线开两份环境，交回补丁、可运行结果和同样的检查。关闭后再恢复一次，看准备是否更快、成果是否更易比较，而不先搭完整平台。

**想替掉一小段重复判断。** 让 Clef-flash 先只给分类建议，写清误判代价，允许无法判断，再和规则或已有模型比较。

**想让 agent 中断后继续。** 选一个无私人输入的公开任务，比较现有任务系统与 PiHarness 的增量：谁保存未完成工作、谁在中断后唤醒、不可逆动作如何防止重放。

**想只给指定的人看一份 demo。** 先在本机确认页面，再用 `--allowed-mail` 分享；试允许邮箱、另一个不允许的邮箱，再停止连接器确认入口失效。需要长期可用时再换命名 Tunnel 与 Access。

<!-- SOURCES -->

## 来源索引

本篇为混合来源选编：主体沿用 2026-10-02 的核验范围；Observability、PiHarness、Web Search API 与 Protected Quick Tunnel 四组议题 沿用 2026-10-03 的核验范围；严格 Service Token、Tunnel routes 与 connections API 变更、Artifacts 与 Sandbox 的 API 区分于 **2026-10-05** 定点查阅官方来源。**这不是一次整篇重新核验**；未标注点日期者按其自身来源日期阅读。本节来源定义与本书目共存，构建时不被 catalog 覆盖。资料查阅不等于账户、模型或云端实测。

- **[S01]** · Birthday Week 2026 发布总览
- **[S02]** · cf CLI 发布
- **[S03]** · cf CLI 文档
- **[S04]** · Containers 新运行接口与 Sandbox
- **[S05]** · Containers 文件系统快照
- **[S06]** · Containers 价格
- **[S07]** · Artifacts 公开测试发布
- **[S08]** · Artifacts 价格
- **[S09]** · AI Search GA
- **[S10]** · AI Search 限制与价格
- **[S11]** · Workers Issues 发布
- **[S12]** · Workers Issues 文档
- **[S13]** · AutoRouter 发布
- **[S14]** · AI Gateway User Insights
- **[S15]** · AI Gateway 价格与日志
- **[S16]** · Clef 与强化学习平台发布
- **[S17]** · Clef 模型卡
- **[S18]** · Clef-flash 模型卡
- **[S19]** · Kitesurf 更新
- **[S20]** · Cloudflare OS 托管候补
- **[S21]** · EmDash 1.0 与 EmDash Build
- **[S22]** · K2 发布
- **[S23]** · K2 文档
- **[S24]** · Basin GA
- **[S25]** · KV Instant 私测与价格
- **[S26]** · Rust Emscripten target
- **[S27]** · Forge 生成工具链
- **[S28]** · Vinext 1.0
- **[S29]** · Threat Signals
- **[S30]** · Monetization Gateway 封闭测试
- **[S33]** · 开发者平台 Changelog
- **[S34]** · Workers 价格
- **[S35]** · Workers Builds 限制与价格
- **[S36]** · Browser Run 价格
- **[S38]** · R2 价格
- **[S40]** · Vectorize 价格
- **[S41]** · Workers AI 价格
- **[S47]** · Cloudflare Tunnel
- **[S48]** · Access JWT 验证
- **[S59]** · Sandbox SDK
- **[S63]** · Workers 预览资源隔离
- **[S70]** · Durable Objects pending I/O 保活
- **[S71]** · Workers OAuth Provider v1
- **[S72]** · Sandbox SDK 1.0 迁移差异
- **[S73]** · Jev：Cloudflare 第三方模型目录
- **[S74]** · TypeSafe：Jev 版本、价格与上下文预算
- **[S75]** · OpenRouter：Jev 1.13 价格与供应商
- **[S76]** · OpenRouter：Jev 的两种接口
- **[S80]** · Cloudflare AI Gateway：Unified Billing
- **[S98]** · Cloudflare Observability 新平台发布
- **[S99]** · Cloudflare Traces 发布
- **[S100]** · Cloudflare Observability 价格
- **[S102]** · SQL API 查询
- **[S103]** · SQL API 限制
- **[S104]** · PiHarness 发布
- **[S105]** · PiHarness 状态与 Lifecycle
- **[S106]** · Web Search API 发布
- **[S107]** · Web Search API providers
- **[S109]** · Protected Quick Tunnels 发布
- **[S110]** · Quick Tunnel 邮箱限制与开发边界
- **[S114]** · Artifacts：Sandbox SDK 示例
- **[S115]** · Sandbox SDK 1.0：替换 Sandbox 类

- **[S31]** · The Cold Start

- **[S32]** · Git 平台比赛正式规则

- **[S49]** · Access Service Tokens

- **[S116]** · Access 严格 Service Token 认证

- **[S117]** · Tunnel routes 与 connections API 变更

## 关于这一版

这是面向个人使用的独立参考资料，不是 Cloudflare 官方出版物。产品事实保留来源，场景与判断属于编辑分析。本篇为 2026-10-02 报告与 2026-10-03 观察的选编与整合，不做全篇重新核验。本次未进行账户操作或云端部署。

GitHub：[github.com/IndelibleVivi](https://github.com/IndelibleVivi)  
*made by Faye & Cove*

[S01]: https://www.cloudflare.com/birthday-week/ "Birthday Week 2026 发布总览"
[S02]: https://blog.cloudflare.com/cloudflare-cf-cli-launch/ "cf CLI 发布"
[S03]: https://developers.cloudflare.com/cf/ "cf CLI 文档"
[S04]: https://blog.cloudflare.com/faster-agent-sandboxes/ "Containers 新运行接口与 Sandbox"
[S05]: https://developers.cloudflare.com/containers/guides/snapshots/ "Containers 文件系统快照"
[S06]: https://developers.cloudflare.com/containers/platform/pricing/ "Containers 价格"
[S07]: https://blog.cloudflare.com/next-git-platform-on-cloudflare/ "Artifacts 公开测试发布"
[S08]: https://developers.cloudflare.com/artifacts/platform/pricing/ "Artifacts 价格"
[S09]: https://blog.cloudflare.com/ai-search-ga/ "AI Search GA"
[S10]: https://developers.cloudflare.com/ai-search/platform/limits-pricing/ "AI Search 限制与价格"
[S11]: https://blog.cloudflare.com/real-time-issue-detection/ "Workers Issues 发布"
[S12]: https://developers.cloudflare.com/workers/observability/issues/ "Workers Issues 文档"
[S13]: https://blog.cloudflare.com/auto-router/ "AutoRouter 发布"
[S14]: https://developers.cloudflare.com/ai-gateway/observability/user-insights/ "AI Gateway User Insights"
[S15]: https://developers.cloudflare.com/ai-gateway/reference/pricing/ "AI Gateway 价格与日志"
[S16]: https://blog.cloudflare.com/clef-decision-models/ "Clef 与强化学习平台发布"
[S17]: https://developers.cloudflare.com/workers-ai/models/clef/ "Clef 模型卡"
[S18]: https://developers.cloudflare.com/workers-ai/models/clef-flash/ "Clef-flash 模型卡"
[S19]: https://blog.cloudflare.com/kitesurf-update/ "Kitesurf 更新"
[S20]: https://blog.cloudflare.com/managed-cloudflare-os/ "Cloudflare OS 托管候补"
[S21]: https://blog.cloudflare.com/emdash-cms-plugin-registry/ "EmDash 1.0 与 EmDash Build"
[S22]: https://blog.cloudflare.com/cloudflare-k2-streams/ "K2 发布"
[S23]: https://developers.cloudflare.com/k2/ "K2 文档"
[S24]: https://blog.cloudflare.com/cloudflare-basin/ "Basin GA"
[S25]: https://blog.cloudflare.com/workers-kv-instant/ "KV Instant 私测与价格"
[S26]: https://blog.cloudflare.com/rust-workers-emscripten-target/ "Rust Emscripten target"
[S27]: https://blog.cloudflare.com/forge-open-source-generation-pipeline/ "Forge 生成工具链"
[S28]: https://blog.cloudflare.com/vinext-nextjs-on-vite/ "Vinext 1.0"
[S29]: https://blog.cloudflare.com/threat-signals/ "Threat Signals"
[S30]: https://blog.cloudflare.com/monetization-gateway-beta/ "Monetization Gateway 封闭测试"
[S33]: https://developers.cloudflare.com/changelog/product-group/developer-platform/ "开发者平台 Changelog"
[S34]: https://developers.cloudflare.com/workers/platform/pricing/ "Workers 价格"
[S35]: https://developers.cloudflare.com/workers/ci-cd/builds/limits-and-pricing/ "Workers Builds 限制与价格"
[S36]: https://developers.cloudflare.com/browser-run/pricing/ "Browser Run 价格"
[S38]: https://developers.cloudflare.com/r2/pricing/ "R2 价格"
[S40]: https://developers.cloudflare.com/vectorize/platform/pricing/ "Vectorize 价格"
[S41]: https://developers.cloudflare.com/workers-ai/platform/pricing/ "Workers AI 价格"
[S47]: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/ "Cloudflare Tunnel"
[S48]: https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/ "Access JWT 验证"
[S59]: https://developers.cloudflare.com/sandbox/ "Sandbox SDK"
[S63]: https://developers.cloudflare.com/workers/previews/resources/ "Workers 预览资源隔离"
[S70]: https://developers.cloudflare.com/changelog/post/2026-10-01-pending-io-keep-alive/ "Durable Objects pending I/O 保活"
[S71]: https://developers.cloudflare.com/changelog/post/2026-10-01-workers-oauth-provider-1x/ "Workers OAuth Provider v1"
[S72]: https://developers.cloudflare.com/sandbox/sdk/migrate/changes-in-1-0/ "Sandbox SDK 1.0 迁移差异"
[S73]: https://developers.cloudflare.com/ai/models/typesafe/jev/ "Jev：Cloudflare 第三方模型目录"
[S74]: https://docs.typesafe.ai/models "TypeSafe：Jev 版本、价格与上下文预算"
[S75]: https://openrouter.ai/typesafe/jev-1.13/ "OpenRouter：Jev 1.13 价格与供应商"
[S76]: https://openrouter.ai/docs/guides/community/jev "OpenRouter：Jev 的两种接口"
[S80]: https://developers.cloudflare.com/ai-gateway/features/unified-billing/ "Cloudflare AI Gateway：Unified Billing"
[S98]: https://blog.cloudflare.com/one-observability-platform/ "Cloudflare Observability 新平台发布"
[S99]: https://blog.cloudflare.com/cloudflare-tracing/ "Cloudflare Traces 发布"
[S100]: https://developers.cloudflare.com/observability/pricing/ "Cloudflare Observability 价格"
[S102]: https://developers.cloudflare.com/analytics/sql-api/query-api/ "SQL API 查询"
[S103]: https://developers.cloudflare.com/analytics/sql-api/limits/ "SQL API 限制"
[S104]: https://developers.cloudflare.com/changelog/post/2026-10-02-pi-harness/ "PiHarness 发布"
[S105]: https://developers.cloudflare.com/agents/harnesses/pi/ "PiHarness 状态与 Lifecycle"
[S106]: https://developers.cloudflare.com/changelog/post/2026-10-02-introducing-web-search-api/ "Web Search API 发布"
[S107]: https://developers.cloudflare.com/web-search/providers/ "Web Search API providers"
[S109]: https://developers.cloudflare.com/changelog/post/2026-10-02-protected-quick-tunnels/ "Protected Quick Tunnels 发布"
[S110]: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/ "Quick Tunnel 邮箱限制与开发边界"
[S114]: https://developers.cloudflare.com/artifacts/examples/sandbox-sdk-artifacts/ "Artifacts：Sandbox SDK 示例"
[S115]: https://developers.cloudflare.com/sandbox/sdk/migrate/replace-the-sandbox-class/ "Sandbox SDK 1.0：替换 Sandbox 类"
[S31]: https://blog.cloudflare.com/introducing-the-cold-start/ "The Cold Start"
[S32]: https://www.cloudflare.com/documents/build-next-gen-git-platform-competition-terms.pdf "Git 平台比赛正式规则"
[S49]: https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/ "Access Service Tokens"
[S116]: https://developers.cloudflare.com/changelog/post/2026-10-02-strict-service-token-authentication/ "Access 严格 Service Token 认证"
[S117]: https://developers.cloudflare.com/changelog/post/2026-07-09-tunnel-routes-and-connections-api-changes/ "Tunnel routes 与 connections API 变更"
