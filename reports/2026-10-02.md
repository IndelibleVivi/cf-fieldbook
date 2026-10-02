---
title: Cloudflare 新发布观察
subtitle: 个人开发者与独立创作者参考报告
edition: 2026.10 · 第 01 期 · 阅读版 3
source_cutoff: 2026-10-02
coverage_start: 2026-09-28
coverage_end: 2026-10-02
presentation_revision: 3
author: Faye & Cove
github: https://github.com/IndelibleVivi
credits: made by Faye & Cove
status: dated-reference
scope: 不含邮件服务；示例不对应私人账户或项目
---

# Cloudflare 新发布观察

**2026.10 · 第 01 期**  
个人开发者与独立创作者参考报告 · Faye & Cove

一次运行结束，文件还在。页面关掉，任务能重新接上。报错出现，不必再靠人从日志里拼出故事。这一轮 Cloudflare 发布，把过去需要自己连接的几段工作拉近了。[S04] [S07] [S11]

这份报告从个人使用出发，看新能力能省下什么劳动、适合放在哪里，以及它的开放状态和费用。具体项目各有历史与约束，文中的场景供读者对照，不是一套必须采用的组合。

资料截止 **2026 年 10 月 2 日**，主要覆盖 9 月 28 日至 10 月 1 日的发布；邮件另册处理。阅读版 3 修正作者与 GitHub 的呈现，并重新核对、扩充决策模型专题；其余发布信息沿用本期资料快照。[S01]

## 01 / 先看变化，再看产品名

### 执行环境有了下一次

以前，把代码放进一个临时环境，往往意味着运行结束就要重新准备。新的 Containers 快照和 Artifacts 给出了两种不同的延续：一份保存装好依赖的文件环境，一份保存可审查的文件历史。它们让短时执行更容易重复使用，不必顺带成为常驻服务器。[S04] [S05] [S07]

### 平台开始接住维护劳动

`cf` CLI 将资源查询与操作放进更统一的命令入口；Workers Issues 将失败与部署、源码和调用材料关联起来。对独立维护者，最直接的收益可能不是多做一个应用，而是少在控制台和编辑器之间搬一次材料。[S02] [S03] [S11]

### 检索与判断变得更专门

AI Search 将图片纳入正式支持的检索路径；Clef 则针对有限选项做判断。一个帮助人找回东西，一个帮助程序选择下一步。它们都值得通过小样本认识，而不是一接入就替换所有模型调用。[S09] [S16]

> **怎样读这一期**  
> 想试执行环境，读第 2 章；想改善维护，读第 3 章；资料与模型见第 4–5 章；浏览器和创作工具见第 6 章。费用、开放状态与申请日期分别在第 8–10 章。最后一章留了几种使用情境，没有默认的“个人最佳技术栈”。

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

## 03 / 少搬一次日志，少猜一个版本

### `cf` CLI：先从看清账户开始

新的 `cf` CLI 已进入公开 beta，提供覆盖更广控制面的命令、搜索和 JSON 输出。现有 Wrangler 项目可以先使用资源命令，不必立即转换全部配置。Wrangler 计划至少维护到 `cf` GA 后 18 个月，目前无需为了尝鲜集体迁移。[S02] [S03]

个人使用可以从只读盘点开始：有哪些 Worker，分别绑定什么资源，哪个版本正在服务哪个入口。等这些关系能被稳定查询，再考虑自动化修改。

### Workers Issues：让一个错误带着上下文到来

Issues 可以聚合同类失败，并关联调用、部署及源码材料，再通过 webhook 或其他集成交给后续工具。公开 beta 期间免费，面向所有 Workers 账户，只处理启用后的新流量。[S11] [S12]

第一次接入，建议让它产出一份调查材料：什么时候发生、对应哪个版本、怎样复现、已有测试是什么。修复仍通过原来的审阅与发布路径。这样先省掉搬运劳动，再决定是否扩大自动化。

使用 Wrangler 时需要 **4.134.0 或更高版本**，并把 `observability.issues.enabled` 写进配置；只在控制台打开，下一次部署可能覆盖。它也不会自动看到没有进入 Worker 的本机脚本或第三方故障。[S12]

### CI：交回能看的结果

Workers Builds 在 Paid 下包含每月 6,000 构建分钟、6 路并发，单次构建仍限 20 分钟。它适合 Worker 和前端的检查、构建与发布，不是通用 macOS／Windows runner。[S35]

