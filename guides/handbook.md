---
title: Cloudflare 个人基础设施实践手册
subtitle: 从一个入口到可恢复的应用与自动化
edition: 2026.10 · 阅读版 3
source_cutoff: 2026-10-02
presentation_revision: 3
author: Faye & Cove
github: https://github.com/IndelibleVivi
credits: made by Faye & Cove
status: living-guide-snapshot
scope: 不含邮件服务；通用示例与实际账户分离
---

# Cloudflare 个人基础设施实践手册

**2026.10 · 阅读版 3**  
从一个入口到可恢复的应用与自动化 · Faye & Cove

一个网站能打开，只是开始。用了几周以后，问题会变得更具体：手机怎么访问，朋友能看哪些内容，文件放在哪里，任务断了能否继续，暂时不用时会不会还在付费。

本手册从这些问题出发。它不要求先学完 Cloudflare，也不把服务组合当作唯一答案。已有服务器、数据库和工作方式都可以保留，只在出现实际需要的地方加入新的能力。

本版承接既有《Cloudflare 用途盘点与实战教程》的 7 月基础版和 8 月扩充版，以 **2026-10-02** 的来源快照为依据。阅读版 3 修正署名并补入决策模型的供应路径，详细代码和状态约束保留在仓库的 `reference/implementation.md`。邮件不在本期范围内。

## 01 / 从手边的事情开始

如果只是想发布网页或小 API，从第 2–3 章开始就够了。已有本机或 VPS 服务，希望安全访问，重点读第 4 章。内容与文件的保存看第 5 章；自动化经常重复、超时或丢结果，看第 6 章。

检索、模型与 agent 执行分别在第 7–9 章。系统已经能运行，却越来越难维护，可以直接读第 10–13 章。各章不构成强制施工顺序。

本手册解释做法；配套《Cloudflare 新发布观察》记录当期产品变化和价格时间线。工具名或价格影响决策时，可通过文内来源编号回查。

## 02 / 给一个请求找路

### 先分清：入口、程序、数据

浏览器输入域名，先找到服务入口，再由程序处理请求，最后按需要读取数据库或文件。DNS 和 HTTPS 让请求到达正确的地方；Worker 可以在 Cloudflare 上运行程序；Tunnel 则把入口连接到仍在本机或服务器运行的程序。[S45] [S47]

因此，小应用有两种同样合理的起点。第一种是 Worker 加必要的数据存储。第二种是 Access／Tunnel 加现有应用，数据库继续留在原来的服务器。选择取决于程序需要什么环境，不取决于控制台里有多少服务可以开。

<!-- figure: two-routes -->

| 路线 | 请求怎样走 | 程序与数据在哪里 |
|---|---|---|
| 新建边缘应用 | 浏览器 → Worker → 绑定的数据资源 | 应用运行在平台上，按需选择存储 |
| 保留已有服务 | 浏览器 → Access（需要时）→ Tunnel → 原应用 | 仍由原设备／服务器运行 |

*这是两种常见组合，不要求一个项目同时采用。*

### 绑定：把资源交给应用，而不是交出整套账户

在 Worker 里，`env.DB` 可以指向一项 D1 数据库，`env.FILES` 可以指向一个 R2 bucket。这种 binding 是部署时给予程序的能力，通常不需要在业务代码里再携带账户管理 key。[S45]

可以把三件事分开记：管理工具负责创建和部署资源；binding 让应用使用被分配的资源；应用再决定哪位用户能读写哪些内容。

同一账户的 Worker 之间，可以用 Service Binding 调用指定服务，减少公网入口和重复凭据。调用关系由部署配置和可靠身份建立；请求里随手加一个 `x-service-id`，并不能自己证明是谁发来的。[S57]

## 03 / 发布第一个小入口

### 先选一个很容易判断对错的功能

健康检查适合起步：`GET /health` 返回固定 JSON，未知路径返回 404，不读取文件、不调用模型、不接受业务写入。这样一旦响应不对，排查范围很小。

随包的 `examples/health-worker/` 已有完整源码、配置模板和测试。它还检查 HEAD 与不允许的方法；人读手册时先理解行为，实施时再打开完整文件。

| 发出的请求 | 应得到什么 |
|---|---|
| `GET /health` | 200，固定 JSON |
| `HEAD /health` | 200，没有正文 |
| `POST /health` | 405，注明允许的方法 |
| `GET /missing` | 404 |
| 请求夹带私有头 | 响应不回显这些内容 |

在仓库根目录，可先做离线检查：

```bash
node --test examples/health-worker/worker.test.mjs
python3 tools/check.py
```

