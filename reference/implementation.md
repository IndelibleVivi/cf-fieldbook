---
title: Cloudflare 实施参考
subtitle: 从一个入口到可恢复的应用与自动化
edition: 2026.10 · 修订 1
source_cutoff: 2026-10-02
author: Faye & Cove
github: https://github.com/IndelibleVivi
status: implementation-reference-snapshot
scope: 不含邮件；示例与实际账户分离
---

# Cloudflare 实施参考

**面向实施、审查与 agent 的完整技术材料 · 2026-10-02 状态快照**

本文件保留首版手册的详细实现说明、代码、恢复语义和来源；人的阅读入口在 `guides/handbook.md`。本次编辑分层不代表重新核验平台行为，也不构成云端部署记录。

个人基础设施的难处通常不是少一种服务。一个网站能打开之后，还要知道谁能写入、文件存在哪里、任务失败后怎么继续，以及几个月不用时是否仍在付费。本手册围绕这些工作展开，选择服务只是其中一步。

本版以既有《Cloudflare 用途盘点与实战教程》2026 年 8 月扩充版为主要编写底稿，参照 7 月版结构，并用截至 **2026-10-02** 的官方文档重查产品行为。保留其入口、身份、数据、执行和恢复分层，重新编写操作路线；旧教程中的实际部署叙述不转换成本手册作者的实测声明。邮件服务另行讨论，不纳入本版。

这里有三种不同证据：官方平台事实；本手册提出的设计与检查；随包示例的本地测试。附件包含 health Worker、离线任务状态模型、费用演算和 PDF 重建工具。**本地测试不代表云端验收。** 本版未执行账户登录、部署、迁移或模型调用；接手实施时仍需补真实绑定、远端正负向测试、预算与恢复演练。

## 01 / 选择一条读法

| 你现在的位置 | 先读 | 暂时可以跳过 |
|---|---|---|
| 想发布一个网页或小 API | 第 2–4 章：分层、准备、最小 Worker | 队列、容器、记忆和私网 |
| 已有本机或 VPS 服务，想安全访问 | 第 5–6 章：身份和 Tunnel | 重写现有后端 |
| 已经在保存用户内容与文件 | 第 7 章：D1、R2、备份与恢复 | 托管搜索、agent 工作台 |
| 自动化经常超时、重复或丢任务 | 第 8 章：任务与外部副作用 | 多模型路由 |
| 想做文档检索、记忆或 agent 执行 | 第 9–11 章 | 大规模事件流和数据湖 |
| 系统能运行，但维护越来越累 | 第 12–15 章：发布、观测、故障、退出 | 新服务的试用申请 |

本期新发布的逐项状态与价格时间线见配套《Cloudflare 新发布观察》。手册解释如何实施；报告解释为什么近期变化值得重新评估。两份文件都能单独阅读。

## 02 / 先把请求、数据与任务画在不同位置

Cloudflare 的服务可以组合，但一个应用不必走遍全部层次。先用下表记录职责，往往比画几十个产品图标更有帮助。[S45] [S47] [S58] [S59]

| 需要安排的职责 | 常见选择 | 一定要留下的决定 |
|---|---|---|
| 用户从哪里进入 | DNS、Custom Domain、Workers、Tunnel | hostname、目标服务、备用入口是否公开 |
| 哪个身份能进入 | Access、人类登录、Service Token | 验证主体、有效期、撤销方式 |
| 进入后能做什么 | 应用角色、资源权限、动作授权 | 读写范围和高风险操作边界 |
| 结构化状态存在哪里 | D1、现有数据库、按实体划分的 DO | 谁负责写入和修订 |
| 文件存在哪里 | R2、现有对象或文件存储 | 对象生命周期、访问权限、导出方法 |
| 工作何时完成 | 直接请求、Queues、Workflows | 接收与完成的区别、失败恢复 |
| 哪些计算需要完整环境 | Workers、Dynamic Workers、Containers | 原生依赖、资源、出站网络与超时 |

一种常见的、小型应用形态是：浏览器访问 Worker；Worker 处理应用权限，使用 D1 保存目录与状态，使用 R2 保存文件。另一种同样合理的形态是：Access 和 Tunnel 只负责访问入口，应用与数据库继续留在原来的服务器。平台能力增加，不构成迁移现有状态的理由。

**绑定（binding）是部署时交给代码的能力。** `env.DB` 或 `env.FILES` 已指向配置好的资源，代码通常不必再携带管理这些资源的账户 API key。控制面 token 用于创建和部署；运行时 binding 用于应用访问；最终用户权限仍由应用协议决定。这三类权限不应混成一个万能密钥。[S45]

Service Binding 可以让 Worker 调用指定的另一项服务，减少公开入口和复制凭据。设计内部接口时，仍要限制操作和输入。客户端随便提供一个 `x-service-id` 字符串不证明身份；可靠的调用者身份应来自受控部署关系或实际校验的凭据。[S57]

## 03 / 动手之前：账户、预算、秘密信息

### 套餐是账单边界，不是架构图

Workers Paid 当前最低为每账户每月 $5，多项目共用相应包含量。R2、模型、浏览器、容器、日志等各有计量维度；Zero Trust 也是自己的产品计划。付了 Workers Paid 不等于买下全部企业功能。[S34] [S38] [S41] [S67]

先在私人记录里写下：允许新增哪些收费服务；一次实验最多运行多久、多少并发；临时数据保留几天；何时停止入口；由谁查看账单。这里的数字是自己的预算，不是宣称 Cloudflare 提供全账户硬封顶。通知只能提醒，应用还要设置实际限制。

对于第一次实验，成本控制最好落在能直接验证的地方：请求大小、每任务最大模型调用次数、容器总运行时间、浏览器会话超时、队列最大重试、产物保留期。不要只靠“流量应该不大”。

### 凭据按用途拆开

交互式开发可以使用工具提供的登录流程。CI 使用限定资源、限定权限的凭据，不把全局 API key 放进每个仓库。前端代码、打包产物、客户端环境变量都按公开内容处理；名称里带 `SECRET` 不会让浏览器里的值变秘密。[S03] [S45] [S66]

建议给开发、预览与生产建立清楚的资源映射。测试数据库和生产数据库都叫 `DB` 没问题，但其绑定目标必须不同。真实 Account ID、域名、bucket 和策略保存在私人配置或受控环境，不复制进公开手册。

创建资源前看一遍将要发生的远端写入。部署、创建数据库、应用迁移、恢复历史、删除对象都是不同操作；不能因为同在一个命令列表里，就默认整串命令都已获准执行。

### 保留可回来的一条路

