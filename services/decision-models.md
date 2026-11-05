---
id: service.decision-models
reviewed_on: 2026-11-06
source_cutoff: 2026-11-06
review_scope: 11-06 仅补 Gateway 认证、账户级 token 与 model aliases；模型价格、窗口、Clairic 疑点和性能保留原核验范围
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

## 先看需要哪一种输出

| 想得到什么 | 候选能力 | 验收关注什么 |
|---|---|---|
| 从列好的动作或类别中选择 | Clef／Jev 有限决策 | 选项误判、输入完整性与阈值校准 |
| 取得未事先枚举的编号、日期、数值或原文片段 | Clairic 字段抽取 | 字段缺失、原文位置、截断与数值正确性 |
| 写解释、代码或长文，做开放式推理 | 通用生成模型 | 事实与推理、工具调用、生成内容 |

这个区分围绕输出空间；同为小模型不表示任务相同。Clairic 也支持计算、估计与预测，但类型正确并不证明内容正确，长算式宜抽取输入后交给代码。[S163] [S165]

## Gateway 认证与模型池别名

11 月 3 日起新 AI Gateway 必须认证；创建时省略 `authentication` 等于 `true`，显式 `false` 返回 400。旧的未认证 gateway 可继续原设置，但一旦开启就不可关闭。REST `/ai/run` 使用标准 `Authorization`；`gateway.ai.cloudflare.com` 的 provider-native URL 使用 `cf-aig-authorization`，Workers binding 保持预认证。[S213] [S214]

AI Gateway Read／Run／Edit token 是 **account-scoped**，不能限制单个 gateway；Run token 可调用同账户其他 gateway，包括它们存储的 provider keys。按不同 gateway 名称或 alias 分组不提供这种权限隔离；官方建议按需使用独立账户或 Worker-side binding。[S214]

11 月 4 日新增 model alias：应用以 `custom/<name>` 调用一组模型，REST 用 `cf-aig-gateway-id` 指定 gateway，可按顺序 fallback 或 smart routing。alias 不转换不同模型的输入协议，配置也可能暂时命中缓存；条件分支、百分比分流和流程内限制仍使用 dynamic routes。它改变接入和路由，不提供本书的模型质量结论。[S215] [S216]

## 接入方式与模型隔离，另看两项变化