这检查的是示例行为和资料一致性，不会登录或部署 Cloudflare。健康响应本身也只证明这个 handler 工作，不能代表所有数据库与外部依赖都正常。

### 再接入开发与部署工具

当前 `cf` CLI 处于公开 beta，Wrangler 仍受支持。新项目可沿官方脚手架选择工具；既有项目不需要为了新命令立即迁移。记录实际版本与依赖锁文件，比依赖某台机器的全局安装更容易重建。[S02] [S03] [S66]

采用 Wrangler 且已在项目里安装固定版本时，可先启动本地开发：

```bash
npx --no-install wrangler dev --port 8787
```

然后在另一终端请求本地 `/health` 和 `/missing`。本地通过后，再核对目标账户、路由和配置，执行单独的远端部署。完整命令与模板留在实施参考中；本包没有替读者安装工具或创建生产入口。

### 前端加入后，多检查一次缓存

Workers Static Assets 可把网页与 API 一起发布。要确定静态资源和 Worker 的处理顺序，避免 SPA fallback 把不存在的 API 变成一张“看起来正常”的首页。静态资源与动态请求也有不同计费规则。[S46] [S34]

私人 PWA 可以先只缓存公开壳，私有 API 使用 `no-store`。检查退出登录、切换用户和更新旧版本之后的行为：用户已经离开，并不意味着浏览器里保存过的内容自动消失。

## 04 / 私人服务的门与钥匙

### 能到达，不等于有权使用

Access 可以保护一个 hostname 或指定路径，让用户先完成身份验证。应用依赖该身份时，应验证 JWT 的签名、issuer、audience 与有效期，而不是只看请求头是否存在。[S48]

拿到可信身份之后，应用继续决定角色、资源和动作。没有必要机械地再叠几份 bearer；额外凭据应当服务于单独撤销、机器作用域或动作确认，而不是仅仅增加层数。

对机器客户端，Service Tokens 能避免模拟网页登录。按用途单独签发，设置有效期和撤销方式，再映射到允许的操作范围。浏览器里的长期秘密、多人共用的万能 key，都不适合作为这种边界。[S49]

### 不只测“自己能打开”

上线前也试匿名用户、已登录但没有资格的用户、过期 token 和错误 audience。再列出所有替代入口：默认开发域名、其他 Custom Domain、预览地址、源站直连。保护一个域名，不会自动证明另一条路也安全。

Cookie 会话的写请求还要处理 CSRF／Origin。私人数据应在权限检查以后读取，而不是先取得完整内容，再靠界面藏按钮。

### 已有服务器：Tunnel 只改变访问方式

Tunnel 由源站连接器主动向 Cloudflare 建立连接，把指定 hostname 的请求送到原应用。它不替原设备运行程序，不备份磁盘；笔记本关机后，程序仍会停。[S47]

```yaml
ingress:
  - hostname: app.example.com
    service: http://127.0.0.1:8080
  - service: http_status:404
```

这只是示例结构。端口要对应实际监听，最后一条为未知入口提供兜底；源站若还另开公网端口，仍需检查是否绕过访问限制。

顺序可以很朴素：先确认本机 HTTP 正常，再检查连接器与 Tunnel，最后从外部验证 hostname 和权限。Quick Tunnel 适合短暂试验，长期入口使用可管理的命名配置。升级、日志和恢复方式依然属于服务器维护的一部分。

### MCP 与私网各有自己的入口

远程 MCP 的 OAuth 发现、授权与 token 验证不是普通浏览器登录。Workers OAuth Provider v1 可作为授权服务与资源服务拆分的实现候选；连接成功后，仍要检验错误受众、过期令牌与跨资源请求。[S71]

WARP 是设备接入与流量策略；Mesh 面向加入组织的设备和私网；Tunnel 发布明确选择的服务。Mesh 当前仍有 beta 标识。与现有 VPN 共存时，先用非关键设备观察路由和 DNS，保留不依赖待改路径的恢复入口。[S61] [S62]

## 05 / 保存内容，也保存它的来历

### 一份文件，不只是一串字节

假设要保存一份文档。原件可以放在 R2，目录与当前版本放在 D1：谁拥有它、对应哪个对象、大小和 hash 是什么、现在是否仍可读取。大对象与结构化状态分开之后，查目录不必每次加载原件。[S37] [S38]

| 要保存的东西 | 常见位置 | 为什么要留下 |
|---|---|---|
| 原件、媒体、导出 | R2／已有文件存储 | 以后能重新读取与处理 |
| 目录、权限、版本指针 | D1／已有数据库 | 知道当前哪一版有效 |
| 检索索引 | Vectorize／托管检索 | 帮助找到候选，而不是代替原文 |
| 备份与恢复说明 | 独立可取回的位置 | 原服务失效时仍能使用 |