在调整 Access、Tunnel、客户端路由或 DNS 前，确认还有不依赖待改路径的管理入口。准备好旧配置、当前版本与恢复步骤。不要通过唯一的远程会话，同时替换 DNS、私网客户端和服务器防火墙。

## 04 / 路线 A：先发布一个很小、能验证的 Worker

本节使用一个无账户依赖的小例子。它只响应健康检查，不连接数据库、不调用模型、不接受用户写入。运行测试只需要支持 Fetch API 的 Node.js；实际部署另用项目中固定版本的 Cloudflare 工具。[S66]

随包目录 `examples/health-worker/` 包含源码、配置模板和测试。下面的代码与该目录一致：

```js
const HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
};

function reply(body, status, head = false, extra = {}) {
  return new Response(head ? null : JSON.stringify(body), {
    status,
    headers: { ...HEADERS, ...extra },
  });
}

export default {
  async fetch(request) {
    const head = request.method === "HEAD";
    const path = new URL(request.url).pathname;
    if (path !== "/health") {
      return reply({ error: "not_found" }, 404, head);
    }
    if (request.method !== "GET" && !head) {
      return reply({ error: "method_not_allowed" }, 405,
        false, { allow: "GET, HEAD" });
    }
    return reply({ ok: true, schema: "health/1" }, 200, head);
  },
};
```

它故意不回显请求头、上游地址、环境变量和私有版本标识。健康响应只证明请求到达了这个 handler，不证明数据库、文件服务和所有依赖都正常。

### 第一步：本地检查，不联网

在仓库根目录运行：

```bash
node --test examples/health-worker/worker.test.mjs
python3 tools/check.py
```

这是纯函数和资料一致性检查。测试不启动 Cloudflare，也不验证实际网络。

### 第二步：明确选择开发工具

当前 `cf` CLI 在公开 beta，Wrangler 仍受支持；维护期计划至少延续到 `cf` GA 后 18 个月。既有项目不必为了尝鲜立刻改配置。首次试验可以沿官方脚手架选择工具，并把实际采用的版本和锁文件留在项目里。[S02] [S03] [S66]

配置模板如下，包含的是合成名称：

```json
{
  "name": "health-lab",
  "main": "index.mjs",
  "compatibility_date": "2026-10-01",
  "workers_dev": false,
  "preview_urls": false
}
```

这个模板故意没有生产路由。只有绑定自己的测试 Custom Domain，或在确认服务可公开后主动启用开发入口，远端请求才应到达它。不要把禁用默认入口误读成部署失败。

采用 Wrangler 的项目，可以在安装并固定版本之后，于示例目录执行以下流程。`deploy` 会修改远端，只在目标账户和测试路由已经核对后运行：

```bash
npx --no-install wrangler dev --port 8787
# 另开终端，只测本地：
curl -i http://127.0.0.1:8787/health
curl -i http://127.0.0.1:8787/missing

# 以下是另外一次、明确的远端操作：
npx --no-install wrangler deploy
```

`--no-install` 的用途是避免命令临时下载一个与项目锁定版本不同的工具；缺少依赖时应停止并完成安装，而不是不断换命令直到“能跑”。本包没有伪造一份未安装过的 Wrangler 锁文件。

### 第三步：用不同方向的请求验收

| 请求 | 预期 | 能证明什么 |
|---|---|---|
| `GET /health` | 200，固定 JSON | 正确路由和 handler 可用 |
| `HEAD /health` | 200，无正文 | HEAD 行为符合约定 |
| `POST /health` | 405，含 Allow | 不把任意方法当作健康检查 |
| `GET /missing` | 404 | 未知路径没有落入宽泛 handler |
| 故意带伪造私有头 | 响应仍不含这些内容 | 不发生请求信息回显 |

域名与 TLS 另行检查。浏览器打开成功只是一条样本；建议再用命令行和不同网络核对，特别是本机有代理、VPN 或自定义 DNS 时。

### 加上前端资源时

Workers Static Assets 可以与 API 一起部署。确定资源优先还是 Worker 优先，以及 SPA fallback 是否会把未知 API 路径错误变成 `index.html`。静态资源免费规则与动态请求不同；启用 Workers Caching 等特定功能时还要重查请求计费，不能把“静态页面”当作永远零计费的属性。[S46] [S34]

私有 PWA 的离线能力要更谨慎：退出登录后仍留在 Service Worker 缓存里的数据可能继续可读。最简单的起点是只缓存公开壳，私有 API 使用 `no-store`，并实测注销、切换用户和旧版本更新。

## 05 / 路线 B：把“能到达”与“有权使用”拆开

### 浏览器管理台：Access 提供身份，应用决定权限

Access 可以保护一个内部 hostname 或明确路径。先选择真正需要的身份来源与允许用户，再配置合理的会话期限。应用依赖 Access 身份时，要验证 JWT 签名、issuer、audience 和有效期，而不是检查 `Cf-Access-Jwt-Assertion` 这个头是否存在。[S48]

不必无条件再叠一串 bearer token。若验证后的 Access 身份已经成为可靠的应用 principal，接下来应做角色和资源授权。需要另一份凭据的理由，应是机器作用域、单独撤销或更强动作确认，而不是“层数多看起来更安全”。

Cookie 会话的写请求还要考虑 CSRF 与 Origin。对未通过校验的请求在读取私有内容之前拒绝；不能先读完整对象，再靠 UI 隐藏不允许的按钮。

### 自动化客户端：每个用途有可撤销身份

Service Tokens 适合机器通过 Access，不需要模拟人类登录。单独签发、设有效期并保留撤销路径。Service Auth 通过之后，应用仍要把该机器映射到允许的操作和数据范围。[S49]

不要把包含真实 token 的 `curl` 命令放进聊天或终端历史。把凭据放入受控的配置、系统 secret store 或执行环境，并防止进程调试和日志输出它们。测试记录只需写凭据身份标签、测试时间和通过/拒绝结果。

### 所有替代入口都要检查

保护 `admin.example.com` 并不会自动证明 `workers.dev`、另一条 Custom Domain、预览地址和源站 IP 都已受保护。列出所有可达路径，逐一匿名访问。只需要一个公开 webhook 时，让那个精确入口执行签名、时效和重放检查，不要顺手公开整个管理面。

| 身份与路径组合 | 期待结果 |
|---|---|
| 匿名访问私有页面 | 登录挑战或明确拒绝 |
| 允许用户访问 | 成功，并映射正确应用角色 |
| 已登录但未获资格的用户 | 仍然拒绝 |
| 过期或被撤销的机器 token | 不能读取旧权限下的数据 |
| 伪造 Access JWT / 错 audience | 验证失败 |
| 默认开发域名、邻近路径、直连源站 | 不绕过既定边界 |

### 远程 MCP 不要被登录页面卡住