比增加一条“构建成功”通知更有用的，是交回一个隔离预览、固定输入下的操作过程，以及导出后能重开的样本。前端的结果应该能看、能按、能比较。

Preview URL 与数据隔离要分别确认。当前 DO 和 Containers 有自动隔离支持；D1、R2、KV、Queues、Vectorize 等若仍指向同一资源，预览会共享相应数据。[S63]

## 04 / 让搜索找回一张图

### AI Search GA 带来的实际变化

10 月 1 日，AI Search 正式发布，支持通过多模态 embedding 索引图片像素；纯文本 embedding 也可使用图片描述路线。两者不是同一种视觉检索。扫描 PDF 可使用 OCR，音频和视频直接摄取仍是后续方向。[S09]

个人资料里经常有这样的东西：记得大致布局，却忘了文件名的截图；记得一句意思，却想不起用词的文章；只有扫描件的材料。对这些输入，先让搜索返回原件与定位，比立即生成一段总结更容易判断质量。

例如，查“主体偏左、文字沿轮廓走的构图”，再放入一张颜色相近、布局不同的反例。这比单查“蓝色海报”更能看出搜索是否理解了关系。文档查询也应包含旧版本和找不到答案的情况。

### 适合省掉什么，不适合省掉什么

AI Search 可以省去一部分分块、索引与检索维护。权限较简单的资料集合，适合先用小样本试。复杂撤回、严格版本控制和自定义混合排序，则可能更适合保留自己的状态库与检索管线。

当前限制也值得提前看：纯文本／代码和启用 OCR 的 PDF 可到 10 MiB；未启用 OCR 的 PDF 及其他受支持格式仍为 4 MiB。自定义元数据字段限 5 个，字符串的可过滤索引覆盖前 64 个 UTF-8 字节。复杂权限不能只靠把一个很长的规则字符串塞进 metadata。[S10]

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

## 08 / 把费用放回使用过程

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

R2 使用自己的免费层；Workers AI 的日额度也不是 Paid 独占。以上不是该账户尚余多少额度的证明。

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
| 2026-12-31 | 旧容器类／Sandbox SDK 维护节点 | 安排迁移验证，不解释为当日停机 [S04] |
| `cf` GA 后至少 18 个月 | Wrangler 计划维护期 | GA 日期未定，不猜具体停用日 [S02] |

账单提醒用于发现趋势；真正限制开销，还要靠任务截止时间、最大并发、调用次数和数据保留期。提醒不等于自动封顶。

## 09 / 发布状态速查

GA 表示该产品正式发布；不意味着相关的 SDK、托管版和地区全部同步开放。下面保留各自状态，便于回查。

### 可以调用、安装或进入公开测试

| 能力 | 本期状态与入口 | 来源 |
|---|---|---|
| `cf` CLI | 公开 beta，可与现有 Wrangler 项目并行使用资源命令 | [S02] [S03] |
| Workers Issues | 公开 beta；配置启用后处理新流量 | [S12] |
| Containers／快照 | 新调度为公开 beta 路线；Paid；快照需 DO 调度 | [S04] [S05] |
| Sandbox SDK 1.0 | 新接口与迁移文档已提供；底层仍有 beta 状态 | [S59] [S72] |
| Artifacts | 公开 beta，Paid | [S07] [S08] |
| AI Search | GA，11 月新计费 | [S09] [S10] |
| Clef／Clef-flash | Workers AI 模型可调用 | [S17] [S18] |
| AutoRouter／User Insights | 路由 beta；使用分析已开放 | [S13] [S14] |
| Kitesurf | beta，Playground／终端 | [S19] |
| EmDash 1.0／Build | CMS 稳定版／生成器 alpha | [S21] |
| K2／Basin | 事件流公开 beta／分析平台 GA | [S23] [S24] |

### 申请、候补与其他值得留意的发布

Cloudflare OS 托管版候补、KV Instant 私有 beta、Clef 强化学习设计合作及 Monetization Gateway 封闭 beta，各有独立申请条件。Monetization Gateway 使用 HTTP 402 为 API／MCP 等访问计费，当前面向符合条件的美国卖家；登记候补不等于已经得到可用服务。[S20] [S25] [S16] [S30]

