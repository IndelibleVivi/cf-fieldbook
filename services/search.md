---
title: 自己的材料，还是互联网上的新信息
subtitle: AI Search、Vectorize 与 Web Search API 分别搜什么
source_cutoff: 2026-10-03
---

# 自己的材料，还是互联网上的新信息

问“这三份资料哪份写了撤下规则”，证据在自己持有的集合；问“今天官方更新了什么”，证据在当前互联网。先确定需要哪一边，才选择检索入口。网页搜索不会因同属 Cloudflare 就读取私有 R2 内容。

## 让自己的集合回到原件

AI Search 管一部分摄取、分块与检索，Vectorize 适合由应用自己安排管线。权限、版本、撤下状态与回读原文仍属于应用；索引只帮助找到候选。现有[手册的检索章节](../guides/handbook.md#retrieval)说明两条路线。[S09] [S10] [S40]

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