这是建议的分工，不要求替换已有数据库。完整 SQL 示例保留在实施参考中。

### 更新、撤回与删除不要混成一个按钮

更新可以新增版本，再把当前指针切过去；撤回首先让内容不再对读者可见；物理删除才移除原件或派生数据。把三者分开，才能解释某个旧引用为什么存在，也更容易恢复误操作。

R2 bucket 默认保持私有，通过授权入口或有时效的访问方式取文件。对象 key 尽量使用不含真实姓名、邮箱等含义的标识；上传还要限制大小、类型和校验结果。生命周期规则先限定 prefix，避免一条清理规则影响所有历史对象。[S52]

### 备份应该回答“能恢复什么”

D1 Time Travel 有计划相关的保留期，原地恢复会改变数据库。执行前保存当前状态和目标 bookmark，明确要恢复到哪一刻。需要更长保留时，另行安排导出；数据库有虚拟表或全文索引时，还要核对导出、导入的当前限制，不能假定所有内容都能一条命令来回。[S50] [S51]

一个可用的演练是恢复到隔离目标，再检查代表性记录、原件 hash、版本与权限。数据库恢复成功但文件缺失，或文件齐全但权限回到旧状态，都不算恢复完了。

## 06 / 一次任务，可能执行不止一次

### 先想清楚用户在等什么

用户上传文档后，网页可以先显示“已接收”，后台再生成预览或索引。Queues 适合将接收与处理分开；Workflows 适合有多个步骤、等待与恢复的流程；Durable Objects 适合按实体协调；Cron 负责按时间触发。[S53] [S55] [S56] [S58]

不是每个应用都需要四种。一次短请求就能完成的事，可以继续直接执行。

### 为什么只记一个“处理过”会丢任务

考虑这样一段程序：先登记任务 ID，再做工作；重复收到同一 ID 就跳过。如果登记后进程退出，任务虽然“见过”，却永远没有做完。

反过来也有问题：外部动作先成功，登记之前连接断掉，重试可能再做一次。解决方法不是挪一行代码，而是留下任务现在处于什么状态。

<!-- figure: task-state -->

| 当前状态 | 人能读懂的含义 | 下次收到同一任务时 |
|---|---|---|
| 等待处理 | 已经收下，还没开始 | 可以领取 |
| 执行中 | 某次执行正在处理 | 先检查它是否仍有效 |
| 已完成 | 结果已核实保存 | 返回已有结果 |
| 可以重试 | 确认失败，再试不会扩大损失 | 受预算限制地重试 |
| 等待核对 | 外部动作结果未知 | 不盲目再做 |
| 已取消 | 后续执行不应再开始 | 保留取消事实 |

这些是本手册建议的状态，不是平台统一规定。实现中还需要区分不同 attempt：旧执行者即使迟到，也不能覆盖新一次的结果。租约过期只是恢复的一个条件，不证明旧程序已经停止。

### 数据库与队列之间留一个投递记录

写入数据库和发送队列是两件事。任务已写下、队列却没收到时，需要有地方看见这份待投递工作。常见做法是在同一次数据库提交里写任务和 outbox，再由投递器发送；重复发送由消费者的状态记录承接。

Outbox 可以理解为“准备寄出的任务清单”。它保住待投递意图，不保证所有系统恰好执行一次。清单本身也要能查积压、重试与终止。

Queues 可能重复投递；重试耗尽后，DLQ 可以保存需要调查的消息。Workflows 的步骤也可能重试，所以外部服务仍要有自己的幂等机制。[S53] [S54] [S55]

### 结果未知，应该有一个明确位置

服务商支持 idempotency key 时，一次逻辑动作使用同一个 key，并按其契约查询或重试。不支持幂等、也无法查结果的外部动作，超时后先标为等待核对。

离线示例 `examples/job-state/` 演示领取、迟到提交和未知结果的处理。上线之前，还需要注入真实失败：领取后退出、保存结果后丢 ACK、外部成功但客户端超时、取消与执行竞争。检查的是任务没消失、重复没扩大损失，而不只是成功路径能跑通。

Workflows 当前 Paid 包含每月 50 万步骤与 1 GB·月状态，步骤和存储自 2026-08-10 起计费；等待不计 CPU，不等于保留状态没有费用。Cron 使用 UTC，按业务日期工作的任务应明确时区与逻辑时间窗。[S44] [S56]

## 07 / 先找回原件，再组织答案

### 托管检索与自己的管线

