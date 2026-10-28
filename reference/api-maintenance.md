---
title: 用程序维护 Cloudflare 资源
subtitle: 选择调用入口，取得完整结果，再判断变更是否完成
source_cutoff: 2026-10-28
---

# 用程序维护 Cloudflare 资源

“控制台里有这个资源”“API 返回成功”“读者能用到服务”是三个需要分别检查的结果。程序可以减少重复盘点和配置操作；它也必须说明读了哪些范围、哪里失败，以及哪些结果还不知道。先确定手边的操作，再选择 CLI、REST 或现有语言的 SDK。

本文于 2026-10-08 定向查阅官方 SDK、Go `v7.12.0`、OpenAPI 仓库与 R2 API 文档；Tunnel 变更另复看已有来源。没有安装 SDK、访问账号或执行云端请求。下面的可靠操作方法是编辑建议；Go 的默认值只适用于所标版本。

10 月 13 日另核查 `v7.13.0` release 与 API MCP 的 Skills 扩展，下文补充具体触发点。原先 `v7.12.0` 的客户端默认值继续按固定版本阅读，没有据新 release 推断它们已重新验收。

10 月 20 日补充 `cf docs search`、Cloudflare API MCP 的事件与 step-up 调查，以及 Gateway／CWS 作为变更执行边界的入口。没有安装 CLI、发出搜索请求或使用账户执行这些动作。

10 月 28 日定向补充产品 MCP 的旧传输入口退役、模型 provider 迁移与两个字段变更；既有 Go 固定版本、分页和 timeout 说明保留原范围。

## 控制台、CLI、REST、SDK、binding 各接哪一段