浏览器网页登录与 MCP 的 OAuth 发现、授权和 token 校验不是同一协议。10 月发布的 Workers OAuth Provider v1 提供授权服务与资源服务分离、范围升级等能力，可作为自建服务的实现候选。[S71]

部署时要决定哪些发现和授权入口需要客户端可达，哪些资源调用必须携带正确 token。检验错误受众、过期令牌、撤回资格和跨资源请求。不要为了让客户端连接成功，把所有 MCP 工具改成匿名访问；也不要把一个成功 OAuth 页面等同于全部工具权限正确。

## 06 / 路线 C：已有服务器继续运行，Tunnel 只改变入口

Tunnel 是源站上的连接器主动连接 Cloudflare，再把请求交给指定本地服务。它不托管应用、不备份本地磁盘，也不会在笔记本关机后继续运行那台机器上的程序。[S47]

**先查本地，再查外网。** 本地应用应先能在预期的回环或受控接口上工作。确认端口与当前进程，再创建命名 Tunnel，配置 hostname 和 ingress，必要时叠加 Access，最后做外部正向和反向测试。

以下是结构示例，不含真实 tunnel identity：

```yaml
ingress:
  - hostname: app.example.com
    service: http://127.0.0.1:8080
  - service: http_status:404
```

这里的 8080 只是测试端口，必须换成应用实际监听地址。最后的 404 兜底不替代防火墙；源站若同时在另一公网端口公开服务，仍可能绕过入口。

建议把验收按五段记录：本机 HTTP 响应；连接器运行状态；Tunnel 健康；hostname 命中正确服务；Access 与应用权限。某段失败时保持其他配置不变，一次只修一个原因。

Quick Tunnel 适合临时试验；长期使用应选择可管理的命名入口。后台连接器的开机启动、日志轮转、升级与停用也要有说明。一个持续运行的进程，维护责任仍然属于设备或服务器侧。

### 与设备私网的区别

Cloudflare One Client / WARP 是终端接入和流量策略；Mesh 连接加入组织的设备与私网；Tunnel 发布被明确选择的服务。当前 Mesh 仍有 beta 标识，不应成为没有替代方案的唯一灾难恢复入口。[S61]

与现有 VPN 共存时，先在非关键设备观察默认路由、DNS、虚拟接口与私网路径。Split Tunnel 的 IP 排除不自动证明 DNS 也走原来的解析路径，应按客户端实际配置检查。面向个人的小型环境，不需要为了使用 Cloudflare 服务而同时换掉已经稳定的网络层。[S62]

## 07 / 数据：保存内容，也保存重新解释它的条件

### D1 与 R2 的分工

D1 适合结构化目录、任务状态、版本、约束和查询；R2 适合原件、媒体和导出文件。数据库里存对象 key、hash、大小、权限与来源，通常比把大对象塞进每一行更容易维护。D1 按读取/写入的行计量，索引会影响性能和写入成本；R2 还计存储与对象操作。[S37] [S38]

下面是本手册提出的最小文档目录模型，不是平台要求。它把撤回与物理删除分开，也把当前版本与原始对象分开：

```sql
CREATE TABLE documents (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  current_revision INTEGER NOT NULL CHECK(current_revision > 0),
  state TEXT NOT NULL CHECK(state IN ('active','withdrawn'))
);

CREATE TABLE document_versions (
  document_id TEXT NOT NULL REFERENCES documents(id),
  revision INTEGER NOT NULL CHECK(revision > 0),
  object_key TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  byte_size INTEGER NOT NULL CHECK(byte_size >= 0),
  created_at TEXT NOT NULL,
  PRIMARY KEY(document_id, revision)
);
```

写新版本时使用比较并交换：只有 `current_revision` 仍等于用户开始编辑时的值，才提交新版本。否则返回冲突，让调用者重读，而不是让较旧页面覆盖新内容。用数据库实际支持的原子操作实现，不把几次独立网络请求假装成一个事务。

### R2 权限与文件处理

先保持 bucket 私有，通过应用验证资格再返回对象，或签发用途明确、时长合适的访问凭证。不能把难猜的对象 key 当作完整授权；撤回访问之后，既发出的有效链接和客户端缓存也可能需要处理。

上传限制大小、类型和内容，不能只信文件扩展名。对网页可执行内容使用合适的下载策略或隔离域名，避免把上传文件当作主应用可信页面。为原件保留摘要、字节数和对象身份，读取时才能检查内容有没有换掉。

生命周期规则先限到特定 prefix，再核查会影响已有的哪些对象。临时预览、依赖缓存、正式成果和备份分别设保留规则，避免一条“清理旧文件”把长期成果一起删掉。[S52]

### 不要用一个“备份成功”覆盖所有情况

D1 的 Time Travel 提供时间点恢复，但保留期与计划有关；Paid 当前为 30 天。回到过去会改变目标数据库，不能直接在生产上试试看。操作前先读当前 bookmark，确认目标、时间和受影响数据，再在替代环境验证恢复流程。[S50]

SQL 导出另有实际限制。当前 D1 不直接接收原始 SQLite 文件；导入的是符合 D1 条件的 SQL。包含虚拟表、例如全文索引的数据库还存在导出限制。不要为导出方便临时删掉生产全文表；可以设计应用级原始数据导出，并让可派生的全文索引在恢复后重建。[S51]

一次有用的恢复演练，应能回答：目录版本是否正确；每个对象是否存在且 hash 一致；当前权限是否恢复；可派生索引如何重建；尚未完成的任务是否会误重复执行。导出文件存在只是开始。

**代码回滚与数据回滚分开。** 新版本已经写入新字段或发出外部操作之后，回退 Worker 代码不会撤销这些事实。迁移优先采用旧新版本都能读取的过渡结构，再择期清理；涉及不可逆删除时保留单独操作与确认。

## 08 / 自动化：接收成功、执行成功、结果可见各有自己的状态

### 先选择最少的一种编排

Queues 解决接收与消费解耦、削峰和重投；Durable Objects 适合按实体协调；Workflows 适合多步骤恢复、等待事件或较长间隔；Cron 负责按时间触发。普通短请求不必全套使用。[S53] [S55] [S56] [S58]

队列是至少一次投递的工作环境，不能因为常见请求只收到一次，就把 consumer 写成单次运行程序。DLQ 是重试耗尽后的存放与调查入口，仍需要有人或程序处理；未配置时要认真确认消息在重试耗尽后的行为。[S53] [S54]

### 一个常见陷阱：去重记录比工作先完成

旧教程采用过这样的简化流程：先登记 `event_id`，发现已经登记就直接 ACK，否则执行工作。如果登记之后、工作之前进程退出，下一次投递看见“已登记”就跳过，任务永远丢失。