AI Search 可以接管一部分摄取、分块、索引和检索；Workers AI 加 Vectorize 则让应用自己安排这些环节。前者省维护，后者留下更多可修改的接口。两者都应先接受同一组真实问题的检验。[S09] [S10] [S40] [S41]

准备一组小集合：精确术语、同义改写、模糊描述、旧名称、没有答案的问题，以及不该返回的内容。记录已知答案在哪里，不只挑五个漂亮结果展示。

10 月 GA 的 AI Search 已支持图片和 OCR。图片检索可用多模态路线，也可用文字描述路线；效果要用自己的材料比较。文件上限、字段数与模型条件仍需按本期来源核对。[S09] [S10]

### 让每个结果带着回原处的路

自建索引时，留下来源 ID、来源版本、chunk ID、内容 hash、embedding 模型和索引版本。升级模型建立新索引代，避免将不同语义空间里的向量混在一起比较。[S64]

读取身份决定允许查询的范围；候选返回后，再核对当前权限、撤回状态与版本，最后读取原文窗口。模型传来的 `owner_id` 不能替代服务器验证的身份。

AI Search 的 metadata filter 有字段数量和索引长度限制，复杂权限不能只靠一个任意长的字符串表示。细粒度内容需要明确分区与返回前的核验。[S10]

### 撤回不应该等待索引慢慢消失

内容撤回后，应用读取资格应立即变化；向量和派生缓存的清理可以成为后续可重试任务。更新时先准备新原件与索引，验证后再切当前版本，避免一半新、一半旧拼成一份材料。

Vectorize mutation 已被接受，不代表所有查询马上可见。按状态和实际读回确认，比固定睡一秒钟更可靠。[S64]

### 记忆比搜索多了一层问题

搜索问“哪里可能有相关材料”；记忆还要问“谁说的、何时有效、后来有没有更正、适用于谁”。这些条件不会由 embedding 自动补齐。

Cloudflare Agent Memory 当前仍是 private beta，与 AI Search 的 GA 分开看。取得接入前，不将它写成已可用依赖。[S60]

自己的记忆设计可以先保留自动抽取建议与原始来源，让人查看当前有效内容。测试旧偏好变更、同名人物、上下文冲突和明确禁止召回，比只测几条事实问答更能看见问题。

## 08 / 模型、路由与三种缓存

### 先弄清谁在回答、谁在计费

Workers AI 提供模型推理；AI Gateway 组织经过它的调用、凭据、观测与路由。通过 binding 或受控凭据，可以减少应用直接持有 provider key；Gateway 的访问资格本身仍是敏感能力。[S41] [S45] [S15]

先记录模型、时间、结果、token 和费用。确实需要正文调试时，再限定内容和保留期。首次创建 Gateway 在 2026-09-24 或之后的账户走新的 Workers Logs 规则；Unified Billing 充值另收 5%。[S15]

### 小判断可以比较三款模型，不必先换平台

Clef、Clef-flash 与 Jev 都可以从 Cloudflare 接入，但前两款是 CF 托管模型，Jev 是第三方 TypeSafe 模型。先挑一个明确判断：例如下一步读标题、读原文，还是材料不足。模型只提建议，程序按照允许的操作集合执行。[S17] [S18] [S73]

用同一份材料和题目比较，记录实际响应版本、错误、延迟与计费输入。第一轮不要同时换模型、换平台、改题目，否则不知道变化从哪里来。下一轮固定 Jev，再比较原厂、CF 或已有 Gateway，才是在比较接入路线。[S74] [S76] [S79]

有限输出免去了文字解析，却不会自动消除误判。Jev 文档说明 confidence 从概率分布计算而来；两个模型都返回 0.9，不证明它们在你的材料上有相同正确率。阈值应用单独的验证集合校准，数值、日期和权限规则能直接计算的部分交给代码。[S77] [S78]

