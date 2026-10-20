---
title: CF Fieldbook 更新增补 · 2026-10-20
subtitle: 从检索与字段抽取，到能恢复、能核对的执行
edition: 2026.10 · 三册之后的独立增补
source_cutoff: 2026-10-20
author: Faye & Cove
credits: made by Faye & Cove
status: dated-supplement
scope: 汇集三册首发后纳入的资料与机制；沿用各来源的实际核验日期，无账户、模型或云端实测
---

# CF Fieldbook 更新增补 · 2026-10-20

**从检索与字段抽取，到能恢复、能核对的执行**

首发三册分别解释产品变化、个人基础设施的做法，以及 Clef／Jev 的决策模型路线。这份增补把此后进入 Fieldbook 的重要变化接成一条可独立阅读的路径：先取得材料，得到可检查的结果，再决定怎样执行、恢复与维护。

本册汇集 **10 月 8 日、13 日与 20 日**的更新，以 10 月 20 日为资料上界。10 月 8 日的 SDK 说明、10 月 13 日的模型与运行时资料沿用当次核验范围；本次重新查阅的价格、检索、抽取、Browser／MCP 与出站控制另有来源记录。资料上界不表示全书来源同日重新核验，公告、费用生效与实际运行也不是同一个时间。

这里没有模型 benchmark、账号开放验证、真实账单或云端恢复实验。合成材料、输入形状与验收方法用于让读者知道下一步应该检查什么。原三册、旧报告与已经冻结的文件继续保留；持续更新的使用说明可从[CF Fieldbook 阅读站](https://indeliblevivi.github.io/cf-fieldbook/)进入。

<!-- chapter: changes -->

## 01 / 三册之后，哪些判断需要重看

| 原先的判断或问题 | 现在需要补上的条件 |
|---|---|
| 便宜的小模型适合做简单任务 | 先分有限选项、字段值与生成；再比较输入完整性、误判与价格 |
| 中文原文明明存在，换 embedding 就好 | 先查 tokenizer、短词、and／or、入库与重建状态 |
| agent 下一轮能继续，就是状态持久化了 | 活着的浏览器、持久会话、外部动作各有自己的恢复边界 |
| 界面停止了，工具也应该停止 | Browser 调用可能继续完成；恢复前要先核对外部结果 |
| 代理连接成功、Worker 运行了，策略就生效 | 还要确认实际路由、分类、body 检查、命中政策与上游响应 |
| 价格表与博客不同，继续采用旧文档数值 | 现行 Observability 包含量已为 10 GB-month，生效仍在 12 月  |
| API 列表拿到了，就可以下结论 | 要知道分页完整性、总期限与失败后的未知范围 |
| 更新提醒没有命中，就没有变化 | 复核期限、新公告、生效事件和项目自身变化分开触发 |

这些条件并不要求读者重搭系统。它们帮助找到真正使用了变化接口的地方，保留仍然成立的选择，把必要的新验证接到原来的工作上。

<!-- chapter: models -->

## 02 / 模型需要输出什么，先于选哪一个模型

### 有限选项、字段值与开放文本

从一个允许的动作集合里选择下一步，与从通知中取出版本号，是两种不同的任务。前者的答案已经列好，后者的值往往无法事先枚举；写解释、代码或长文又有不同的输出要求。

| 需要的结果 | 候选能力 | 主要检查 |
|---|---|---|
| 读原文／继续找／材料不足，或其他已列选项 | Clef／Jev 有限决策 | 选项设计、误判、概率校准与材料是否完整 |
| 版本号、时间、数值、列表或原文片段 | Clairic typed extraction | 缺失值、原文位置、截断、数值和日期 |
| 解释、代码、开放式计划 | 通用生成模型 | 事实、推理、工具执行与生成质量 |

这个区分以任务的输出空间为依据，不能由一个模型单价推导它适合所有结构化工作。字段合法和选项合法，只减少了一部分解析问题，不证明判断正确。[S163] [S165]

### Clef 降价，也改变了长输入条件

10 月 9 日的 hosted Clef-flash 输入价从 $0.090 降为 **$0.038／百万 tokens**，同时窗口收为 **24,576 tokens**。Clef-omni 新增音视频输入，模型卡窗口 **64,000**，标价 **$0.150／M**；Clef 为 **65,536** 与 **$0.240／M**。这些是 10 月 13 日定向核对的规格，不把公告中的“64K”统一展开。[S123] [S17] [S18] [S124]

媒体与 questions 先占预算，剩余窗口不足时，文本 state 可能被截断。长材料流程先验证决定所需证据确实进入输入，再比较更低单价。Omni 的媒体能力也不等于输出开放式说明；同任务比较需要固定材料、问题与适配后的语义输入。[S18] [S124]

Jev 的 confidence 来自概率分布，不能与其他模型共用未经校准的阈值。第一轮在同一入口比较模型，第二轮固定模型再比较供应路径；版本不能固定时，保留为不同实验条件。当前 [Clef／Jev 专题](../comparisons/clef-vs-jev.md)及离线请求例子继续承接这些检查。[S77] [S78]

### Clairic：从短材料开始验证

10 月 19 日进入 preview 的 `@cf/cloudflare/clairic` 接收 `state` 与 typed `fields`，返回每个字段的值；文本可带原文字符位置，输入不足时 `value` 可为 `null`。标价 **$0.10／百万输入 tokens**，没有生成输出 token 费用。[S163] [S164]

例如材料是“版本 v2.4.1 于 2026-10-19T09:30:00Z 发布，错误代码 E_TIMEOUT”，可以定义版本、时间、错误码和负责人四个字段。负责人没有写，就应保留缺失，不能把其他名字猜成答案。再把错误码移到尾部，检查 `truncated`、原文 span 与尾部证据是否仍在；中文和 emoji 的位置要实际回读，不能假定所有 runtime 的字符串索引等价。

同页模型表列 **65,536-token context**，`fields` 参数却写材料与字段装入 **8,192-token pass**；目前关系没有解释清楚。字段可拆多个 pass，费用应看响应中的 `usage.input_tokens` 与 `usage.passes`。先测短材料，不把较大数字当完整读取保证；复杂算术则抽取输入后交给代码。[S164]

### 通用生成模型仍有自己的路线

Workers AI 的 `@cf/deepseek-ai/deepseek-v4.1-flash-1017` 提供视觉、reasoning 与 function calling，context 为 **1,048,576 tokens**；输入 **$0.30／M**、输出 **$1.20／M**、缓存输入 **$0.006／M**，需要 Workers Paid 或预付 AI Gateway credits。它属于生成路线，本书没有把它与有限决策或抽取模型混作同任务排名。[S170] [S171]

<!-- chapter: retrieval -->

## 03 / 中文检索先从原件与索引查起

AI Search 接管摄取、分块与一部分检索，应用仍负责权限、版本、撤下与回读原文。一个零结果并不直接证明原文没有答案，也不直接证明 embedding 不适合。

10 月 16 日，AI Search 修复 `trigram` 对无空格中日韩问句的处理；此前这类查询容易被当成一个完整短语。官方建议中日韩内容设置 `indexing_options.keyword_tokenizer` 为 `trigram`，切换会全量重建索引。[S161] [S162]

trigram 使用重叠的三个字符，**不足三个字符的词不能独立匹配**。`retrieval_options.keyword_match_mode` 默认 `and`，改为 `or` 扩大召回时，也要检查多出来的片段。Workers Paid 的 keyword 实例最多 500,000 文件，vector-only 为 1,000,000；容量和重建不能只看查询单价。[S162]

### 一组问题，保留每题的已知证据

下面全部是合成输入和待验证样本，没有运行云端索引。

| 已知原件 | 问法 | 要分辨的失败 |
|---|---|---|
| 撤下后立即拒读，随后清理索引 | “资料撤下后还能读到旧版本吗？” | 长问句匹配到了相近词，却没返回真正规则 |
| 维护人为“林岚” | “林岚”；“谁负责维护资料架？” | 两字短词边界与语义查询的不同 |
| 恢复接口使用 `lease_expires_at` | “lease_expires_at”；“job_id 租约” | 标识符切片、多个查询项及 and／or |
| 先核对外部结果，再决定重试 | “回包丢了要再做一遍吗？” | 语义改写找不到原文中的操作条件 |
| 集合未说明售价 | “这份资料卖多少钱？” | 为了给答案而使用不相关片段 |

固定同一原件版本，比较 keyword／hybrid 与匹配模式；记录命中片段、漏检、误召回、耗时和用量。出现问题时，先查文件是否摄取、分块是否带证据、重建是否完成，再比较 embedding 与 reranking。查询返回后，还要核对当前读取资格与原件版本。

### 11 月计费按阶段与查询类型拆开

AI Search **11 月 1 日**开始计费，每月含 5M 摄取 tokens、10 GB-month 存储，以及各 1,000 次 semantic 与 full-text 查询。超额 full-text **$0.10／千次**，semantic／vector／hybrid **$0.75／千次**。内部 Workers AI embedding 与 reranking 已包含；生成、query rewriting、外部模型另计。估算一个回答的成本，要同时统计查询次数和后续调用。[S10]

<!-- chapter: web-reading -->

## 04 / 搜得到与读得全，是两个验收

自己的资料集合和当前互联网是两个证据入口。10 月 12 日提供的 Agents SDK `web_search` 与 `web_fetch` 可以直接调用，也可以接入 harness；前者要求 SDK ≥0.27.0，后者 ≥0.28.0。先取得候选 URL，再读取原页，核对版本、日期和条件，不必让每次搜索都由模型先发起一轮工具调用。[S128] [S129] [S130] [S131]

模型选择 query 和结果数，应用固定 provider、Gateway 与用量边界。搜索摘要不能替代来源原文；使用自定义 source，也会接过 provider、费用与网络限制的责任。[S129]

SDK 读页默认每窗 20,000 字符，以 offset 继续；整个响应默认最多 5,000,000 bytes，总 deadline 30 秒。这条读取不带浏览器 cookies、凭据或自定义请求头，不执行页面 JavaScript；需要登录或交互，再选择浏览器路线。一次返回成功不等于全文完整。[S131]

10 月 9 日 Markdown for Agents 改为边缘进程内流式转换，HTML 上限增至解压后 6 MiB，同时移除 `x-markdown-tokens`、`x-original-tokens` 与 `Content-Length`。消费者按实际读取的 body 检查预算，保留中断状态；不能因为缺少 header 就判失败，也不能因为已收到一段正文就判完整。转换上限、传输预算和返回窗口分别控制。[S127]

<!-- chapter: runtime -->

## 05 / Agent 继续运行，需要分别保存哪些状态

持久身份、对话状态、工具执行环境与外部动作结果不是同一份东西。把它们拆开，才能解释“下一轮恢复了什么”，以及哪些调用绝不能自动重做。

### 多一点排空时间，仍然要能恢复

10 月 12 日 Workers 例行 runtime 更新的旧进程排空窗口由最多 30 秒增至最多 20 分钟。它按旧进程计算，故障仍可让连接更早断开；响应后的 `waitUntil()` 也仍有自己的 30 秒限制。长连接需要重连，业务动作需要自己的身份和恢复规则，不能把排空窗口当持续执行保证。[S125] [S126]

同日的 experimental OpenCodeHarness 将 OpenCode 会话放进 SQLite-backed Durable Object，以 Lifecycle 唤醒中断工作；工具环境仍需配置。服务端持久事件与客户端实时文字增量有不同回放范围，未提交的实时内容不会自动重新出现。接入前分别检查服务端恢复、工具行为与客户端重连。[S132] [S133]

### Browser 保存活会话，不是快照

SDK ≥0.28.0 的 Browser／browserTool 可保留远端浏览器，DO 保存 session identifier，休眠后在浏览器仍活着时重连。默认空闲保活 **10 分钟**；到期、关闭或崩溃后下一次创建新浏览器，返回 `restarted: true`，旧 tabs、cookies 和登录态已经消失。[S143] [S144]

Pi 默认每段 conversation 一个 active tab，但同一 Browser 中 cookies 与登录共享；tab scope 不等于独立 profile。不同用户若需独立登录态，必须隔离浏览器。Live View 允许人在同一个活浏览器中查看或接管，不能据此推断永久保存。[S144]

**Pi 不自动重放因 eviction 中断的浏览器调用；停止 conversation 也不取消已经运行的调用。** 调用会完成或达到 `timeoutMs`，默认 60 秒。表单提交或点击结果未知时，先查页面、动作身份或外部记录；“模型停下了”不能写成“外部动作没有发生”。[S144]

### 事件调查与追加权限

Workers Issues 可作为 MCP Events 发送新问题或复发问题：客户端发现并按账号或 Worker 订阅，服务器向 webhook 发签名事件。需启用 Issues，以 Notifications Write 和 Workers Observability Write 权限连接支持该扩展的客户端。事件只触发调查，接收后仍需读回版本、时间窗和错误证据。[S145]

API MCP 的 step-up 允许先用 Minimal 连接，缺少 scope 时返回 `insufficient_scope`，再由支持的客户端请求用户追加授权，保留原有 scopes。事件、工具错误或自动重试都不能替代授权。[S146]

<!-- chapter: egress -->

## 06 / 请求真正发出去以前，在哪里检查

CWS 与 Gateway Forward 都可以影响出站请求，但运行位置、可见流量和执行条件不同。

| 路线 | 检查什么 | 开放与成本条件 |
|---|---|---|
| Cloud Workload Security | 用户运行的 proxy 对云 API 操作及参数执行过滤与 Rego | 10 月 19 日 Beta；Zero Trust Free 足够，主机与维护自行承担 |
| Gateway Forward Workers | 已进入 Gateway 且匹配 Forward 的 HTTP 请求／响应 | 10 月 15 日 public beta；所有 Zero Trust plans，Workers 按常规计费 |

### CWS：创建策略不会自动改变流量路径

CWS 的 workload 选择请求，policy 检查请求，policy set 组合范围，deployment 提供给用户运行的 proxy。当前本地入门面向 Linux／VM，客户端要实际使用代理并信任其 CA；代理须加载当前 deployment，policy 处于 Enforce 并匹配。云提供商自身的调用凭据与资源权限仍然存在。[S151] [S152] [S153] [S154]

排错文档明确：未分类目的地可能按 raw tunnel 通过，不执行 request policy。配置加载、连接成功、请求被分类、策略允许与上游成功分别是证据。一个云 API 的 403 也可能来自上游权限，不能看到状态码就认定 CWS 已阻断。body inspection 被跳过或日志截断时，也要保留实际观察边界。[S155]

获准验收时，固定一个合成允许请求和一个合成拒绝请求；同时看客户端代理设置、当前配置、分类、policy decision 和上游响应。只看到 dashboard 保存成功，不能证明请求走过了检查点。

### Gateway Forward：调用 Worker 不证明 body 通过

Forward 需要设备流量进入 Gateway，同账号的 Worker 已部署，HTTPS 已解密并配置可信根证书。HTTP request policy 允许后，第一条匹配的 Forward policy 选择 Worker；body inspection 可能在 Worker 已开始后拒绝并中断它，最终响应仍会经过检查。[S156] [S157]

`GatewayMiddleware.handle(request, context, next)` 可变换请求／响应，或直接返回合成响应。`next()` **零次或一次**，保留原 destination URL 和 host，不能用来重试或扇出；普通 Workers `fetch()`是独立 subrequest，不能假定沿用用户 Gateway 策略与出口 IP。[S156]

WebSocket、CONNECT 与 Do Not Inspect 流量不经过这个 Worker。Gateway 检查原始请求 body 和最终响应，不会再次扫描 Worker 新增的请求 bytes；因此不能假设修改后的全部数据又通过了一轮 request-side DLP。[S156]

博客展示了“DLP profile 命中后向绑定 Worker 发送流量”的告警场景，接口文档却明确 DLP／body inspection 结果不能用于选择 Worker。本册保留差异，具体实施按接口文档并另行验收。不能把应用方向直接当可部署的筛选条件。[S158] [S156]

<!-- chapter: observability -->

## 07 / 观测要保留因果边界，也要重算费用

### 499 与日志导出，不只看最后状态码

10 月 9 日 HTTP/3 客户端取消的处理与记录改变，部分请求更早停止并记为 499；此前可能继续到源站并记录上游状态。499 增多可能来自记录口径更完整，不能直接推断服务端故障增多。若取消集中在慢请求上，等待原因仍需调查。[S140]

Logpush Transformers 在导出前过滤与变换记录。10 月 12 日的机制说明解释，转换失败不发送原始 batch，也不推进 delivery offset，系统会重试并报告错误，长期失败的 job 可能被禁用。接收端没有新日志，应检查转换本身，而不是立刻增大导出量。[S141]

### Observability：10 GB-month，仍从 12 月 生效

10 月 20 日复看的价格页列明，**2026-12-01**起 Paid 共享包含量为每 billing cycle **50 GB 摄取＋10 GB-month 存储**，超额分别 **$0.25／GB**和 **$0.10／GB-month**。Enterprise 在续约时迁移；Log Explorer datasets 另有计价，不消费共享包含量。[S100]

本书旧登记曾采用 12 GB-month，现已将当前数据与表格改为 10，原 12／10 差异不再是当前口径。页面标注 10 月 15 日更新，不足以确定正式条款变更日；10 月 也不能提前套用 12 月 账单。

价格页的算例仍有算术不一致。一个 billing cycle 内 75 GB 摄取、20 GB-month 存储，按条款应为：

| 项目 | 计算 | 超额费用 |
|---|---|---:|
| 摄取 | (75−50) × $0.25 | $6.25 |
| 存储 | (20−10) × $0.10 | $1.00 |
| 合计 | $6.25＋$1.00 | **$7.25** |

页面仍列存储$0.80 与合计$7.05。应按条款重算，不能把发布页的示例当作实际账单。[S100]

### Artifacts 公开计费期已经到达

价格页写 10 月 14 日起算，博客仍写 15 日；截至本册两日均已过去，按公开计费期安排预算，但没有账号扣款验证。每月包含 10,000 operations 和 1 GB，超额$0.15／千次与$0.50／GB-month；单 repo 上限 1 GB、file／blob 上限 32 MB。文件历史与运行中的容器各有生命周期，任务退出不自动停止仓库存储计量。[S07] [S08] [S136]

<!-- chapter: operations -->

## 08 / 数据地点、连接寿命与构建环境

Queues 新增 `eu`、`us`、`fedramp` jurisdiction，创建后不能改变，DLQ 必须相同；生产／消费 Worker 仍可在别处运行。D1 可新建 US jurisdiction 数据库，在美国运行并持久化。一个组件满足地点约束，不代表 Worker、队列、存储、日志与模型整条链路都满足。[S137] [S138] [S139]

| 运维变化 | 先做的判断 |
|---|---|
| Local Explorer 单次测 Cron | 启动既有 dev server，从 Cron Triggers 调用 `scheduled()`，指定时间并看结果；本地不会自动按 cron 表跑，临时预设不改生产配置。[S166] |
| infrastructure application 会话时长 | 默认 24 小时，到期关闭活跃 SSH；多个应用取最短。进程存活、连接与结果恢复分开验收。[S167] |
| Tunnel／Mesh routes 扩容 | 默认 50,000 指 CIDR／hostname routes，不包括 published applications。每账户含 1,000 tunnels，额外$4.50／tunnel·月。[S168] |
| Workers Builds 默认工具链升级 | 10 月 14 日默认 Node24.21.0、Python3.14.8；环境变量或版本文件固定的项目继续使用指定版本。源码没变时，也应比较镜像、runtime 和 lockfile。[S169] |

这些变化各自有适用对象。普通 HTTP Tunnel ingress 不因私网路由 API 改名就必须迁移；只有解析旧连接字段、使用特定 jurisdiction 或依赖默认版本的地方，才需要对应复查。

<!-- chapter: maintenance -->

## 09 / 用程序维护，也要说明哪里仍未知

### 先选调用入口，再检查完成条件

10 月 8 日新增的 API 维护入口区分控制台、CLI、REST、SDK 与 Worker binding。控制台便于发现；CLI 适合可检查的小操作；SDK 把语言类型与客户端行为带入应用；R2 的 Workers、S3 和管理 REST 也各有职责。入口选择不消除完整分页、期限与结果核对。[S118] [S122]

拿到 20 个资源但下一页超时，只能报告已经读到的范围，不能写“其余不存在”。读操作可在总期限内做有限重试，某次 HTTP 超时不应悄悄重新获得完整任务预算。写请求响应丢失时，外部动作可能已经成功；先用稳定身份与读回记录核对，再决定能否重做。

本书的[离线操作例子](../examples/api-operations/README.md)用虚拟时间和合成分页演示这些机制，没有连接真实 SDK；同进程内存里的结果核对也不证明崩溃后持久恢复。代码测试、官方接口查阅与云端验收分别记录。

Go 默认值固定在 `v7.12.0` 的 README 范围；`v7.13.0` release 移除 `Registrar.Domains` 下 List／Get／Update，转向 `Registrar.Registrations`，先找实际调用再迁移。GitHub 发布时间 10 月 12 日与 notes 的 10 月 9 日分别保留，不把“SDK 更新”写成全部项目受影响。[S119] [S120] [S142]

### 先主动取得官方入口

`cf docs search` 无需 Cloudflare 登录，返回最多五条排序 JSON，含标题、简介与 URL；继续读取原页 Markdown 再核对条件。源码 beta.15 已加入该能力，10 月 16 日公告介绍 beta.16 并说明 kebab-case 改名，例如 `getCredits` → `get-credits`。脚本要核对锁定版本，不能从命令名变化猜 API 变化。[S149] [S150] [S160]

CLI changelog 明示搜索 query 会进入 telemetry；公共查询足够时，不要把私人项目材料送进搜索。API MCP 的 Skills 扩展、Events 与 step-up 也各需客户端支持，连接成功不等于全部能力已兼容。[S134] [S145] [S146]

### 把更新接回项目已有的理由

Fieldbook 提供[项目判断入口](../use-cases/project-context.md)和任务单；当前采用理由、配置、版本与运行证据留在各项目已有文档。新公告之外，搬到 VPS、发布越来越慢、网站只需静态内容等项目自身变化，也会改变选择。

检查结果区分三种：命中了具体版本／调用／字段／运行流程；在已查范围内未发现；证据不足仍未知。保留暂缓条件和下一项验证，不能仅凭产品名相同就要求迁移，也不建立私有跨项目状态表。

本轮来源维护继续采用“来源→候选影响→精确数据→当前事实块→表外解释”。`impact-source`支持 JSON 的 `source` 单值与 `sources` 数组；历史报告是传播终点。`due`只查登记复核日，事实块检查只验证共源，二者都不能替代新公告调查或整页适用性判断。

<!-- chapter: next-step -->

## 10 / 带着一个完整任务回去

选一个当前问题，沿着这份增补取得最小充分证据：

1. **材料在哪里。** 确定自己的集合还是互联网，记录原件、版本和是否有权限。
2. **需要什么结果。** 有限选项、typed fields 或生成；保留无答案、缺失与尾部证据。
3. **动作经过哪里。** 列出浏览器、SDK、CWS 或 Gateway 真正看见的请求，不用连接成功代替策略证据。
4. **中断后怎样核对。** 区分会话、工具调用与外部结果；未知动作不自动重放。
5. **成本何时生效。** 按计量单位、包含量、额外模型与存储留存计算，不提前套未来价格。
6. **只改实际命中的地方。** 使用项目现有理由与证据，验证完成条件，更新当前说明。

本册给出的是截至资料上界可公开检查的机制与判断。采用哪个产品、授权哪些动作、是否运行真实实验，继续由具体任务和项目边界决定。

<!-- SOURCES -->

## 来源索引

本册承接三册首发后的 10 月 8 日、13 日和 20 日资料。来源的实际读取日期与范围保存在 Fieldbook 目录；10 月 20 日只对本轮主题和相应价格作定向核对。合成样本、输入形状与路径解释不构成模型、账单或云端实测。原三册与旧报告按原身份保留，本文件是独立增补。

GitHub · [github.com/IndelibleVivi](https://github.com/IndelibleVivi)  
*made by Faye & Cove*

[S07]: https://blog.cloudflare.com/next-git-platform-on-cloudflare/ "Artifacts 公开测试发布"

[S08]: https://developers.cloudflare.com/artifacts/platform/pricing/ "Artifacts 价格"

[S10]: https://developers.cloudflare.com/ai-search/platform/limits-pricing/ "AI Search 限制与价格"

[S17]: https://developers.cloudflare.com/workers-ai/models/clef/ "Clef 模型卡"

[S18]: https://developers.cloudflare.com/workers-ai/models/clef-flash/ "Clef-flash 模型卡"

[S77]: https://docs.typesafe.ai/confidence "TypeSafe：confidence 的含义"

[S78]: https://docs.typesafe.ai/model-jaggedness/jev-1.13 "TypeSafe：Jev 1.13 已知能力边界"

[S100]: https://developers.cloudflare.com/observability/pricing/ "Cloudflare Observability 价格"

[S118]: https://developers.cloudflare.com/fundamentals/api/reference/sdks/ "Cloudflare 官方 SDK 与 curl 使用入口"

[S119]: https://github.com/cloudflare/cloudflare-go/blob/v7.12.0/README.md "Cloudflare Go v7.12.0：分页、超时与重试"

[S120]: https://github.com/cloudflare/cloudflare-go/releases/tag/v7.12.0 "Cloudflare Go v7.12.0 release：管理接口与迁移"

[S122]: https://developers.cloudflare.com/r2/api/ "R2 API：Workers、S3 与 REST 的职责"

[S123]: https://developers.cloudflare.com/changelog/post/2026-10-09-clef-omni-workers-ai/ "Clef-omni 发布与 Clef-flash 降价／上下文收缩"

[S124]: https://developers.cloudflare.com/workers-ai/models/clef-omni/ "Clef-omni 模型卡与媒体输入预算"

[S125]: https://developers.cloudflare.com/changelog/post/2026-10-12-longer-runtime-update-grace-period/ "Workers 运行时更新排空窗口"

[S126]: https://developers.cloudflare.com/workers/platform/limits/ "Workers 平台限制：执行、等待与运行时更新"

[S127]: https://developers.cloudflare.com/changelog/post/2026-10-09-markdown-for-agents-in-process-conversion/ "Markdown for Agents 流式转换与响应头变更"

[S128]: https://developers.cloudflare.com/changelog/post/2026-10-12-web-search/ "Agents SDK web search 工具发布"

[S129]: https://developers.cloudflare.com/agents/tools/web-search/ "Agents SDK Web Search 调用与适配器"

[S130]: https://developers.cloudflare.com/changelog/post/2026-10-11-web-fetch/ "Agents SDK web fetch 工具发布"

[S131]: https://developers.cloudflare.com/agents/tools/web-fetch/ "Agents SDK Web Fetch 的窗口、期限与抓取边界"

[S132]: https://developers.cloudflare.com/changelog/post/2026-10-12-opencode-harness/ "OpenCodeHarness 发布"

[S133]: https://developers.cloudflare.com/agents/harnesses/opencode/ "OpenCodeHarness 生命周期与事件回放"

[S134]: https://developers.cloudflare.com/changelog/post/2026-10-10-cloudflare-mcp-skills/ "Cloudflare API MCP 的 Skills 扩展"

[S136]: https://developers.cloudflare.com/artifacts/platform/limits/ "Artifacts 仓库、对象与账户限制"

[S137]: https://developers.cloudflare.com/changelog/post/2026-09-18-queues-jurisdictions/ "Queues jurisdiction 发布"

[S138]: https://developers.cloudflare.com/queues/configuration/data-location/ "Queues 数据地点与死信队列约束"

[S139]: https://developers.cloudflare.com/changelog/post/2026-10-02-us-jurisdiction/ "D1 美国 jurisdiction"

[S140]: https://developers.cloudflare.com/changelog/post/2026-10-09-http3-499-reporting-improvement/ "HTTP/3 取消请求的 499 记录改进"

[S141]: https://blog.cloudflare.com/transformers-on-logpush/ "Logpush Transformers 的转换与失败交付语义"

[S142]: https://github.com/cloudflare/cloudflare-go/releases/tag/v7.13.0 "Cloudflare Go v7.13.0 release"

[S143]: https://developers.cloudflare.com/changelog/post/2026-10-13-persistent-browser/ "Agents SDK 跨 turn 的 Browser/browserTool"

[S144]: https://developers.cloudflare.com/agents/tools/browser/ "Browser 会话、tab、中断与 Live View"

[S145]: https://developers.cloudflare.com/changelog/post/2026-10-13-cloudflare-mcp-events/ "Cloudflare API MCP 作为 MCP Events 发送 Workers Issues"

[S146]: https://developers.cloudflare.com/changelog/post/2026-10-19-cloudflare-mcp-step-up/ "Cloudflare API MCP 的 step-up authorization"

[S149]: https://github.com/cloudflare/cf/blob/main/packages/cli/CHANGELOG.md "cf CLI changelog：文档搜索与 kebab-case 命令"

[S150]: https://github.com/cloudflare/cf/releases/tag/cf%401.0.0-beta.15 "cf 1.0.0-beta.15 release：docs search"

[S151]: https://developers.cloudflare.com/changelog/post/2026-10-19-cloud-workload-security-beta/ "Cloud Workload Security Beta 发布"

[S152]: https://developers.cloudflare.com/cloudflare-one/cloud-workload-security/ "Cloud Workload Security：workloads、policies 与 Rego"

[S153]: https://developers.cloudflare.com/cloudflare-one/cloud-workload-security/platform/ "Cloud Workload Security proxy 部署与平台条件"

[S154]: https://developers.cloudflare.com/cloudflare-one/cloud-workload-security/get-started/ "Cloud Workload Security 本地 proxy 入门"

[S155]: https://developers.cloudflare.com/cloudflare-one/cloud-workload-security/troubleshooting/ "Cloud Workload Security proxy、CA 与未分类隧道排错"

[S156]: https://developers.cloudflare.com/cloudflare-one/traffic-controls/integrate-workers/forward-traffic/ "Gateway Forward traffic：执行顺序、限制与故障"

[S157]: https://developers.cloudflare.com/changelog/post/2026-10-15-gateway-workers-public-beta/ "Gateway 与 Workers 集成进入 public beta"

[S158]: https://blog.cloudflare.com/programmable-gateway-dlp/ "可编程 Gateway 与 DLP 示例"

[S160]: https://developers.cloudflare.com/changelog/post/2026-10-16-docs-search/ "使用 Cloudflare CLI 搜索文档"

[S161]: https://developers.cloudflare.com/changelog/post/2026-10-16-cjk-keyword-search/ "AI Search 中日韩关键词查询修复"

[S162]: https://developers.cloudflare.com/ai-search/configuration/indexing/keyword-search/ "AI Search keyword tokenizer、匹配模式与索引限制"

[S163]: https://developers.cloudflare.com/changelog/post/2026-10-19-clairic-workers-ai/ "Clairic preview：有类型的字段抽取"

[S164]: https://developers.cloudflare.com/workers-ai/models/clairic/ "Clairic 模型卡、输入字段与上下文说明"

[S165]: https://blog.cloudflare.com/clairic-extraction-model/ "Clairic 抽取、决策与生成的输出空间"

[S166]: https://developers.cloudflare.com/changelog/post/2026-10-17-local-explorer-cron-triggers/ "Local Explorer 单次调用 Cron Triggers"

[S167]: https://developers.cloudflare.com/changelog/post/2026-10-14-infrastructure-ssh-session-duration/ "Access infrastructure application 会话时长"

[S168]: https://developers.cloudflare.com/changelog/post/2026-10-16-tunnels-for-platforms-and-50k-routes/ "Tunnel 与 Mesh 的五万 routes 和 Tunnels for Platforms"

[S169]: https://developers.cloudflare.com/changelog/post/2026-10-14-workers-builds-default-tooling/ "Workers Builds 默认工具链升级"

[S170]: https://developers.cloudflare.com/workers-ai/models/deepseek-v4.1-flash-1017/ "DeepSeek V4.1 Flash 1017 模型卡"

[S171]: https://developers.cloudflare.com/changelog/post/2026-10-19-deepseek-v4.1-flash-workers-ai/ "DeepSeek V4.1 Flash 1017 Workers AI 发布"