相反，工作做完才登记也不充分：外部操作成功、登记前断网，会在下一次投递时重复操作。问题不能靠把一行代码上下移动来解决，需要保存工作处于哪种状态。

以下是建议的任务模型：

| 状态 | 事实含义 | 再次投递时的处理 |
|---|---|---|
| `pending` | 已持久接收，尚未领取 | 可以竞争领取 |
| `running` | 被某个 attempt 领取，租约有效 | 不并发启动相同工作 |
| `done` | 所需结果已核实并提交 | 可以安全 ACK |
| `retryable` | 已知失败，重试不会扩大损失 | 按退避和预算重试 |
| `uncertain` | 外部结果不能确认 | 停止盲重试，先核对 |
| `cancelled` | 取消已生效，后续执行不应再开始 | 返回取消状态，不假装完成 |

领取与状态变化应当是原子的。每次领取有递增 generation 或不可复用的 attempt token；旧执行者即使迟到，也不能提交覆盖新执行者。租约过期只是允许考虑恢复，不证明旧执行者已经停止，更不证明外部操作没有发生。

### 数据库与队列之间也有一个缝

“向数据库写任务，再发队列”涉及两个系统。写任务后断网，队列可能没收到；先发队列后写任务，消费者可能看不到任务。建议在数据库的同一原子提交中写任务和 outbox，然后由投递器发送 outbox；发送后的标记失败可以造成重复投递，由 consumer 的任务状态处理。

这保证的是待投递意图不会悄悄消失，不是跨服务 exactly-once。Outbox 本身也要有有界批次、重试、过期和检查积压的入口。

### 外部副作用需要自己的幂等边界

对于支持 idempotency key 的服务，将一次逻辑操作的稳定 key 传给服务商。响应丢失后，优先使用同一 key 查询或重试，而不是创造一个新 key。对不支持幂等、结果又不可查询的操作，在发送超时后进入 `uncertain`，交给明确的核对流程。

付款、对外发布、删除和通知都可能遇到这个问题。Workflow 记住某个步骤，并不把外部服务也变成同一事务；平台的自动重试是机制，不是执行不可逆动作的许可。[S55]

### 设计一轮故障注入，而不是只看成功路径

在合成数据上分别模拟：接收后未发队列；领取后退出；结果已写入但 ACK 丢失；外部服务成功但客户端超时；旧租约持有者迟到；取消与执行竞争；重试耗尽进入 DLQ。验收目标不是“每次都成功”，而是任务没有消失、重复没有扩大副作用、未知状态可以找到。

Workflows 当前按请求、CPU、存储与步骤计费，步骤和存储计费自 2026-08-10 开始；等待网络或 sleep 不计 CPU，但保留状态仍有存储维度。Paid 包含每月 50 万步骤和 1 GB·月状态；不能沿用早期“整个工作流免费”的印象。[S44]

Cron 使用 UTC。业务想按当地日期执行时，把时区与夏令时语义明确写在任务定义里。每次触发携带逻辑时间窗，例如“处理上一个已结束日期”，避免重触发产生两份不同身份的同日任务。[S56]

## 09 / 检索与记忆：先让人找回原件，再让模型组织答案

### 两条路径分别解决不同问题

AI Search 负责托管摄取、索引与检索；Workers AI + Vectorize 则让应用自己控制分块、向量、召回与核验。前者减少运维，后者保留更多可实验的环节。已有检索能满足需求时，不需要仅因新产品 GA 就迁移全部资料。[S09] [S10] [S40] [S41]

无论选哪一条，都先准备一组实际查询与已知答案位置。例如：精确术语、同义改写、模糊记得的描述、旧版本名称、找不到的内容、没有权限的内容。只展示五个漂亮结果，无法说明系统是否适合日常。

### 路线 D：公开或获准使用的文档集合

建议先选 20–50 份可公开的材料。为每份材料保留稳定 ID、来源、版本、获取日期和读取许可。去掉导航噪声、重复导出和错误编码之后，再决定分块边界。不要把“成功导入”当作内容已经完整。

若使用 AI Search，选择适合输入的 embedding 与处理路线，再检查摄取状态、解析结果和真实查询。10 月 GA 已支持图片与 OCR；视觉输入和纯文本描述的效果要用同一组问题对照，不把“支持图片”误写成“理解一切构图”。具体文件大小和模型条件以当前文档为准。[S09] [S10]

若自建 Vectorize，记录 `source_id`、`source_revision`、`chunk_id`、内容 hash、embedding 模型和索引版本。不同模型不只可能维度不同，即使维度相同也未必处在同一语义空间。模型升级应建立新索引代，而不是把新旧向量混写后继续比较分数。[S64]

### 检索结果不能自己决定访问资格

一个建议的读取链路是：

| 阶段 | 输入 | 必须保留的条件 |
|---|---|---|
| 确定读取身份 | 经验证的 principal | 用户、组织、集合与授权范围 |
| 建立候选查询 | 关键词、向量或混合查询 | 尽可能先限制允许的数据范围 |
| 回查当前记录 | 候选 ID 与版本 | 当前资格、撤回状态、有效版本 |
| 读取原文窗口 | 获准的 chunk 或对象引用 | 可回到原件的定位与有限输出量 |
| 生成或整理 | 已核验的材料 | 答案与来源关联，缺失可见 |

过滤条件应该由服务器从授权身份推导，而不是信任模型传来 `owner_id`。远端索引命中只能提供候选，不能成为“这个人仍然有权读”的证据。缓存和分页同样要绑定读取主体和数据版本。

元数据过滤通常还有字段数量、字符串长度等限制。例如 AI Search 当前过滤字段有数量及索引长度约束；把任意复杂 ACL 编成一个长字符串不等于可靠过滤。复杂权限应选择明确的分区策略，并在返回内容前进行本地或权威记录核验。[S10]

### 更新和撤回要有两种速度

立即生效的应当是应用读取资格：内容撤回后，任何查询都不能再返回该正文。向量与派生缓存的物理清理可以作为可观察、可重试的后续任务，记录何时完成。不要要求用户等待索引重建才真正撤回内容。

更新原文时，先准备新对象与索引，验证可读和版本匹配，再让当前指针切到新代。失败时继续读旧的有效代，或明确报告不可用；不应把一半旧 chunk 与一半新 chunk 混成完整材料。具体实现可以简化，但切换的原子边界要清楚。

Vectorize 的 mutation 成功并不保证所有查询立刻可见。写入后按文档提供的状态与实际读回验证，不靠固定睡一秒钟建立正确性。[S64]

### 记忆还多了修订、来源与适用范围

文档搜索回答“哪里可能有相关材料”，记忆还要回答“这句话何时有效、是谁说的、后来有没有修改、适用于哪个人或项目”。这些问题不是换一个 embedding 自动解决的。

