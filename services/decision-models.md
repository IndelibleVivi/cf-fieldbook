---
id: service.decision-models
reviewed_on: 2026-10-13
review_scope: Clef 系列标价、托管上下文与输入字段；Jev 保留 2026-10-02 核对范围
evidence: official-documents-only
---

# 决策模型与 Cloudflare 接入

从这里读一件事：拿到一段材料以后，只需要类别、概率或等级时，可以先试专门的决策模型。接入网关与模型本身分开选择。

Cloudflare 自有的 Clef／Clef-flash／Clef-omni 与第三方 Jev 都能进入现有 AI 调用路径，但有不同的模型选择器、输入限制和计费。API 形状相近不等于可共享经过校准的阈值。

<!-- facts: cf-routes -->
| 路线（接入 → 模型） | 模型选择器 | 输入 USD / 百万 token | 来源 |
|---|---|---:|---|
| Cloudflare → Jev | `typesafe/jev` | 0.042 | [S73](https://developers.cloudflare.com/ai/models/typesafe/jev/) |
| Cloudflare → Clef-flash | `@cf/cloudflare/clef-flash` | 0.038 | [S18](https://developers.cloudflare.com/workers-ai/models/clef-flash/) [S123](https://developers.cloudflare.com/changelog/post/2026-10-09-clef-omni-workers-ai/) |
| Cloudflare → Clef-omni | `@cf/cloudflare/clef-omni` | 0.150 | [S124](https://developers.cloudflare.com/workers-ai/models/clef-omni/) [S123](https://developers.cloudflare.com/changelog/post/2026-10-09-clef-omni-workers-ai/) |
| Cloudflare → Clef | `@cf/cloudflare/clef` | 0.24 | [S17](https://developers.cloudflare.com/workers-ai/models/clef/) |
<!-- /facts -->

10 月 9 日的更新同时降低了 Clef-flash 的价格和托管上下文上限；使用旧 64K 预算的请求要重新检查材料完整性。新增的 Clef-omni 接受音视频，输出仍是有限选项的判断。只需要文字决策时，也可以将它加入同任务比较。[S123](https://developers.cloudflare.com/changelog/post/2026-10-09-clef-omni-workers-ai/)

核对依据、模型价格、上下文限制与来源，集中在[Clef／Jev 比较](../comparisons/clef-vs-jev.md)，结构化字段在[路由目录](../catalog/decision-routes.json)，不在多页手工重复全部价格。

从实际问题进入：[材料到来后，下一步做什么](../use-cases/bounded-decision.md)。准备请求：[离线适配示例](../examples/decision-routing/README.md)。

本次于 2026-10-13 定向核对 Clef 系列的标价、托管上下文与输入字段；Jev 沿用 2026-10-02 的来源范围。此条目只说明公开接口和用途，不声称任何个人账户已取得全部模型权限或完成实测。