10 月 21 日起，Agents SDK 用 `createAI` 统一旧 Workers AI／Gateway provider；原两包已 deprecated，AI Search 转到独立 provider。模型、供应路径和价格仍分开判断；具体参数和 fallback 条件见[API 维护](../reference/api-maintenance.md#模型-provider-迁移保留调用条件)。[S179] [S180]

10 月 26 日公开的事故报告涉及 **Workers AI 的 `@cf/zai-org/glm-5.3` 部署**：8 月 27 日至 9 月 9 日，过长输入触发 KV cache 跨请求暴露；官方称 9 月 9 日修复恢复，未影响其他 Workers AI 模型。这是已修复事故的披露，不是本周新发生，也不能推广到所有同名模型入口。本书据此提醒：长上下文验收还要核对返回内容、请求隔离和来源，HTTP 200 或 token 用量正确不能独自证明这些条件。[S200]

## Clairic：有类型的值与可定位原文

Clairic 于 **2026-10-19** 进入 preview，Workers AI 选择器为 `@cf/cloudflare/clairic`。传入 `state` 和 `fields`，返回每个字段的 typed value；`text` 可附原文字符位置，缺少依据时 `value` 可为 `null`。输入标价 **$0.10／百万 tokens**，没有生成输出 token 费用。[S163] [S164]

例如下面的合成部署通知可以定义版本、时间、错误代码和缺失的负责人字段。这只是供另行授权试验使用的 binding 输入形状，没有发出模型请求：

```json
{
  "model": "clairic",
  "state": "部署通知：版本 v2.4.1 于 2026-10-19T09:30:00Z 发布。错误代码 E_TIMEOUT。",
  "fields": {
    "version": {"type": "text"},
    "occurred_at": {"type": "datetime"},
    "error_code": {"type": "text"},
    "owner": {"type": "text", "instructions": "通知明确写出的负责人"}
  }
}
```

先检查 `answers.*.value` 与已知材料相符、缺失负责人返回 `null`；字符 span 能定位回原文。把错误代码移至材料尾部，再检查 `truncated` 和尾部证据是否仍可见，记录 `p_null`、confidence 与实际失败。中文、emoji 的 offset 应以返回位置回读确认，不能假定所有语言运行时的字符串索引等价。[S164]

### 65,536 与 8,192：暂不能合并成一个输入承诺

10 月 20 日查阅、10 月 28 日复看时，同一模型页的表格仍写 **65,536-token context**，`fields` 说明写字段和材料装入 **8,192-token pass**。两者关系没有解释清楚，本书保留疑点；先用短材料验证，不把较大的数字当成完整读取保证。字段会拆分为多个 pass，费用看响应的 `usage.input_tokens` 和 `usage.passes`，不能仅以原文长度乘单价。多 pass 可能重复计入材料是费用核查理由，具体计量仍以实际响应与后续官方澄清为准。[S164]

从长聊天判断一个人重视什么，还涉及语境、修订和评价标准；字段类型齐全不能替代这类质量验证。本页没有把抽取能力写成已经通过的记忆理解实验。

## 通用生成路线的一个新入口

Workers AI 新增 `@cf/deepseek-ai/deepseek-v4.1-flash-1017`，模型卡列 **1,048,576 tokens**，输入 **$0.30／M**、输出 **$1.20／M**、缓存输入 **$0.006／M**。需要 Workers Paid 或预付 AI Gateway credits。它提供生成、视觉、reasoning 与 function calling，属于上表的生成路线；没有与 Clef／Clairic 做本仓库质量对比。[S170] [S171]


从实际问题进入：[材料到来后，下一步做什么](../use-cases/bounded-decision.md)。准备请求：[离线适配示例](../examples/decision-routing/README.md)。

本页 2026-10-20 新增 Clairic 与 DeepSeek 路线；Clef 系列的标价、托管上下文与输入字段保留 2026-10-13 核对范围，Jev 沿用 2026-10-02。此条目只说明公开接口和用途，不声称任何个人账户已取得全部模型权限或完成实测。

[S163]: https://developers.cloudflare.com/changelog/post/2026-10-19-clairic-workers-ai/ "Clairic preview：有类型的字段抽取"

[S164]: https://developers.cloudflare.com/workers-ai/models/clairic/ "Clairic 模型卡、输入字段与上下文说明"

[S165]: https://blog.cloudflare.com/clairic-extraction-model/ "Clairic 抽取、决策与生成的输出空间"

[S170]: https://developers.cloudflare.com/workers-ai/models/deepseek-v4.1-flash-1017/ "DeepSeek V4.1 Flash 1017 模型卡"

[S171]: https://developers.cloudflare.com/changelog/post/2026-10-19-deepseek-v4.1-flash-workers-ai/ "DeepSeek V4.1 Flash 1017 Workers AI 发布"

[S179]: https://developers.cloudflare.com/changelog/post/2026-10-21-createai/ "createAI 替代旧 Workers AI 与 Gateway provider"
[S180]: https://developers.cloudflare.com/agents/models/ "Agents Models：连接、fallback 与 stream resume"
[S200]: https://blog.cloudflare.com/kv-cache-exposure-remediation/ "Workers AI GLM-5.3 跨请求 KV cache 暴露事故与修复披露"

[S17]: https://developers.cloudflare.com/workers-ai/models/clef/ "Clef 模型卡"

[S18]: https://developers.cloudflare.com/workers-ai/models/clef-flash/ "Clef-flash 模型卡"

[S73]: https://developers.cloudflare.com/ai/models/typesafe/jev/ "Jev：Cloudflare 第三方模型目录"

[S123]: https://developers.cloudflare.com/changelog/post/2026-10-09-clef-omni-workers-ai/ "Clef-omni 发布与 Clef-flash 降价／上下文收缩"

[S124]: https://developers.cloudflare.com/workers-ai/models/clef-omni/ "Clef-omni 模型卡与媒体输入预算"

[S213]: https://developers.cloudflare.com/changelog/post/2026-11-03-required-authentication/ "新 AI Gateway 强制认证"

[S214]: https://developers.cloudflare.com/ai-gateway/configuration/authentication/ "AI Gateway 认证头与账户级 token 范围"

[S215]: https://developers.cloudflare.com/changelog/post/2026-11-04-model-aliases/ "AI Gateway model aliases 发布"

[S216]: https://developers.cloudflare.com/ai-gateway/features/routing/model-aliases/ "Model aliases 的路由与输入边界"