Cloudflare Agent Memory 当前仍为 private beta，与 AI Search 的 GA 状态分开。它提供 namespace/profile 及摄取、抽取、召回等能力，可以作为候选，但不能在未获得权限时写成已可用依赖。[S60]

建议把自动抽取先放在建议层，保留来源引用；更正与撤回不直接删除所有历史解释；用户能够查看当前有效视图，也能追溯为什么某条内容曾被保留。用“明确禁止召回”“旧偏好后来变更”“不同人物同名”“不同上下文相反”作为测试，而不只测事实问答。

### 检索的成本也要按阶段观察

分别记录摄取、embedding、候选查询、重排、原文核验和生成耗时。AI Search 11 月新计费把内部 embedding、重排与存储等纳入服务规则，但生成与外部模型仍需另看；自行使用 Workers AI + Vectorize 则仍按各产品计费。[S10] [S40] [S41]

若一个搜索需要十几秒，先看各阶段，而不是立刻换模型。重复生成查询向量、串行权限查询、取回过大上下文、冷启动和远端超时都可能占时间。保留“只检索、不生成”的基线，才能知道生成式回答增加了多少延迟与收益。

## 10 / 模型调用：先知道谁在付费，再决定谁来回答

### Gateway 是流量控制面，不是另一个模型

Workers AI 运行模型；AI Gateway 位于应用与支持的模型服务之间，组织身份、观察、路由与费用。通过绑定或受控凭据可以减少业务代码直接持有 provider key，但访问 Gateway 的资格本身仍然是敏感权限。[S41] [S45] [S15]

新入口接入时先只记录请求 ID、模型标识、耗时、状态、token 与费用。需要保存正文做调试时，限定数据范围和保留期，允许关闭。不要默认把私有图片、完整对话、工具结果与访问令牌一起写入可长期搜索的日志。

首次 Gateway 创建于 2026-09-24 或之后的新客户，日志采用 Workers Logs 的新规则。Unified Billing 购买 credits 当前加收 5%；“统一入口”不代表模型推理免费或所有日志都在 $5 基础费内。[S15]

### 三种缓存分别处理

| 缓存类型 | 复用什么 | 主要风险 |
|---|---|---|
| 完整回答缓存 | 之前生成的整份输出 | 最新数据与权限改变后仍返回旧答案 |
| 提供商 prompt cache | 模型可复用的输入前缀计算 | 命中条件依提供商与模型，不等同于 HTTP 缓存 |
| 应用结果缓存 | 已计算的结构化业务结果 | 缓存 key 缺少用户、版本或配置维度 |

这是设计上的区分。一个 Gateway `MISS` 不能证明提供商没有利用输入缓存；一个完整回答命中也不能证明结果仍适用于当前任务。缓存 key 与失效规则应随数据权限和版本一起设计。

### AutoRouter：只在允许改变模型的地方用

AutoRouter 在允许的候选模型中为请求路由。beta 期间路由本身免费，实际推理照常计费。把模型池写成配置，记录实际命中模型；关键任务保存足够的重现信息。[S13]

先选择可重试、错误可检测的任务，例如草稿分类或简单转换。固定模型的实验、依赖特定输出格式的管线，以及需要稳定行为的长期会话，不应悄悄加入通用自动池。

User Insights 可以帮助按归属观察请求和成本，但只能看见流经 Gateway 的部分；异常标记不会自动阻止调用。聚合成本需要明确区分本地模型、订阅内使用、直接 API 与 Gateway 请求，避免一份图表显得很完整，实际漏掉大部分费用。[S14]

### Clef：有限选择可以先做成低风险建议

Clef 系列输出定义好选项的概率，适合分类、选择或排序任务。它可用于决定“下一步还需不需要更多材料”，不需要为每次小判断生成长段解释。模型输出概率仍需在自己的材料上校准，不能直接当正确率。[S16] [S17] [S18]

一种有用的试验是：准备真实正例、容易混淆的反例与无法判断项，先让它只推荐，不实际触发外部动作。统计漏判和误判的不同代价，再决定是否接入流程。关键不在它能不能给出一个选项，而在错的时候是否可见、可纠正。

## 11 / Agent 执行：持久身份、Linux 环境与文件历史分开

### 哪些事情留在 Worker，哪些交给容器

普通 API 变换、字段检查和轻量计算先考虑 Worker；需要完整 Linux、系统包、原生依赖或多语言命令时再考虑 Containers。Agents SDK 提供基于 Durable Objects 的身份、状态、连接与执行能力；它不是完整 Linux，也不替代应用自己的权限和任务语义。[S58] [S59]

为一次任务明确记录：输入版本、允许操作、模型配置、运行环境、资源预算、持久结果位置、取消方式。临时执行者拿到的是这次任务的能力，不是长期管理整套账户的权力。

### Sandbox 1.0 的关键变化

当前 1.0 迁移路线不再沿用旧版万能 `Sandbox` 类。应用通过自己的 Durable Object 控制 `ctx.container`；命令以参数数组执行，每次独立指定工作目录和环境。新系统镜像不保证包含旧版内置的所有工具；文件 helper 和特殊集成也可能要求相应 shim。[S72]

这使隔离层次更清楚，但开发者需要显式处理生命周期。部署新 Worker 不等于替换已运行的容器；旧进程和新代码并存时，协议与镜像版本必须能够兼容，或在有控制的停机后重启。

1.0 默认的容器出站能力与旧版不同，应按文档显式选择网络设置或受控 outbound handler。把第三方凭据保留在 handler 之外的控制层、在允许的请求上注入，比把长期密钥写进镜像更容易限制。这个机制仍要经过实际访问测试，不能只看配置写了“deny”。[S72]

### 路线 E：一次可以关闭、恢复和比较的执行实验

选一个无私有凭据的公开仓库版本，在自定义镜像或准备阶段安装准确依赖。第一次只执行确定性的构建或检查，不同时引入自动选模型、互联网自由浏览和生产写权限。

准备完成后保存文件系统快照。它绑定镜像版本，只保存文件，不保存内存与运行中的程序；当前 30 天期限会在恢复时刷新。若快照包含凭据、下载的私有材料或本地工具配置，这些内容也会被一起保存，应在建立基线前清理并核查。[S05]

从基线生成两个环境，分别做一个有限修改，交回补丁、测试输出和可保存产物。需要留历史的文件可以进入 Artifacts；大型媒体可进入对象存储。正式源码是否接受这些修改，仍走原来的审阅过程。[S07]

完成后关闭执行环境，重新启动并恢复，确认：输入与镜像身份正确；结果可读；旧任务不会自动重复；临时凭据已失效；成本指标反映了实际运行时长。只有这轮通过，“可恢复”才有具体含义。

