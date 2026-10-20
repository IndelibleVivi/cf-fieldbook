---
title: 自己的材料，还是互联网上的新信息
subtitle: AI Search、Vectorize 与 Web Search API 分别搜什么
source_cutoff: 2026-10-20
---

# 自己的材料，还是互联网上的新信息

问“这三份资料哪份写了撤下规则”，证据在自己持有的集合；问“今天官方更新了什么”，证据在当前互联网。先确定需要哪一边，才选择检索入口。网页搜索不会因同属 Cloudflare 就读取私有 R2 内容。

2026-10-20 定向复核 AI Search 中日韩关键词查询、索引限制与 11 月计费；10 月 13 日的 SDK 搜索、读页与流式转换范围保留。Vectorize 及下方互联网 provider 价格／保留表仍按 2026-10-03 阅读，没有检索质量 benchmark。

## 让自己的集合回到原件

AI Search 管一部分摄取、分块与检索，Vectorize 适合由应用自己安排管线。权限、版本、撤下状态与回读原文仍属于应用；索引只帮助找到候选。现有[手册的检索章节](../guides/handbook.md#retrieval)说明两条路线。[S09] [S10] [S40]

## 中文明明在原文里，为什么搜不到

10 月 16 日，AI Search 修复 `trigram` 对无空格中日韩问句的处理；此前这类输入容易被当成一个完整短语。中文集合先检查 `indexing_options.keyword_tokenizer`：默认 `porter` 不适合这类切词，官方建议使用 `trigram`。更换 tokenizer 会触发全量重建，等待索引完成后再比较结果。[S161] [S162]

`trigram` 按重叠的三个字符切片，**不足三个字符的词不能独立匹配**。`retrieval_options.keyword_match_mode` 默认 `and`，改成 `or` 会扩大召回，也可能引入无关片段。Workers Paid 启用 keyword 时单实例最多 500,000 文件，vector-only 为 1,000,000；重建和容量都应纳入选择。[S162]

### 用同一组问题比较 keyword 与 hybrid

以下是合成材料与待验证样本，不是已经运行的云端结果。先给每题标出原件与期望证据，再固定材料版本比较 keyword／hybrid、`and`／`or`，记录命中片段、漏检、误召回、耗时和用量。

| 合成原件中的已知证据 | 查询样本 | 重点检查 |
|---|---|---|
| 《撤下规则》：撤下后立即拒绝读取，随后清理索引 | “资料撤下后还能读到旧版本吗？”；“撤下后什么时候清理索引？” | 无空格长问句与完整证据，不只看有无结果 |
| 《维护人》：维护人为“林岚” | “林岚”；“谁负责维护资料架？” | 两字名字的 trigram 边界；语义查询是否回到该原件 |
| 《恢复接口》：保留 `job_id`、`lease_expires_at` | “lease_expires_at”；“job_id 租约” | 标识符切片、多个查询项的 and／or 差别 |
| 《恢复规则》：先核对外部结果，再决定是否重试 | “回包丢了要再做一遍吗？”；“不确定有没有成功” | 语义改写；召回后是否真的回答了问题 |
| 集合未说明资料售价 | “这份资料卖多少钱？” | 保留无答案样本，不能因有相近片段就编造 |

出现漏检，先核对原件是否入库、分块是否含证据、索引是否完成，再检查 tokenizer 与匹配模式；然后才比较 embedding／reranking。权限和撤下状态仍由应用核验。

### 11 月的两类查询费用

AI Search 从 **2026-11-01** 开始计费。每月含 5M 摄取 tokens、10 GB-month 存储、各 1,000 次 semantic 和 full-text 查询。超出部分 full-text 为 **$0.10／千次**，semantic／vector／hybrid 为 **$0.75／千次**；Workers AI embedding 与 reranking 已包含，生成、query rewriting 与外部模型继续另计。比较检索路线时同时观察每题查询次数与额外模型调用。[S10]

## 当前互联网：先搜索，再读来源

Web Search API 在 2026-10-02 进入 beta，经 AI Gateway 提供 provider 入口。一个完整任务可以是：查询某项能力 → 从结果取 title、URL 和 description → 打开原页 → 核对公告与生效日期 → 保存出处与读取日期 → 在自己的答案中链接证据。description 是候选摘要，不能代替原页的条件。[S106] [S108]

下面是供另行授权实验采用的 Worker 调用形状，不是本仓库已发出的请求：

```js
const response = await env.AI.websearch({
  gatewayId: "default",
  query: "Cloudflare Observability pricing effective date",
  provider: "ceramic",
  limit: 5,
});
const results = await response.json();
```

需要 AI binding、Gateway 及 credits 或相应 provider key；REST 入口是 `/accounts/{account_id}/ai/websearch/`。返回 `items` 中的 URL、title、description，以及 metadata；最多 10 个结果，query 最长 1,024 字符。[S108]

## 把搜索与读页接进任务

2026-10-12，Agents SDK 提供了配套的 `web_search` 与 `web_fetch` 工具；前者要求 SDK ≥ 0.27.0，后者 ≥ 0.28.0。除了 Pi、AI SDK 和 TanStack AI adapters，也可直接调用 `createAIWebSearch()` / `createHTTPWebSearch()` 做定时查询，再用 `fetchWeb()` 读取来源，不必先让模型发起一次工具调用。[S128] [S130]

搜索时，模型选择 query 与结果数；应用固定 provider、Gateway 和用量边界。SDK 默认最多返回 5 项，可配置的上限为 1–10。默认 Gateway 是 `default`；省略 `byokAlias` 时，先使用该 provider 的 `default` key，没有该 key 才使用 AI Gateway credits；显式指定的 alias 不存在时会失败。接入任务前应明确这条费用归属。[S129]

读页会返回最终 URL、HTTP status、content type 与正文窗口。默认每窗最多 20,000 字符，以 offset 继续；整个响应最多读取 5,000,000 bytes，包含重定向与转换的 deadline 为 30 秒。这些值由应用配置，模型不能通过要求“全文”绕过边界。PDF 与支持的 Office 文档可转换为文本；直接读取不带浏览器 cookie、凭据或自定义请求头，也不执行页面 JavaScript。需要登录、动态页面或交互时，再选择 browser 路线。[S131]

自定义 `WebSearchSource` 接管 provider 与计费；自定义 `WebFetchSource` 接管 URL、host、bytes 和重定向控制。更换来源时要保留这些责任，不能只保留同名工具。工具返回的来源仍须经过上面的原页核对；一次 SDK 调用成功不证明内容已经完整或适用于问题。[S129] [S131]

## Markdown 流式转换改变了哪些读取约定

2026-10-09，Markdown for Agents 改为边缘进程内流式转换，HTML 上限增至解压后 6 MiB。转换响应不再生成 `x-markdown-tokens`、`x-original-tokens`，并移除 `Content-Length`。依赖这些头的读页程序应自行计算所需计量，按实际读取的 body 执行上限，并保留中断状态；不能用 header 缺失判定失败或用已有正文判定完整。[S127]

网站转换的 6 MiB 上限与 SDK 读页的 5,000,000 bytes 默认预算约束不同环节。调整其中一项不会自动放宽另一项；处理长文时应一起检查转换、传输和返回给模型的窗口。

## Provider 比较：费用、返回材料和保留分开看

| provider | USD / 1,000 requests | 返回材料的特点 | 当前 provider 页 ZDR |
|---|---:|---|---|
| `ceramic`（默认） | $0.25 | 较长页面 description | Yes |
| `exa` | $7.00 | query 相关 highlights | No |
| `linkup` | $5.00 | fast / raw 结果 | Yes |

表格查阅于 2026-10-03。公告称三个 provider 均支持 ZDR，而当前 provider 文档将 Exa 标为 No；此处按 provider 文档保留差异，不承诺 Exa 零保留。Provider 的保留承诺也不能替代 Gateway 自己的日志设置。[S106] [S107]

通过 credits 走 provider 标价，公告没有另加搜索加价；BYOK 改由 provider 结算。API 指定 `byokAlias` 却没有相应 key 时失败，不能以为总会自动转 credits。[S106] [S108]

同一组实际问题比较来源质量、覆盖、延迟、失败和每任务查询数，再判断单价。本文没有 benchmark，不把最便宜的入口写成效果最好。

## 两边怎样组合

公开更新先从互联网取得，经过编辑再进入自己的资料集合；私人原文查询留在自己的获准范围。回答同时使用两种来源时，分别记录来源类型、版本或读取日期。只缺自己的旧资料时，不必把私人问题发送到互联网 provider。

完整的更新与撤下过程见[私有资料站实践](../practice/private-reader.md)，模型调用与网关的分工见[手册](../guides/handbook.md#models)。

<!-- SOURCES -->

[S09]: https://blog.cloudflare.com/ai-search-ga/ "AI Search GA"
[S10]: https://developers.cloudflare.com/ai-search/platform/limits-pricing/ "AI Search 限制与价格"
[S106]: https://developers.cloudflare.com/changelog/post/2026-10-02-introducing-web-search-api/ "Web Search API 发布"
[S107]: https://developers.cloudflare.com/web-search/providers/ "Web Search API providers"
[S108]: https://developers.cloudflare.com/web-search/how-to-use/ "Web Search API 调用与响应"
[S40]: https://developers.cloudflare.com/vectorize/platform/pricing/ "Vectorize 价格"
[S127]: https://developers.cloudflare.com/changelog/post/2026-10-09-markdown-for-agents-in-process-conversion/ "Markdown for Agents 流式转换与响应头变更"
[S128]: https://developers.cloudflare.com/changelog/post/2026-10-12-web-search/ "Agents SDK web_search 发布"
[S129]: https://developers.cloudflare.com/agents/tools/web-search/ "Agents SDK 搜索工具与费用归属"
[S130]: https://developers.cloudflare.com/changelog/post/2026-10-11-web-fetch/ "Agents SDK web_fetch 发布"
[S131]: https://developers.cloudflare.com/agents/tools/web-fetch/ "Agents SDK 读页窗口与请求边界"

[S161]: https://developers.cloudflare.com/changelog/post/2026-10-16-cjk-keyword-search/ "AI Search 中日韩关键词查询修复"

[S162]: https://developers.cloudflare.com/ai-search/configuration/indexing/keyword-search/ "AI Search keyword tokenizer、匹配模式与索引限制"