其他发布可按现有技术栈选择：Workers OAuth Provider v1 提供授权与资源服务拆分等能力；Rust／Emscripten 扩大运行时实验；Forge 从 API 规范生成可维护接口；Vinext 1.0 面向 Next.js 的 Vite 迁移；Threat Signals 提供一个安全情报 RSS 的免费分析入口、最长保存 30 天。[S71] [S26] [S27] [S28] [S29]

Registrar 的程序化入口，以及 Workers 的 ML-KEM／ML-DSA opt-in 接口，也在本轮发布范围内。搜索域名不等于授权购买，实验密码接口不等于整套系统已完成后量子迁移。企业功能、研究原型与申请中的 CA 不作为个人套餐现成福利计算。[S01] [S33]

## 10 / 申请与比赛，先读条件

**Git 平台比赛**的截止为 **2026-10-14 23:59 PDT**。正式规则要求美国或加拿大合法居民、起始时满 18 岁，使用 Workers 与 Artifacts，支持多个 agent 并行工作，并提交源码、运行说明及 5–10 分钟演示。源码许可限 MIT、Apache-2.0 或指定 BSD；第一名的 $25,000 是 Cloudflare credits，不是现金。现场展示和其他条件仍应读完整规则。[S32]

**The Cold Start**面向位于美国或加拿大、融资少于 $1,000 万的早期创业公司，申请截止日期为 **2026-10-02**，奖项为 $500,000 Cloudflare credits。本期恰在截止日形成，阅读时先检查申请入口，不将它当作长期开放项目。[S31]

对多数个人试验，公开入口上的一次完整使用已经足以积累判断。是否改许可证、经营商业项目或参加比赛，应与作品计划有关，不必由 credits 金额决定。

## 11 / 使用场景，不是项目处方

每个人的项目、数据和维护习惯不同。以下只是编辑提出的试验情境，没有云端实测结论，也不是一套推荐组合。

**想少搬一次日志。** 用一个测试 Worker 的无害失败，检查 Issues 能否连起错误、版本与复现材料。先减少调查准备，自动修复和自动发布以后分别决定。

**想找回自己的视觉材料。** 选 30–50 张获准使用的图，保留来源，用真实查询比较多模态与图片描述。加入颜色相似、构图不同的反例，判断是否真的找回了原件。

**想比较两种实现。** 从同一文件基线开两份环境，交回补丁、可运行结果和同样的检查。关闭后再恢复一次，看准备是否更快、成果是否更易比较，而不先搭完整平台。

**想替掉一小段重复判断。** 让 Clef-flash 先只给分类建议，写清误判代价，允许无法判断，再和规则或已有模型比较。

<!-- SOURCES -->

## 来源索引

本次重新核对决策模型、接入路径与价格；其他发布条目沿用 2026-10-02 原版来源记录。资料核验不等于账户或模型实测。

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
- **[S31]** · The Cold Start
- **[S32]** · Git 平台比赛正式规则
- **[S33]** · 开发者平台 Changelog
- **[S34]** · Workers 价格
- **[S35]** · Workers Builds 限制与价格
- **[S36]** · Browser Run 价格
- **[S38]** · R2 价格
- **[S40]** · Vectorize 价格
- **[S41]** · Workers AI 价格
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

## 关于这一版

这是面向个人使用的独立参考资料，不是 Cloudflare 官方出版物。产品事实保留来源，场景与判断属于编辑分析。本次未进行账户操作或云端部署。

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
[S31]: https://blog.cloudflare.com/introducing-the-cold-start/ "The Cold Start"
[S32]: https://www.cloudflare.com/documents/build-next-gen-git-platform-competition-terms.pdf "Git 平台比赛正式规则"
[S33]: https://developers.cloudflare.com/changelog/product-group/developer-platform/ "开发者平台 Changelog"
[S34]: https://developers.cloudflare.com/workers/platform/pricing/ "Workers 价格"
[S35]: https://developers.cloudflare.com/workers/ci-cd/builds/limits-and-pricing/ "Workers Builds 限制与价格"
[S36]: https://developers.cloudflare.com/browser-run/pricing/ "Browser Run 价格"
[S38]: https://developers.cloudflare.com/r2/pricing/ "R2 价格"
[S40]: https://developers.cloudflare.com/vectorize/platform/pricing/ "Vectorize 价格"
[S41]: https://developers.cloudflare.com/workers-ai/platform/pricing/ "Workers AI 价格"
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