### 休眠时间也属于费用

Containers 的 CPU 按实际活跃使用计量，内存和磁盘则按分配配置与运行时长计量。任务两分钟做完，但实例多运行十分钟，不能仍按两分钟预算。模型、DO、网络与日志也可能另有费用。[S06]

为容器建立独立的任务截止时间和关闭策略。一次命令取消可能已改变文件；向外部 API 发出的请求可能已经成功。停止容器不是撤销过去副作用，取消结果需要诚实保留。

### 不要把临时保活理解为可靠后台任务

10 月的 DO pending-I/O 更新可以让部分仍在等待的操作继续阻止空闲回收，保护存在时仍计时长费用。它不保证从崩溃中恢复，也不保证整段业务只执行一次。需要可接续的工作，用持久任务记录或 Workflow 保存可恢复状态。[S70]

### 什么时候看 Cloudflare OS

当目标确实是文件、工具、上下文与多个可修改应用组成的工作空间时，Cloudflare OS 值得研究。当前自部署源码与托管候补是两回事。先检查 Gatekeeper 的权限模型、数据导出与升级方法，再决定是否承载关键工作；开源软件不等于它依赖的存储、模型和浏览器免计费。[S20]

## 12 / 发布与前端验收：让预览成为可看的证据

### 只留一条负责生产发布的路径

可以由 GitHub Actions 负责检查和部署，也可以由 Workers Builds 负责构建与发布。先决定哪一条是生产入口，另一条提供检查或预览即可。两个系统同时自动部署主分支，容易形成版本竞争与缺失检查。

Workers Builds 当前 Paid 包含每月 6,000 分钟、6 并发，但单次构建仍有 20 分钟上限；不是通用的无限时 Linux 作业平台。macOS、Windows 和设备专属集成测试继续放在合适环境里。[S35] [S65]

建议流水线依次输出：固定依赖安装结果、类型与单元测试、构建物、隔离预览、浏览器检查和可归档验收材料。正式发布使用已经检查的同一源版本，避免检查 A、上线 B。

### Preview URL 不证明数据隔离

当前资源规则中，某些预览状态（例如 DO 和 Containers）有自动隔离支持，其他数据资源则依赖配置。D1、R2、KV、队列或 Vectorize 若指向同一目标，预览仍可能操作正式数据。逐项看绑定，不用一个“Preview”标签代替确认。[S63]

外部贡献的 PR 不应自动拿到生产 token、真实用户数据和宽泛出站权限。预览用合成数据；需要特定外部服务时使用独立测试身份并限制费用。部署结束记得清理预览产生的文件、队列和临时资源。

### Browser Run：操作生命周期比单张截图更重要

使用固定视口与固定输入，检查从进入页面、执行主要动作、保存、刷新、回读、取消到错误恢复的完整路径。页面视觉和交互行为分别记录。截图显示按钮存在，不证明按下之后状态正确。[S36]

一个实际的验收包可以包含：桌面与移动视口的截图、键盘操作路径、一次错误状态、导出文件与重开结果。比较同一输入的两个版本，才能判断变化来自设计还是随机内容。

Kitesurf 是新的浏览器与终端操作入口，可以用于独立实验；它的兼容性不能替代目标用户实际使用的浏览器。发布给手机用户的站点，仍要测移动浏览器、软键盘、触控、低带宽与中断恢复。[S19]

需要登录、上传、发布或支付的浏览器任务，要把人可确认的具体动作留在执行前。正当的自动化可能需要会话 cookie，但应只读取和使用该任务获准的会话，不把浏览器个人资料目录整体交给临时执行环境。

## 13 / 观测：先记录足以定位的问题，不先复制全部正文

### 一次请求最有用的记录

建议保留 request ID、部署版本、动作类别、处理阶段、耗时、结果状态、重试次数和必要的资源引用。失败时记录稳定错误分类；完整堆栈和原始正文分别控制访问与保留期限。

对于检索，计时分到 embedding、索引查询、权限核验和生成。对于异步任务，分清接收时间、排队时间、执行时间和结果提交时间。一次总耗时无法告诉维护者该优化哪一段。

### Workers Issues 的第一轮接入

当前公开 beta 可以聚合异常、失败调用、5xx 和错误日志，并关联部署与源映射；配置启用后才处理新流量。将 `observability.issues.enabled` 写进项目配置，避免下一次部署把控制台开关覆盖。[S11] [S12]

先制造一个不会含敏感内容的测试错误，确认分组、版本和调用上下文正确，再连接 webhook 或修复 agent。自动化第一步只生成调查材料和候选修复；是否合并、上线，仍由项目原来的测试和权限决定。

Workers 侧的观测不会自动看到所有本机脚本、第三方平台和离线任务。要么这些路径有自己的日志与告警，要么显式发送经过裁剪的事件，不能在控制台里看不见就推断它们没有失败。

### 告警应当对应一种行动

“CPU 稍微高一点”通常不如“任务队列已超过可接受等待时长”有用。选择与用户体验和恢复相关的阈值：持续错误比例、任务积压、未知结果、成本异常、索引新版本长时间未就绪。每条告警都写清应该查看哪份材料，避免只把焦虑推到通知栏。

## 14 / 三种规模的成本计划

本节是预算方法，不是账户报价。具体包含量参见本期报告和官方定价；税费、地区、外部服务与已被其他项目消耗的额度都要单独确认。[S34] [S36] [S37] [S38] [S39] [S40] [S41] [S43] [S44]

| 使用形态 | 首先观察 | 最容易漏算的项 | 建议的停止条件 |
|---|---|---|---|
| 静态站 + 少量 API | 动态请求、CPU、日志 | Worker-first 路由、重复构建、日志正文 | 错误/请求突然上升时暂关高成本路径 |
| 私人资料库 + 检索 | 索引体量、摄取、查询、模型 | 重复分块、重排/生成、失效索引长期保留 | 日查询或摄取超过个人预算则排队 |
| 按需 agent / Linux 工作台 | 总运行时长、规格、模型调用 | 空闲环境、失败重试、预览、产物与网络 | 截止时间、最大实例数和模型调用数 |

### 分配量与实际使用量别混算

容器可能按分配的内存计费，CPU 则看实际使用；R2 计对象操作；D1 计行而不是 SQL 次数；向量费用含维度，不能只数条目；队列重试与消息大小也会影响操作量。把每项单位写出来，比只比较“每月几美元”更可靠。[S06] [S37] [S38] [S39] [S40]

普通 Workers KV 适合一部分读多写少的数据，但不应拿来代替需要事务的高频状态。KV Instant 是另一种特殊产品，其每次写操作与每 MB 存储价格都与普通 KV 显著不同；不要因为名称接近就沿用成本估计。[S42] [S25]