| 手边的操作 | 先找哪个入口 | 还需要检查什么 |
|---|---|---|
| 人查看资源、理解一次配置 | Dashboard 与相应产品文档 | 页面显示的 account、zone 和资源身份，是否属于目标环境 |
| 项目创建、开发、部署或重复 shell 操作 | 项目现有 CLI，例如 Wrangler；通用入口见 [cf CLI 介绍](../reports/2026-10-02.md#cf-cli先从看清账户开始) | 已有 config、命令的支持范围与部署目标；别同时建立第二套配置 owner |
| 只需核对一个接口，或已有少量可维护的请求 | 官方 REST API / curl 示例 | 方法、路径、权限、分页、超时与输出处理 |
| 已有应用要串联多个请求与结果 | 应用现有语言的官方 SDK | 锁定版本、客户端默认值、返回类型、迁移说明 |
| Worker 在请求中使用已绑定的资源 | 产品的 Workers binding | binding 名称、资源与环境；它不能证明管理接口也已配置好 |

官方 SDK 入口列出 Go、TypeScript、Python，并将集成现有应用、串联请求列为 SDK 的使用情形。它不要求为了使用 Go SDK 重写一个已有的 Python 或 TypeScript 项目。[S118]

R2 尤其需要分清入口：Workers API、S3-compatible API 和 Cloudflare REST API 均有用途。REST 支持 bucket 管理及对象操作；高吞吐工作负载应按官方建议使用 Workers 或 S3 路线。不能把“SDK 可以调用 REST”推成“所有文件交付都改走 REST”。[S122]

## 先知道自己读的是哪一组资源

盘点从项目现有 dependency、config 和实际调用路径开始，保留 account / zone / Worker / bucket / Tunnel 的归属线索。绑定名是应用中的名字；资源 ID、环境与部署版本是另外的身份。公共说明使用占位符，真实配置留在项目批准的位置。

建议把读取结果附上这几项：目标环境、接口或命令、查询条件、客户端版本、核对时间，以及是否取得全部页。查询成功只证明指定权限与筛选条件下的结果；它不证明账号里所有资源都已列出，更不证明服务可达。网页、Access、回源与应用响应的分层检查见[私有状态页实践](../practice/protected-status.md)。

写配置前先取得当前状态，形成具体差异，说明目标资源和失败范围。只有任务已授权该动作，才执行写入；随后读回配置，再检查受影响的使用路径。批量操作应逐项保留成功、失败和未知，不能把一个成功响应当成整批完成。

## 完整分页：第二页失败不能宣布盘点完成

一次列表响应、完整遍历与服务是否可用分别报告。迭代遇到错误时保留已取得的对象和失败页／cursor，标明 `complete: false`。空页仍可能有下一页；没有对象不自动表示结束。即便分页完成，筛选条件、权限和遍历期间的资源变化仍限定这次观察。

Go `v7.12.0` 的普通 `.List()` 取一页；`.ListAutoPaging()` 继续遍历，结束后须检查 `iter.Err()`。成功读到若干对象而没有检查结束错误，不能作为完整盘点证据。[S119]

语言无关的[离线操作例子](../examples/api-operations/README.md)用合成分页验证成功、重试、后页失败、空页与总期限。它由 Python 实现教学模型，没有调用 Cloudflare Python SDK，也没有验证真实 API 的分页语义。

## 超时与重试：整件事有自己的期限

给整个操作设置期限，覆盖分页、重试与等待；单次请求可以另设较短期限。若每次重试都重置整件事的时钟，agent 可能一直等，也无法及时交付部分结果。期限耗尽时，说明停在哪里，保留已有结果，不把停止解释成完整成功。

在 Go `v7.12.0` 中，请求默认没有 timeout；context 可以限定含重试的请求生命周期，`option.WithRequestTimeout()` 限定单次尝试。默认自动重试两次，范围包括连接错误、408、409、429 和 5xx；`option.WithMaxRetries()` 可调整。其他语言或版本须各自核对。[S119]

客户端重试不能决定整个业务动作是否安全。读操作也要看服务的具体语义；写操作响应丢失时，服务可能已经改完了。先记为 [uncertain / 结果未知](../docs/glossary.md#uncertain--结果未知)，通过该接口支持的状态查询、操作记录或稳定幂等约定核对，才能选择是否再执行。不要为一次未知结果生成新身份后重放；[任务恢复用例](../use-cases/recoverable-jobs.md)解释了本地任务状态与外部副作用之间的缺口。

> **想一想：列表已返回 20 个对象，下一页超时，能写“没有发现其他资源”吗？**
>
> **答案：不能。** 可以报告已读取的 20 个对象、筛选范围和失败位置；全量结论仍未知。写操作超时也只说明响应没有可靠取得，不能直接写成“未执行”。

错误报告保存安全摘要、状态码、操作身份和范围。真实请求头、token、完整响应 body、私有对象名和日志不复制进公共工单或本书；调试输出是否需要保留由项目的数据边界决定。

## SDK 与 OpenAPI 更新：先找到被使用的方法

Go `v7.12.0` release 增加 Containers application、instance、version、rollout、image 和 registry 的管理入口，也记录 Breaking Changes，例如部分 Zero Trust 列表由 `SinglePage` 变为分页类型。这说明接口可用与返回行为可能改变；它没有证明账号开放条件、权限或运行质量。[S120]

官方 `cloudflare/api-schemas` 保存 Cloudflare API 的 OpenAPI schemas。它适合检查接口层的方法、参数和返回结构；具体客户端的默认值和迁移细节仍看对应语言、版本的文档。[S121] 可使用下面的复查顺序：

1. 固定变化依据：旧／新版本或明确公告、生效日期、受影响的方法或字段。
2. 从本书来源定位候选内容：例如 `python3 tools/fieldbook.py impact-source S120`。
3. 到目标项目找对应的依赖版本、实际调用与解析代码；“用了同一个产品”只构成候选。
4. 命中后检查完整分页、调用参数和失败行为；需要改动时遵循该项目授权与验证入口。
5. 没命中就附核查范围收口；证据不够则保留未知，不宣布不受影响。

以 `v7.13.0` 为例：release 移除 `Registrar.Domains` 下的 List／Get／Update，替代入口为 `Registrar.Registrations`。用过 Go SDK 的项目先查这个方法是否真的出现，再决定迁移；不需要随每次生成式 SDK 更新重写全部教程。GitHub 发布时间为 10 月 12 日，release notes 标注 10 月 9 日，两个日期分别保留。[S142]

例如 Tunnel 的 list/get 内嵌 `connections` 于 2026-10-05 移除，应查询专用 connections endpoint。只有仍解析旧字段的调用需要据此修正；部署了 Tunnel 本身不能证明项目命中该变化。官方说明还区分了 `cloudflared` 与读取该字段的集成。[S117]

来源查询只检查登记条目的正文引用和 JSON `source` 单值／`sources` 数组，接着沿 `depends_on` 传播；来源书目、代码示例、注释与来源附录不作为正文使用点。它返回当前复查、历史勘误和非活动候选，`related` 不传播。它不分析私人项目，不改变日期，也不判定所有引用已经过时。

### 先核对具体字段，再迁移解析器

10 月 26 日 Advanced Nameservers 开始约七天滚动切换为 `nameservers.type: "cloudflare.advanced"`；未轮到的账户仍可能返回旧类型。`foundation_dns` 保留为 deprecated 兼容别名，同时提交时两者必须一致。把 type 当封闭 enum 的代码须接受新值；这项 API 表示变化不要求迁移 zone，也不改变订阅。[S198]

SQL introspection 另有 `include_attributes`／`attributes` 新名字，发现范围是前七天，旧字段仍兼容。它属于 SQL API，不应套到其他资源列表；[观测页](../services/observability.md#一次查询先选一份-dataset)保留具体查询条件。[S196]

### 模型 provider 迁移保留调用条件

10 月 21 日 `createAI` 从 `agents/models/ai-sdk` 或 `agents/models/pi-ai` 接入 Workers AI、Gateway catalog、dynamic route 和 vendor models。`workers-ai-provider`／`ai-gateway-provider` 已 feature frozen、deprecated；AI Search 则使用独立的 `ai-search-provider`。[S179]

旧 `apiKey` 参数改为 `apiToken`。fallback 只在首选模型**产生输出之前**失败时尝试后续模型；binding 的 catalog／dynamic stream resume 是另一项能力，不能推定外部工具动作也可恢复。迁移时检查凭据、模型身份、用量与错误路径；本书的离线 REST 请求例子不依赖这些 provider，无需为了接口名变化重写。[S179] [S180]

## Agent 怎样取得官方操作指导

10 月 10 日起，Cloudflare API MCP 在 `https://mcp.cloudflare.com/mcp` 提供 Skills over MCP：支持该扩展的客户端可用 `skills/list` 发现，再从 `skill://<name>/<path>` 读取。客户端具备 MCP 工具能力不自动说明它支持 Skills 扩展；接线时分别确认资源发现、内容读取和实际操作权限。本书没有连接真实账户验证此入口。[S134]

### MCP 返回 410 Gone：检查旧 /sse 地址

10 月 22 日起，Cloudflare **产品专用** MCP servers 只提供 `/mcp`；旧 `/sse` 返回 **410 Gone**，附新地址。将客户端配置改为服务器公布的 `/mcp`，例如 `https://docs.mcp.cloudflare.com/mcp`；原来经 `/sse` 登录的客户端需要重新登录。已经用 `/mcp` 的连接不受此项变化影响。它不表示所有第三方 MCP 都采用同一迁移安排。[S181]


## 先搜文档，再读取原页

2026-10-16 公告介绍 CLI `1.0.0-beta.16` 的 `cf docs search`：它搜索 guides、tutorials、examples 和产品文档，返回**最多五条按相关度排序的 JSON**，每项含 title、description 与 documentation URL。该命令需要互联网连接；公告示例未要求 Cloudflare 登录。[S160]

下面的查询只使用公共主题，不携带私人项目名、账号或凭据。以下命令是查询形状，不是本次已执行的结果：

```sh
cf docs search "schedule a worker"
cf docs search "Gateway Forward Workers"
cf docs search "R2 bucket public access"
```

从结果中先取 documentation URL，再核对页面日期、适用计划、返回字段与操作权限。搜索成功只表示文档索引返回了候选；它不能证明账号开放了功能，也不能证明当前客户端支持某个命令。搜索 query 会进入 telemetry，官方说明采用与 CLI command search 相同的长度限制与 opt-out 行为；在受限环境里先查项目的遥测设置。[S150]

公告还给出读取完整页面的方式：用 `.[0].url` 取首个结果，再带 `Accept: text/markdown` 请求该 URL。这里使用公共查询形状，不携带私人项目名、账号或凭据；没有在本页执行它。

```sh
url=$(cf docs search "proxy a DNS record" | jq -r '.[0].url')
curl -H "Accept: text/markdown" "$url"
```

### Kebab-case 与生成命令面

同一 beta.16 公告说明生成命令统一为 kebab-case；CLI changelog 记录了从 camelCase／snake_case 迁移的示例：

```text
cf accounts billing getCredits          -> cf accounts billing get-credits
cf addressing regional_hostnames list   -> cf addressing regional-hostnames list
cf analytics_engine sql query           -> cf analytics-engine sql query
```

这只是迁移示例，不应从名称变化推断 API 行为改变。项目应先查锁定的 CLI 版本、帮助输出与现有脚本，再决定迁移；其余 breaking command 与 flag 变化参考 CLI release notes。[S149] [S160]

### 搜索之后的事件与授权

10 月 13 日，Cloudflare API MCP 开始把 Workers Issues 作为首个 MCP Event 交给客户端。客户端用 `events/list` 发现 `cloudflare.alert.workers_observability_real_time_issue`，用 `events/subscribe` 按 account 或单个 Worker 订阅；Issues 检测到新故障或复发故障时，服务器把签名事件发到客户端 webhook，agent 不必轮询就能开始调查。使用前要在 Worker 启用 Issues，并以 Notifications Write 和 Workers Observability Write 权限连接支持 MCP Events webhook 的客户端。[S145]

10 月 19 日，API MCP 加入 step-up authorization：连接 `https://mcp.cloudflare.com/mcp` 时先在 consent page 选择 Minimal，工具调用需要尚未授予的 scope 时，服务器返回点名该 scope 的 `insufficient_scope` challenge，由 client 请求用户追加授权；已经授予的 scopes 会保留。该能力要求客户端支持 step-up；工具错误不会被自动视为已获授权。[S146]

一条可复核的操作记录应写成：搜索了哪个公共 query → 读了哪个 URL 与版本 → 当前 token／MCP 授权是否覆盖动作 → 写请求返回了什么 → 读回哪个资源。事件、搜索摘要与工具错误都只能把调查带到下一步，不能替代读回。产品页面的观察与授权模式见[云 API 与 HTTP 出站控制](../services/egress-controls.md)。

## 把这次操作交回项目工作

一份可继续使用的结果应连在一起说明：当前任务、目标范围、现有采用理由、命中的变化、已得到的证据、仍未知的部分和下一项验证。检查失败时保留部分观察；技术选择的条件没变时复用它。

接下来读[把变化接到当前项目](../use-cases/project-context.md)，或直接使用[项目判断任务单](../templates/project-context-task.md)。采用理由和当前配置由项目自己的已有文档持有；本书提供解释与可检查的方法。

<!-- SOURCES -->

[S117]: https://developers.cloudflare.com/changelog/post/2026-07-09-tunnel-routes-and-connections-api-changes/ "Tunnel routes 与 connections API 变更"
[S118]: https://developers.cloudflare.com/fundamentals/api/reference/sdks/ "Cloudflare 官方 SDK 与 curl 使用入口"
[S119]: https://github.com/cloudflare/cloudflare-go/blob/v7.12.0/README.md "Cloudflare Go v7.12.0：分页、超时与重试"
[S120]: https://github.com/cloudflare/cloudflare-go/releases/tag/v7.12.0 "Cloudflare Go v7.12.0 release：管理接口与迁移"
[S121]: https://github.com/cloudflare/api-schemas "Cloudflare API OpenAPI schemas"
[S122]: https://developers.cloudflare.com/r2/api/ "R2 API：Workers、S3 与 REST 的职责"
[S134]: https://developers.cloudflare.com/changelog/post/2026-10-10-cloudflare-mcp-skills/ "Cloudflare API MCP 的 Skills 扩展"
[S142]: https://github.com/cloudflare/cloudflare-go/releases/tag/v7.13.0 "Cloudflare Go v7.13.0 release"
[S145]: https://developers.cloudflare.com/changelog/post/2026-10-13-cloudflare-mcp-events/ "Cloudflare API MCP 作为 MCP Events 发送 Workers Issues"
[S146]: https://developers.cloudflare.com/changelog/post/2026-10-19-cloudflare-mcp-step-up/ "Cloudflare API MCP 的 step-up authorization"
[S149]: https://github.com/cloudflare/cf/blob/main/packages/cli/CHANGELOG.md "cf CLI changelog：文档搜索与 kebab-case 命令"
[S150]: https://github.com/cloudflare/cf/releases/tag/cf%401.0.0-beta.15 "cf 1.0.0-beta.15 release：docs search"
[S160]: https://developers.cloudflare.com/changelog/post/2026-10-16-docs-search/ "使用 Cloudflare CLI 搜索文档"

[S179]: https://developers.cloudflare.com/changelog/post/2026-10-21-createai/ "createAI 替代旧 Workers AI 与 Gateway provider"
[S180]: https://developers.cloudflare.com/agents/models/ "Agents Models：连接、fallback 与 stream resume"
[S181]: https://developers.cloudflare.com/changelog/post/2026-10-22-cloudflare-mcp-servers-retire-sse/ "Cloudflare 产品 MCP 退役 /sse 入口"
[S196]: https://developers.cloudflare.com/changelog/post/2026-10-27-introspection-include-attributes/ "SQL API introspection 的 include_attributes 字段"
[S198]: https://developers.cloudflare.com/changelog/post/2026-10-26-foundation-dns-nameserver-type/ "Advanced Nameservers 类型与兼容字段迁移"