<!-- facts: cf-routes -->
| 路线（接入 → 模型） | 模型选择器 | 输入 USD / 百万 token | 来源 |
|---|---|---:|---|
| Cloudflare → Jev | `typesafe/jev` | 0.042 | [S73](https://developers.cloudflare.com/ai/models/typesafe/jev/) |
| Cloudflare → Clef-flash | `@cf/cloudflare/clef-flash` | 0.09 | [S18](https://developers.cloudflare.com/workers-ai/models/clef-flash/) |
| Cloudflare → Clef | `@cf/cloudflare/clef` | 0.24 | [S17](https://developers.cloudflare.com/workers-ai/models/clef/) |
<!-- /facts -->

完整比较与可离线检查的请求形状，分别在 `comparisons/clef-vs-jev.md` 和 `examples/decision-routing/`。这些材料没有冒充真实推理验收。

### “缓存命中”究竟复用了什么

| 类型 | 复用的东西 | 需要确认 |
|---|---|---|
| 完整回答缓存 | 上一次的整份输出 | 内容与权限变化后是否仍有效 |
| Provider prompt cache | 可复用的输入前缀计算 | 命中条件由模型与提供商决定 |
| 应用结果缓存 | 自己计算的结构化结果 | key 是否带了用户、版本与配置 |

三者不能从同一个 `HIT`／`MISS` 推断。尤其是有新消息、实时状态或权限变化的对话，旧答案即使便宜，也可能已经不适用。

### 允许换模型的任务，再试 AutoRouter

AutoRouter 可在限定模型池中选择；beta 路由本身免费，推理照常计费。适合先放在可重试、错误可检测的小任务上，并记录实际命中模型。[S13]

User Insights 帮助查看流经 Gateway 的归属与成本，异常标记不自动阻止调用。它不能代替本地、订阅、直接 API 等其他使用记录。[S14]

### 有限选择可以单独试 Clef

Clef 系列适合分类、筛选和下一步建议，不一定要为一个小判断生成长解释。先准备正例、反例与无法判断项，让模型只提出建议，再看误判代价是否可接受。概率仍需在自己的材料上校准。[S16] [S17] [S18]

## 09 / 给机一间临时工作室

### 不同运行层，负责不同的事情

普通 API、字段变换与轻量计算可以留在 Worker。需要系统包、原生程序或完整 Linux 时再用 Containers。Agents SDK 提供身份、状态、连接与执行能力；它不是另一台 Linux 机器。[S58] [S59]

一次任务最好带着明确输入进入：哪个版本、允许做什么、预算多少、成果保存在哪里、怎样取消。临时执行者得到这次任务的能力，不必持有长期管理账户的钥匙。

### 1.0 要重新看生命周期

Sandbox 1.0 由应用自己的 Durable Object 控制 `ctx.container`。命令使用参数数组，每次指定工作目录和环境；新镜像未必含有旧镜像的全部工具，旧进程也不会因为 Worker 更新就自动替换。[S72]

网络能力同样需要按新版文档设置。将长期凭据留在控制层，只在获准请求上使用，比把它们写进镜像更易限制。配置后仍要测试实际允许与拒绝的访问。[S72]

### 做一次完整的小实验

选一个没有私人凭据的公开仓库版本，装好固定依赖，先跑确定性的检查。然后保存文件快照，从这份基线分出两个环境，各做一个小修改，交回补丁与结果。

快照只保存文件，不保存运行中程序，绑定镜像版本，当前 30 天保留期会在恢复时刷新。建立基线前清理不应被复制的材料与凭据。[S05]

需要历史的文件可用 Artifacts 保存，大型媒体可用对象存储。完成后关闭，再恢复一次：文件能否回来，旧任务有没有被误重跑，成果是否仍可读？这些才是“可恢复”的具体含义。[S07]

### 停下来也是任务的一部分

Containers 的 CPU 按实际活跃使用计，内存和磁盘按配置及运行时长计。执行两分钟、多等十分钟，不能仍按两分钟预算。停止容器也不会撤销已经发出的外部请求。[S06]

10 月的 DO pending-I/O 更新可保护部分等待操作，期间仍计时长费用；它不代替持久任务恢复。[S70]

Cloudflare OS 则适合观察更完整的文件、工具与工作空间。当前自部署源码和托管候补是两种状态，研究 Gatekeeper、导出与升级即可，不必立即承载关键工作。[S20]

## 10 / 发布以后，真的用一遍

### 检查哪一版，就发布哪一版

生产发布保留一条明确负责的路径：可以是 GitHub Actions，也可以是 Workers Builds；另一边提供检查或预览。这样不容易出现两个系统同时发布，或检查的是 A、上线的却是 B。

Workers Builds 当前 Paid 包含每月 6,000 分钟、6 并发，单次限 20 分钟；设备专属和不同操作系统的测试，仍放在对应环境。[S35] [S65]

### 预览也会使用真实资源

DO 与 Containers 当前支持部分预览自动隔离，其他资源要逐项看绑定。D1、R2、KV、队列、Vectorize 指向同一目标时，换一个 URL 并不会得到另一份数据。[S63]

外部 PR 用合成数据和独立测试身份，避免直接取得生产 token。测试结束也要清理预览文件、队列与临时资源。

### 从进入到离开，而不只看首页

Browser Run 可用于固定视口下的页面读取和操作。一个有用的检查过程是：进入、执行主要动作、保存、刷新、重开、取消，再故意触发一次错误。桌面与窄屏、键盘与触控都要考虑。[S36]

截图证明某一刻画面是什么样；导出后重新打开，才知道保存是否成立。两种证据都重要，不能互相替代。

Kitesurf 可以用于独立浏览实验，但不能代替最终目标浏览器。登录任务可以使用获准会话，没必要把整份个人浏览器资料交给临时环境；发布、支付等动作仍须有具体授权。[S19]

## 11 / 留下够用的记录

### 总耗时不够解释问题

一个搜索用了十二秒，可能慢在 embedding、索引、权限核验或生成。一次任务等了很久，也可能主要在排队，而不是执行。把时间分到阶段，才能知道值得改哪一段。

日常记录可以保持小：请求 ID、部署版本、动作、阶段、耗时、结果与重试次数。完整正文和堆栈按需要另行控制，不必每条请求都存下来。

### 给 Issues 一个无害的测试错误

Workers Issues 当前公开 beta 能关联失败、版本与源码材料，配置后只处理新流量。把开关写进项目配置，先制造一个没有敏感内容的错误，确认聚合和上下文，再连接 webhook 或修复工具。[S11] [S12]

第一步只生成调查与候选修复，也已经能减少维护劳动。Workers 看不到的本机、离线和外部路径，仍需自己的记录。

### 通知应该让人知道做什么

“CPU 有点高”不一定需要打断人；“任务队列已经超过可接受等待时间”更接近一个动作。为持续错误、积压、结果未知、成本变化和索引迟迟未就绪选择少量通知，并写清该看哪份材料。

## 12 / 算清持续成本

### 先按单位，再按美元

Workers Paid 最低每账户每月 $5，多项目共享包含量；R2、浏览器、模型、容器和日志各自计量，Zero Trust 也是另一种计划。启用 Paid 不等于取得所有企业功能。[S34] [S38] [S41] [S67]

| 使用形态 | 首先计量 | 容易漏掉 |
|---|---|---|
| 网站与少量 API | 动态请求、CPU、构建 | 日志和重复构建 |
| 资料库与检索 | 摄取、存储、查询、模型 | 重复分块、生成、旧索引 |
| 临时工作台 | 总运行时间、规格、模型 | 空闲、失败重试、产物保留 |

D1 计行，不只看 SQL 次数；R2 计对象操作；向量需要乘维度；队列还会因重试增加操作量；容器的空闲内存仍在运行时间里。这些单位比“每月应该只花几美元”更有用。[S06] [S37] [S38] [S39] [S40]

### 给每次实验记一笔小账

记录输入规模、次数、实际运行时间、资源与保留产物。先合并账户下的总用量，扣除一次共享包含量，再按项目分配观察。小规模便宜，不保证索引全量重建或重试风暴也便宜。

设定可以执行的停止条件：任务截止时间、最大并发、模型调用数、数据保留期。账单通知提醒趋势，不是全账户硬封顶。

### 免费也有三种含义

免费计划可能在达到上限后停止；Paid 包含量之外可能继续计费；beta 免费可能有未来起算日。Artifacts 的来源存在 10 月 14／15 日一天冲突，AI Search 新计费自 11 月 1 日开始，要把核验日与生效日同时留下。[S07] [S08] [S10]

普通 KV 与 KV Instant 也不能混看。后者面向特殊读重型负载，写入、删除、列举每次 $0.10，存储每 MB·月 $100，不适合作为普通个人状态库的默认选项。[S42] [S25]

## 13 / 坏了、恢复、暂时不用

### 沿着请求走，不同时改所有东西

| 看到的现象 | 先看这里 |
|---|---|
| 域名在不同设备解析不同 | DNS、代理、解析器与权威记录 |
| 302 到登录页 | Access 的应用与路径 |
| 403／401 | 响应来自边缘还是应用，再查对应身份 |
| 404 | hostname、路由、ingress 与对象是否存在 |
| 429 | 配额、限流与重试方式 |
| 5xx／超时 | 请求 ID、各阶段耗时、依赖健康 |
| 页面仍是旧版 | 实际部署、路由与浏览器缓存 |
| 任务有记录却没结果 | outbox、领取状态、租约与未知结果 |
| 容器文件消失 | 生命周期、镜像、快照与持久成果 |

状态码是线索，不是诊断。一次只验证一个原因，恢复后重新测拒绝路径，避免“能打开了”掩盖权限被顺手放宽。

### 让恢复目标具体一点

例如“把测试资料集合恢复到指定版本，不重新执行历史外部任务”。保留当前状态与备份身份，再验证记录、文件 hash、权限和待处理工作。恢复中遇到未知结果，就留下等待核对状态，不把它改成成功或未发生。

### 停用有一个顺序

先关闭新入口和自动触发，再处理执行中的任务；保存成果、撤销凭据，检查容器、浏览器会话、预览、队列和临时对象。最后按需要删除资源，或保留只读内容。

同时检查域名是否仍指向废弃服务，备份能否在不依赖原服务时读取，外部模型和日志是否还有保留设置。一项应用停止访问，不一定意味着所有关联费用都停止。

## 14 / 继续维护这份手册

### 保留问题，更新做法

历史教程提供了入口、身份、数据、任务和执行的分层。本期修正了几处会影响实施的地方：队列登记不等于任务完成；调用者标签不证明身份；快照不保存进程；Preview 不证明数据隔离。

平台状态则更新到本期快照：Sandbox 1.0 路线、AI Search GA 与新计费、Gateway 按首次创建日区分的日志规则、Cloudflare OS 托管候补。历史资料的继承范围见[来源说明](../docs/provenance.md)。[S72] [S09] [S10] [S15] [S20]

### 两种读者，不必挤在同一页

报告与本手册先让人理解用途、过程和取舍。实施参考保存精确字段、源码、命令、状态转移与失败检查；它可以更直接地给 agent 使用，却不能把文档当作部署授权。两层共用来源登记和例子，不各自维护一份互相漂移的事实。

| 需要什么 | 仓库入口 |
|---|---|
| 本期产品变化 | `reports/2026-10-02.md` |
| 人的阅读版 | `guides/handbook.md` |
| 实施细节、完整代码和状态约束 | `reference/implementation.md` |
| 离线示例与测试 | `examples/`、`tests/` |
| 来源、日期与变化记录 | `catalog/`、[来源说明](../docs/provenance.md) |

这里的检查分为资料与示例的本地验证、实际云端验证两类。本包包含前者，不包含账户登录、部署、迁移或模型实测。新的实践结果应按自己的输入、版本和范围补充，不无声地改写旧期判断。

<!-- SOURCES -->

## 来源索引

本次重新核对决策模型、接入路径与价格；其他发布条目沿用 2026-10-02 原版来源记录。资料核验不等于账户或模型实测。

- **[S02]** · cf CLI 发布
- **[S03]** · cf CLI 文档
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
- **[S25]** · KV Instant 私测与价格
- **[S34]** · Workers 价格
- **[S35]** · Workers Builds 限制与价格
- **[S36]** · Browser Run 价格
- **[S37]** · D1 价格
- **[S38]** · R2 价格
- **[S39]** · Queues 价格
- **[S40]** · Vectorize 价格
- **[S41]** · Workers AI 价格
- **[S42]** · KV 价格
- **[S44]** · Workflows 价格
- **[S45]** · Workers Bindings
- **[S46]** · Workers Static Assets
- **[S47]** · Cloudflare Tunnel
- **[S48]** · Access JWT 验证
- **[S49]** · Access Service Tokens
- **[S50]** · D1 Time Travel
- **[S51]** · D1 数据导出
- **[S52]** · R2 对象生命周期
- **[S53]** · Queues 重试与批处理
- **[S54]** · Queues 死信队列
- **[S55]** · Workflows 执行规则
- **[S56]** · Cron Triggers
- **[S57]** · Service Bindings
- **[S58]** · Agents SDK
- **[S59]** · Sandbox SDK
- **[S60]** · Agent Memory
- **[S61]** · Cloudflare Mesh
- **[S62]** · Split Tunnels
- **[S63]** · Workers 预览资源隔离
- **[S64]** · Vectorize Client API
- **[S65]** · Workers Builds
- **[S66]** · Workers 入门
- **[S67]** · Zero Trust 计划
- **[S70]** · Durable Objects pending I/O 保活
- **[S71]** · Workers OAuth Provider v1
- **[S72]** · Sandbox SDK 1.0 迁移差异
- **[S73]** · Jev：Cloudflare 第三方模型目录
- **[S74]** · TypeSafe：Jev 版本、价格与上下文预算
- **[S76]** · OpenRouter：Jev 的两种接口
- **[S77]** · TypeSafe：confidence 的含义
- **[S78]** · TypeSafe：Jev 1.13 已知能力边界
- **[S79]** · Cloudflare AI Gateway：统一 REST API

## 关于这一版

这是面向个人使用的独立参考资料，不是 Cloudflare 官方出版物。产品事实保留来源，场景与判断属于编辑分析。本次未进行账户操作或云端部署。

GitHub：[github.com/IndelibleVivi](https://github.com/IndelibleVivi)  
*made by Faye & Cove*

[S02]: https://blog.cloudflare.com/cloudflare-cf-cli-launch/ "cf CLI 发布"
[S03]: https://developers.cloudflare.com/cf/ "cf CLI 文档"
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
[S25]: https://blog.cloudflare.com/workers-kv-instant/ "KV Instant 私测与价格"
[S34]: https://developers.cloudflare.com/workers/platform/pricing/ "Workers 价格"
[S35]: https://developers.cloudflare.com/workers/ci-cd/builds/limits-and-pricing/ "Workers Builds 限制与价格"
[S36]: https://developers.cloudflare.com/browser-run/pricing/ "Browser Run 价格"
[S37]: https://developers.cloudflare.com/d1/platform/pricing/ "D1 价格"
[S38]: https://developers.cloudflare.com/r2/pricing/ "R2 价格"
[S39]: https://developers.cloudflare.com/queues/platform/pricing/ "Queues 价格"
[S40]: https://developers.cloudflare.com/vectorize/platform/pricing/ "Vectorize 价格"
[S41]: https://developers.cloudflare.com/workers-ai/platform/pricing/ "Workers AI 价格"
[S42]: https://developers.cloudflare.com/kv/platform/pricing/ "KV 价格"
[S44]: https://developers.cloudflare.com/workflows/reference/pricing/ "Workflows 价格"
[S45]: https://developers.cloudflare.com/workers/runtime-apis/bindings/ "Workers Bindings"
[S46]: https://developers.cloudflare.com/workers/static-assets/ "Workers Static Assets"
[S47]: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/ "Cloudflare Tunnel"
[S48]: https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/ "Access JWT 验证"
[S49]: https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/ "Access Service Tokens"
[S50]: https://developers.cloudflare.com/d1/reference/time-travel/ "D1 Time Travel"
[S51]: https://developers.cloudflare.com/d1/best-practices/import-export-data/ "D1 数据导出"
[S52]: https://developers.cloudflare.com/r2/buckets/object-lifecycles/ "R2 对象生命周期"
[S53]: https://developers.cloudflare.com/queues/configuration/batching-retries/ "Queues 重试与批处理"
[S54]: https://developers.cloudflare.com/queues/configuration/dead-letter-queues/ "Queues 死信队列"
[S55]: https://developers.cloudflare.com/workflows/build/rules-of-workflows/ "Workflows 执行规则"
[S56]: https://developers.cloudflare.com/workers/configuration/cron-triggers/ "Cron Triggers"
[S57]: https://developers.cloudflare.com/workers/runtime-apis/bindings/service-bindings/ "Service Bindings"
[S58]: https://developers.cloudflare.com/agents/ "Agents SDK"
[S59]: https://developers.cloudflare.com/sandbox/ "Sandbox SDK"
[S60]: https://developers.cloudflare.com/agent-memory/ "Agent Memory"
[S61]: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-mesh/ "Cloudflare Mesh"
[S62]: https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/configure/route-traffic/split-tunnels/ "Split Tunnels"
[S63]: https://developers.cloudflare.com/workers/previews/resources/ "Workers 预览资源隔离"
[S64]: https://developers.cloudflare.com/vectorize/reference/client-api/ "Vectorize Client API"
[S65]: https://developers.cloudflare.com/workers/ci-cd/builds/ "Workers Builds"
[S66]: https://developers.cloudflare.com/workers/get-started/guide/ "Workers 入门"
[S67]: https://www.cloudflare.com/plans/zero-trust-services/ "Zero Trust 计划"
[S70]: https://developers.cloudflare.com/changelog/post/2026-10-01-pending-io-keep-alive/ "Durable Objects pending I/O 保活"
[S71]: https://developers.cloudflare.com/changelog/post/2026-10-01-workers-oauth-provider-1x/ "Workers OAuth Provider v1"
[S72]: https://developers.cloudflare.com/sandbox/sdk/migrate/changes-in-1-0/ "Sandbox SDK 1.0 迁移差异"
[S73]: https://developers.cloudflare.com/ai/models/typesafe/jev/ "Jev：Cloudflare 第三方模型目录"
[S74]: https://docs.typesafe.ai/models "TypeSafe：Jev 版本、价格与上下文预算"
[S76]: https://openrouter.ai/docs/guides/community/jev "OpenRouter：Jev 的两种接口"
[S77]: https://docs.typesafe.ai/confidence "TypeSafe：confidence 的含义"
[S78]: https://docs.typesafe.ai/model-jaggedness/jev-1.13 "TypeSafe：Jev 1.13 已知能力边界"
[S79]: https://developers.cloudflare.com/ai-gateway/usage/rest-api/ "Cloudflare AI Gateway：统一 REST API"