### 先给实验留一本小账

每次实验记录输入规模、执行次数、总运行时长、峰值资源和保留产物。第一次小额账单不代表规模扩大后仍等比例：重试风暴、索引全量重建、媒体文件和高并发可能改变主要成本项。

同一账户多个应用共享包含量时，分项目的“独立估计”不能直接相加得到账单。最好先算所有应用的实际总量，扣除一次共享包含量，再按项目观测分配责任。

### 免费、包含、测试期间不收费是三种承诺

免费计划可能达到上限就失败；Paid 包含量之外可能继续计费；beta 免费则可能有明确未来起算日。Artifacts 的官方来源目前存在 10 月 14/15 日一天冲突，AI Search 新计费明确从 11 月 1 日开始。发布文档需要同时保留核验日期与生效日期，不能只写“现在免费”。[S07] [S08] [S10]

## 15 / 排障、恢复与停用

### 先沿一条请求路径找问题

| 现象 | 先检查 | 暂时不要做 |
|---|---|---|
| 域名解析与其他设备不同 | DNS、代理、解析器、权威记录 | 同时改证书和应用代码 |
| 302 到登录页 | Access 是否为正确应用与路径 | 直接把整个站点 Bypass |
| 403 | 边缘策略、机器身份、设备条件 | 不看响应来源就重置应用密码 |
| 401 JSON | 应用 token、issuer、audience、scope | 以为 TLS 成功就是权限正确 |
| 404 | hostname、路由、ingress、资源是否存在 | 添加万能 catch-all 把错误藏起来 |
| 429 | 应用或上游的配额与重试 | 无上限即时重试 |
| 5xx / 超时 | request ID、阶段耗时、依赖健康 | 换一批配置却不保留错误样本 |
| 页面仍是旧版 | 部署版本、路由、CDN 与 Service Worker | 认定“部署命令成功”就是用户已看到新版 |
| 向量刚写入查不到 | mutation 状态、模型/维度、命名空间、版本 | 重复无版本地全量 upsert |
| 任务登记了却没结果 | outbox、领取状态、租约、未知结果 | 直接把登记行删除重新跑 |
| 容器里的文件消失 | 生命周期、镜像、恢复方式、持久产物 | 把新环境空目录当作从未执行 |
| 手机连上私网后别的路径断了 | 路由、DNS、客户端模式 | 从唯一远程会话同时改所有网络层 |

这是排查顺序，不是凭状态码就确定根因。记录响应来自边缘、应用还是第三方；一次只改一个可验证的原因，恢复后重做负向测试。

### 一份可实际执行的恢复记录

演练前写清目标和范围，例如“恢复一个测试文档集合到指定版本，不恢复生产外部任务”。保存当前版本、对象清单和备份身份。执行后验证代表性记录、对象 hash、权限拒绝、新旧索引切换与待处理任务。

如果恢复过程中发现未知状态，保留它并停止自动推进。把“不知道是否已发出”改成“未发送”会让后续工具制造重复动作；把它改成“成功”又会掩盖缺失。恢复流程应允许不确定性有一个明确位置。

### 停用不是删掉 Worker 就结束

先停止新入口和自动触发，再处理正在执行的任务；保存需要的结果，撤销不再使用的凭据；确认容器、浏览器会话、预览、队列、Workflow 状态与临时对象的保留计划。最后根据目标删除资源或继续只读保存。

对域名入口，避免 DNS 仍指向已不存在或由别人接管的服务。对备份，确认至少有一份能在不依赖被停用服务的条件下读取。对模型与日志，单独检查外部提供商和持久记录的保留设置。

## 16 / 从旧教程继承了什么，修正了什么

本版不是向旧清单追加产品名。以下改动解释了为什么旧版的某些说法不能直接复制到今天的项目里。

| 旧资料的内容 | 本版处理 | 理由与出处 |
|---|---|---|
| 入口、身份、应用授权分层 | 保留，减少无理由的重复凭据 | 可信 Access 身份可以直接映射角色，不必机械叠多份 bearer。[S48] |
| 将 Service Binding 与调用者标签组合 | 明确标签本身不证明身份 | 能力绑定、应用协议与可伪造输入需要分开。[S45] [S57] |
| 队列先登记、重复就 ACK | 改为可恢复任务状态、outbox、租约与未知结果 | 原简化流程存在登记后退出导致丢任务的逻辑缺口；本版给出设计分析。[S53] [S55] |
| Sandbox 0.x 包办大量操作 | 更新为 1.0 原生容器接口与迁移检查 | 不混用旧类、旧镜像假设和新 API。[S72] |
| 临时磁盘丢失，因此所有恢复靠外部存储 | 补充文件系统快照，仍区分长期结果 | 快照不保存进程，且有镜像与期限条件。[S05] |
| AI Search 仍为 beta | 更新为 GA、多模态与 11 月新计费 | 旧价格和旧额外收费判断需逐项替换。[S09] [S10] |
| Gateway 旧固定日志额度 | 按首次创建日期区分新日志规则 | 2026-09-24 之后的新客户走 Workers Logs。[S15] |
| 只描述自部署 Cloudflare OS | 补充托管版候补，但不当成可用承诺 | 两种交付形态与状态不同。[S20] |
| 泛化 D1 SQL 导出与恢复 | 补充虚拟表、导入格式与恢复演练限制 | 不能把全文索引数据库假设成随时可全库导出。[S50] [S51] |
| 浏览器一概禁止使用 cookie/storage | 改成任务授权与会话最小化 | 合法登录任务需要会话；关键是范围、外流与副作用 |
| 模板或测试通过即可算落地 | 明确分开文档、源码、本地、云端与真实使用证据 | 本手册不会冒充读者的部署记录 |

7 月版本确立了基础服务与故障路径；8 月扩充版加入 Agents、Sandbox、Containers、Cloudflare OS、Mesh 与托管记忆。它们提供了实践问题的结构，本版的平台状态与费用仍以本次官方来源核验为依据。历史文件的“可分享”标签也不替代对新文件中的示例、元数据与附件做实际检查。

## 17 / 分享与持续修订

公开版保留机制与操作顺序，私人版保留真实账户、资源和运行记录。教程里的示例名称不是应该部署到生产的默认配置。截图、终端 prompt、导出 PDF 的元数据和打包的测试数据也需要检查，不能只删除正文中的密钥。

一次修订至少记录：变化依据、核验日期、生效日期、影响哪些章节、哪些例子需重测、哪些旧判断保留为历史。产品从 beta 到 GA 不等于原有试验自动通过验收；SDK 1.0 也不代表示例使用的版本已经安装并执行过。

