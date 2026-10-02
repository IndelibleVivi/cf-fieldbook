---
id: service.decision-models
reviewed_on: 2026-10-02
evidence: official-documents-only
---

# 决策模型与 Cloudflare 接入

从这里读一件事：拿到一段材料以后，只需要类别、概率或等级时，可以先试专门的决策模型。接入网关与模型本身分开选择。

Cloudflare 自有的 Clef／Clef-flash 与第三方 Jev 都能进入现有 AI 调用路径，但有不同的模型选择器、输入限制和计费。API 形状相近不等于可共享经过校准的阈值。

<!-- facts: cf-routes -->
| 路线（接入 → 模型） | 模型选择器 | 输入 USD / 百万 token | 来源 |
|---|---|---:|---|
| Cloudflare → Jev | `typesafe/jev` | 0.042 | [S73](https://developers.cloudflare.com/ai/models/typesafe/jev/) |
| Cloudflare → Clef-flash | `@cf/cloudflare/clef-flash` | 0.09 | [S18](https://developers.cloudflare.com/workers-ai/models/clef-flash/) |
| Cloudflare → Clef | `@cf/cloudflare/clef` | 0.24 | [S17](https://developers.cloudflare.com/workers-ai/models/clef/) |
<!-- /facts -->

核对依据、模型价格、上下文限制与来源，集中在[Clef／Jev 比较](../comparisons/clef-vs-jev.md)，结构化字段在[路由目录](../catalog/decision-routes.json)，不在多页手工重复全部价格。

从实际问题进入：[材料到来后，下一步做什么](../use-cases/bounded-decision.md)。准备请求：[离线适配示例](../examples/decision-routing/README.md)。

此条目只说明公开接口和用途，不声称任何个人账户已取得全部模型权限或完成实测。