建议把报告作为按期冻结的出版物，把手册作为可修订入口。来源条目、产品状态和可复算的费用假设保持小而明确；只有出现反复出错的结构时，才把它升级为检查脚本。不要为了持续更新而制造每天都必须发一篇的负担。

<!-- SOURCES -->

## 来源索引

以下均为本次查阅的官方来源；核验日为 2026-10-02。网页会继续变化，标题与链接不代表已保存其全文快照。正文中的事实与编辑建议分开表达；本索引不代表云端部署验证。

**S02 · cf CLI 发布**  
<https://blog.cloudflare.com/cloudflare-cf-cli-launch/>

**S03 · cf CLI 文档**  
<https://developers.cloudflare.com/cf/>

**S05 · Containers 文件系统快照**  
<https://developers.cloudflare.com/containers/guides/snapshots/>

**S06 · Containers 价格**  
<https://developers.cloudflare.com/containers/platform/pricing/>

**S07 · Artifacts 公开测试发布**  
<https://blog.cloudflare.com/next-git-platform-on-cloudflare/>

**S08 · Artifacts 价格**  
<https://developers.cloudflare.com/artifacts/platform/pricing/>

**S09 · AI Search GA**  
<https://blog.cloudflare.com/ai-search-ga/>

**S10 · AI Search 限制与价格**  
<https://developers.cloudflare.com/ai-search/platform/limits-pricing/>

**S11 · Workers Issues 发布**  
<https://blog.cloudflare.com/real-time-issue-detection/>

**S12 · Workers Issues 文档**  
<https://developers.cloudflare.com/workers/observability/issues/>

**S13 · AutoRouter 发布**  
<https://blog.cloudflare.com/auto-router/>

**S14 · AI Gateway User Insights**  
<https://developers.cloudflare.com/ai-gateway/observability/user-insights/>

**S15 · AI Gateway 价格与日志**  
<https://developers.cloudflare.com/ai-gateway/reference/pricing/>

**S16 · Clef 与强化学习平台发布**  
<https://blog.cloudflare.com/clef-decision-models/>

**S17 · Clef 模型卡**  
<https://developers.cloudflare.com/workers-ai/models/clef/>

**S18 · Clef-flash 模型卡**  
<https://developers.cloudflare.com/workers-ai/models/clef-flash/>

**S19 · Kitesurf 更新**  
<https://blog.cloudflare.com/kitesurf-update/>

**S20 · Cloudflare OS 托管候补**  
<https://blog.cloudflare.com/managed-cloudflare-os/>

**S25 · KV Instant 私测与价格**  
<https://blog.cloudflare.com/workers-kv-instant/>

**S34 · Workers 价格**  
<https://developers.cloudflare.com/workers/platform/pricing/>

**S35 · Workers Builds 限制与价格**  
<https://developers.cloudflare.com/workers/ci-cd/builds/limits-and-pricing/>

**S36 · Browser Run 价格**  
<https://developers.cloudflare.com/browser-run/pricing/>

**S37 · D1 价格**  
<https://developers.cloudflare.com/d1/platform/pricing/>

**S38 · R2 价格**  
<https://developers.cloudflare.com/r2/pricing/>

**S39 · Queues 价格**  
<https://developers.cloudflare.com/queues/platform/pricing/>

**S40 · Vectorize 价格**  
<https://developers.cloudflare.com/vectorize/platform/pricing/>

**S41 · Workers AI 价格**  
<https://developers.cloudflare.com/workers-ai/platform/pricing/>

**S42 · KV 价格**  
<https://developers.cloudflare.com/kv/platform/pricing/>

**S43 · Durable Objects 价格**  
<https://developers.cloudflare.com/durable-objects/platform/pricing/>

**S44 · Workflows 价格**  
<https://developers.cloudflare.com/workflows/reference/pricing/>

**S45 · Workers Bindings**  
<https://developers.cloudflare.com/workers/runtime-apis/bindings/>

**S46 · Workers Static Assets**  
<https://developers.cloudflare.com/workers/static-assets/>

**S47 · Cloudflare Tunnel**  
<https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/>

**S48 · Access JWT 验证**  
<https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/>

**S49 · Access Service Tokens**  
<https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/>

**S50 · D1 Time Travel**  
<https://developers.cloudflare.com/d1/reference/time-travel/>

**S51 · D1 数据导出**  
<https://developers.cloudflare.com/d1/best-practices/import-export-data/>

**S52 · R2 对象生命周期**  
<https://developers.cloudflare.com/r2/buckets/object-lifecycles/>

**S53 · Queues 重试与批处理**  
<https://developers.cloudflare.com/queues/configuration/batching-retries/>

**S54 · Queues 死信队列**  
<https://developers.cloudflare.com/queues/configuration/dead-letter-queues/>

**S55 · Workflows 执行规则**  
<https://developers.cloudflare.com/workflows/build/rules-of-workflows/>

**S56 · Cron Triggers**  
<https://developers.cloudflare.com/workers/configuration/cron-triggers/>

**S57 · Service Bindings**  
<https://developers.cloudflare.com/workers/runtime-apis/bindings/service-bindings/>

**S58 · Agents SDK**  
<https://developers.cloudflare.com/agents/>

**S59 · Sandbox SDK**  
<https://developers.cloudflare.com/sandbox/>

**S60 · Agent Memory**  
<https://developers.cloudflare.com/agent-memory/>

**S61 · Cloudflare Mesh**  
<https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-mesh/>

**S62 · Split Tunnels**  
<https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/configure/route-traffic/split-tunnels/>

**S63 · Workers 预览资源隔离**  
<https://developers.cloudflare.com/workers/previews/resources/>

**S64 · Vectorize Client API**  
<https://developers.cloudflare.com/vectorize/reference/client-api/>

**S65 · Workers Builds**  
<https://developers.cloudflare.com/workers/ci-cd/builds/>

**S66 · Workers 入门**  
<https://developers.cloudflare.com/workers/get-started/guide/>

**S67 · Zero Trust 计划**  
<https://www.cloudflare.com/plans/zero-trust-services/>

**S70 · Durable Objects pending I/O 保活**  
<https://developers.cloudflare.com/changelog/post/2026-10-01-pending-io-keep-alive/>

**S71 · Workers OAuth Provider v1**  
<https://developers.cloudflare.com/changelog/post/2026-10-01-workers-oauth-provider-1x/>

**S72 · Sandbox SDK 1.0 迁移差异**  
<https://developers.cloudflare.com/sandbox/sdk/migrate/changes-in-1-0/>


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
[S43]: https://developers.cloudflare.com/durable-objects/platform/pricing/ "Durable Objects 价格"
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

---

GitHub：[github.com/IndelibleVivi](https://github.com/IndelibleVivi)  
*made by Faye & Cove*
