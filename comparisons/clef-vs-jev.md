---
title: Clef 与 Jev：模型、入口与判断成本
subtitle: 一份面向个人开发者的决策模型比较
edition: 2026.10 · 专题 01 · 阅读版 3
source_cutoff: 2026-10-02
presentation_revision: 3
author: Faye & Cove
github: https://github.com/IndelibleVivi
credits: made by Faye & Cove
status: source-verified-comparison-not-live-benchmark
---

# Clef 与 Jev：模型、入口与判断成本

一个便宜的判断接口，值得拿来替代哪些大模型调用？这个问题不能只比较单价。还要知道返回的数字代表什么、模型读到了多少材料，以及一次误判会把后续工作带到哪里。

本篇核对截至 2026-10-02 的官方模型卡、接口和供应目录。下面的价格是标价，费用示例是演算，性能数据有明确出处；本资料包没有调用真实模型。不要把离线请求测试读成模型效果测试。

先用一个完整任务定位这篇比较：合成材料只说“资料 A 的标题是重试；正文尚未取得”。允许的动作是 `read_original`、`search_context`、`classify`、`insufficient`。此时规则基线要求读原文，模型的建议要与这条基线比较，而不是直接触发发布。

```json
{
  "state": "资料 A：标题为重试；正文尚未取得。",
  "questions": {
    "next_action": {
      "type": "choice",
      "instructions": "下一步怎样取得足够材料？",
      "criteria": {
        "read_original": "已有原件位置，正文尚未读到",
        "search_context": "原件仍缺所需上下文",
        "classify": "材料足够，可进行分类",
        "insufficient": "没有可继续取得的证据"
      }
    }
  }
}
```

这是我们自己的语义输入；各平台外壳见第 4 章。返回的选项分布表达模型建议，程序只允许执行上述动作，并记录实际选择与回读结果；这里没有伪造响应概率或实测表现。[S17] 对照的中英文、材料不足与选项扰动样本见[试验章节](#experiment)，真实模型测评仍须独立授权。

<!-- chapter: models -->

## 01 / 先把模型、接口与平台分开

**Jev 是 TypeSafe 的决策模型；Clef 与 Clef-flash 是 Cloudflare 的决策模型。Cloudflare 同时提供自有模型和第三方 Jev 的调用入口。** 因此，选择 CF 不等于只能用 Clef，比较 Jev 与 Clef 也不必同时搬迁账户和整套应用。[S17] [S18] [S73]

它们接收待判断的状态与带类型的问题，不以长篇回答为目标。`noul` 返回条件成立的概率；`choice` 在有限选项中选择并返回各选项概率；`score` 在有序等级上给出分数及分布。适合判断、分类和排序，不能直接替代负责开放式规划与写作的模型。[S76]

| 对象 | 解决的问题 | 不能从名字推出的事 |
|---|---|---|
| 模型 | 用什么权重做判断 | 在哪个地区、哪个平台实际运行 |
| API / SDK | 请求、响应和错误怎样表达 | 换一个模型 ID 就能无条件互换 |
| 接入与结算平台 | 使用哪种凭据、账单、日志和路由 | 后面一定是独立的推理供应商 |

一个常见的比较误差，是将“Jev 走 OpenRouter、Clef 走 CF”的总延迟写成模型速度差。这里同时变了模型和网络路径。更清楚的实验是先固定 CF，比较三款模型；再固定 Jev，比较原厂与不同网关。

<!-- chapter: providers -->

## 02 / 现在有哪些供应路径

<!-- facts: all-routes -->
| 路线（接入 → 模型） | 模型选择器 | 输入 USD / 百万 token | 来源 |
|---|---|---:|---|
| Cloudflare → Jev | `typesafe/jev` | 0.042 | [S73](https://developers.cloudflare.com/ai/models/typesafe/jev/) |
| Cloudflare → Clef-flash | `@cf/cloudflare/clef-flash` | 0.09 | [S18](https://developers.cloudflare.com/workers-ai/models/clef-flash/) |
| Cloudflare → Clef | `@cf/cloudflare/clef` | 0.24 | [S17](https://developers.cloudflare.com/workers-ai/models/clef/) |
| TypeSafe 原厂 → Jev 1.13 | `jev-1.13.0` | 0.042 | [S74](https://docs.typesafe.ai/models) |
| OpenRouter → Jev 1.13 | `typesafe/jev-1.13` | 0.042 | [S75](https://openrouter.ai/typesafe/jev-1.13/) [S76](https://openrouter.ai/docs/guides/community/jev) |
| Vercel AI Gateway → Jev | `typesafe-ai/jev` | 未知；目录显示 $0.04/M | [S81](https://vercel.com/ai-gateway/models/jev) |
<!-- /facts -->

各路线输入标价以上表为准；未知精确价格保持未知，不能把显示值当作更便宜的证据。Vercel 路线继承的证据仅为官方页面搜索摘录，不用于精确账单演算。[S17] [S18] [S73] [S74] [S75] [S81]

TypeSafe 原厂使用 `/v1/systemone`。OpenRouter 既有 `/api/alpha/decisions`，也有适配 TypeSafe SDK 的 `/api/v1/systemone`，使用 OpenRouter 的 key 与账单。CF 则提供 AI binding 和 `/accounts/{account}/ai/run` 统一 REST 入口，不能自行猜一个 CF `/decisions` 路由。[S74] [S76] [S79]

OpenRouter 的 Jev 供应商仍列为 TypeSafe，CF 目录也标明 Jev 为第三方。多接几个网关可以改变入口和结算方式，但不能据此声称已经获得几套相互独立的模型后端。[S73] [S75]

### 开放权重是另一条路线

Clef 与 Clef-flash 发布了 Apache-2.0 权重，可以研究和自托管；硬件、推理服务与维护成本由部署者承担。Jev 在这里列出的则是托管 API。把 Clef 自托管跑起来，是另一项实验，不应套用 CF 的按 token 标价。配套 CF 强化学习服务目前采用设计合作路线，不能当作 $5 Workers Paid 包含的自助训练功能。[S82] [S83] [S16]

<!-- chapter: cost -->

## 03 / 便宜多少，以及真正该算什么

假设一个月完成 10,000 次判断，每次的**总计费输入**为 5,000 token，包含状态、问题与选项，总计 5,000 万输入 token；不发生缓存和重试。按模型标价演算：[S17] [S18] [S73]

<!-- facts: costs -->
| 路线 | 输入用量假设 | 模型输入费用 |
|---|---|---:|
| Cloudflare → Jev | 50,000,000 计费 token；tokenizer：未核实 | $2.10 |
| Cloudflare → Clef-flash | 50,000,000 计费 token；tokenizer：未核实 | $4.50 |
| Cloudflare → Clef | 50,000,000 计费 token；tokenizer：未核实 | $12.00 |
<!-- /facts -->

这是假定各路线都计入同样数量 token 的对照，不是“同一句话天然使用相同 tokenizer”的保证。实际应读回每条路线的 usage；多题可以共用状态时，也不能把每道题都粗暴算成一次完整长请求。

CF Unified Billing 对充值另收 5%，例如购买 $100 credits 支付 $105；推理标价本身不加价。Workers AI 可以采用不同计费设置，不能给全部调用无条件乘上 1.05；走第三方 Jev 时尤其要明确使用的是哪条授权与结算路线。[S80]

个人用量下，每月几美元的模型价差可能小于一次错误路由造成的返工。更合适的成本表是：**模型 + 重试 + 大模型接管 + Worker／日志 + 人工核对**。一个更便宜但经常把“没读够材料”判成“可以开始”的模型，未必更省。

<!-- chapter: contracts -->

## 04 / “API 兼容”仍然需要适配层

### 相同的问题，可以有不同的请求外壳

CF 的 Jev 模型卡使用 `env.AI.run('typesafe/jev', { state, questions })`；Clef 模型卡除了外层选择器，还要求输入中的 `model: 'clef'` 或 `'clef-flash'`。统一 REST 入口另包一层 `{ model, input }`。本包离线示例把这些外壳分别构造，不把它们混成一个字符串替换。[S73] [S17] [S18] [S79]

Vercel 的示例使用 `experimental_evaluate`，其中布尔问题写作 `boolean`；这是 SDK 的表述，不能原样当成原厂 `noul` 请求。平台协议、SDK 版本、请求字段与返回字段都应在一次适配测试中保留。[S81]

### 上下文限制要按路由记录

下面保留每条入口自己的口径，不把请求总量与单个状态预算混成一个数字。

<!-- facts: contexts -->
| 路线 | 此入口的上下文说明 | 来源 |
|---|---|---|
| Cloudflare → Jev | Catalog: 32000 | [S73](https://developers.cloudflare.com/ai/models/typesafe/jev/) |
| Cloudflare → Clef-flash | 65536; max64 questions; images extension | [S18](https://developers.cloudflare.com/workers-ai/models/clef-flash/) |
| Cloudflare → Clef | 65536; max64 questions; images extension | [S17](https://developers.cloudflare.com/workers-ai/models/clef/) |
| TypeSafe 原厂 → Jev 1.13 | Total64000; state+longest-question32000 | [S74](https://docs.typesafe.ai/models) |
| OpenRouter → Jev 1.13 | Catalog:32000 | [S75](https://openrouter.ai/typesafe/jev-1.13/) [S76](https://openrouter.ai/docs/guides/community/jev) |
| Vercel AI Gateway → Jev | Not verified | [S81](https://vercel.com/ai-gateway/models/jev) |
<!-- /facts -->

Clef 当前 schema 允许最多 64 个问题，并提供最多四张嵌入式图片的扩展，不接受远程图片 URL；长状态可能被截断。模型宣传中的视觉能力不等于任意视频文件都能塞进当前请求。Jev 是纯文本输入，图片需要预先转换成文字，转换误差也应计入结果。[S17] [S18] [S74]

### 同名置信度，不能共享一个阈值

Jev 的 confidence 是从输出概率分布算出的统计量，不是另一个监督者确认的正确率。原厂也列出了否定、数值／日期、上下文干扰等已知边界：同义的 Noul 与 Choice 表述不一定给出一致结果，两个互补问题也未必严格相加为一。[S77] [S78]

因此，把旧模型的 0.9 阈值照搬给新模型，没有自动成立的理由。拒绝回答、交给更强模型、继续读取材料等出口应当在应用里明确存在。权限、精确计数和日期比较可以由程序确定的部分，不交给概率判断充当最终裁决。

<!-- chapter: evidence -->

## 05 / 厂商的比较，告诉了我们什么

Cloudflare 发布文中的自测并没有形成处处相同的排序。下面选取三项，展示排名会随任务改变；这些不是本资料包的实测，也不是独立复现。[S16]

| 指标 | Clef | Clef-flash | Jev |
|---|---:|---:|---:|
| When2Call · accuracy | 72.37 | 65.58 | 80.97 |
| CLINC150+OOS · macro-F1 | 97.43 | 66.77 | 89.27 |
| BRIGHT · nDCG@10 | 45.91 | 39.26 | 47.52 |

不能把不同比例尺的三项平均成自己的总分。更值得追问的是：面对“不属于任何现有类别”的输入，是否会硬选一个？检索相关性强，不代表工具调用时机也强；更大的模型，也不意味着每个任务一定优于小款。

速度同样应该回到实际入口测。关闭响应缓存，保留重试和失败，报告相同输入组的 p50、p95 与完成率，而不是只挑一条最快响应。供应商自测、网关实时统计和个人网络下的时延属于三种观察，不能拼成同一张排行榜。

<!-- chapter: experiment -->

## 06 / 第一轮试验应该怎样长出来

建议先做一个窄任务：收到材料以后，下一步是**直接分类、读取原文、检索上下文，还是材料不足**。这是可重做的建议性决策，不直接产生外部写入。先写简单规则作基线，再比较模型是否真的改善了规则做不好的部分。

样本先拆成开发集与留出集。中文、英文、中英混合分别保留；加入否定、修订、引述、相近选项、找不到答案与刻意缺少背景的材料。TypeSafe 明确说 Jev 的训练主要面向英语，CJK 可以处理但不保证同等表现，因而中文材料值得单独检验。[S74]

分两轮改变条件：第一轮在 CF 上比较 Jev、Clef-flash、Clef，固定任务与外壳适配后的语义输入；第二轮固定 Jev、相同语义版本与输入，再比较 TypeSafe／CF／OpenRouter。若某个入口不能钉住同一版本，就把它作为不同实验条件，而不是假装只换了网络。

最有用的指标通常不是一个总准确率，而是：在愿意接受的误判风险下，自动处理了多少；错误地认为材料足够的比例；交给人或大模型的比例；完成率、尾部延迟和每百次被接受判断的总成本。少量样本只能帮助发现问题，不能宣称已校准到千分之一风险。

另外做几项便宜的对照：交换选项顺序、替换同义词、加入无关段落、把一题单独发送或与其他问题合并。保持语义相同时结果变化多大，本身就是值得记录的性质。数据、prompt、选项集合和实际响应版本应一起保存，才能复读失败。

本包 `examples/decision-routing/` 只提供离线请求构造与成本演算。它没有配置账号、发送请求或生成看似真实的模型结果；首轮语义测评仍待执行。

<!-- chapter: maintenance -->

## 07 / 这篇专题怎样继续维护

服务页保留当前可用入口；用例页解释为何需要这个判断；示例固定请求形状和检查方法；专题记录比较；本期报告则保存当时知道的情况。新的价格或模型版本先更新来源和路由记录，再定位受影响的读物，不要求每次重写整份手册。

这里的最小比较单位建议是：**任务版本 × 输入集合 × 模型版本 × 供应路径 × 策略阈值**。缺掉任何一项，“上次好用，这次变差”都会难以解释。可以从一张简单的运行记录开始，不必先做在线 benchmark 平台。

<!-- SOURCES -->

## 来源索引

本篇的模型、接入路径与价格来源截至 2026-10-02 已核对，范围见[来源说明](../docs/provenance.md)。资料核验不等于账户或模型实测。

- **[S16]** · Clef 与强化学习平台发布
- **[S17]** · Clef 模型卡
- **[S18]** · Clef-flash 模型卡
- **[S73]** · Jev：Cloudflare 第三方模型目录
- **[S74]** · TypeSafe：Jev 版本、价格与上下文预算
- **[S75]** · OpenRouter：Jev 1.13 价格与供应商
- **[S76]** · OpenRouter：Jev 的两种接口
- **[S77]** · TypeSafe：confidence 的含义
- **[S78]** · TypeSafe：Jev 1.13 已知能力边界
- **[S79]** · Cloudflare AI Gateway：统一 REST API
- **[S80]** · Cloudflare AI Gateway：Unified Billing
- **[S81]** · Vercel AI Gateway：Jev 目录显示价与 SDK 示例
- **[S82]** · Cloudflare Clef：开放模型权重与模型卡
- **[S83]** · Cloudflare Clef-flash：开放模型权重与模型卡

## 关于这一版

这是面向个人使用的独立参考资料，不是 Cloudflare 官方出版物。产品事实保留来源，场景与判断属于编辑分析。本次未进行账户操作或云端部署。

GitHub：[github.com/IndelibleVivi](https://github.com/IndelibleVivi)  
*made by Faye & Cove*

[S16]: https://blog.cloudflare.com/clef-decision-models/ "Clef 与强化学习平台发布"
[S17]: https://developers.cloudflare.com/workers-ai/models/clef/ "Clef 模型卡"
[S18]: https://developers.cloudflare.com/workers-ai/models/clef-flash/ "Clef-flash 模型卡"
[S73]: https://developers.cloudflare.com/ai/models/typesafe/jev/ "Jev：Cloudflare 第三方模型目录"
[S74]: https://docs.typesafe.ai/models "TypeSafe：Jev 版本、价格与上下文预算"
[S75]: https://openrouter.ai/typesafe/jev-1.13/ "OpenRouter：Jev 1.13 价格与供应商"
[S76]: https://openrouter.ai/docs/guides/community/jev "OpenRouter：Jev 的两种接口"
[S77]: https://docs.typesafe.ai/confidence "TypeSafe：confidence 的含义"
[S78]: https://docs.typesafe.ai/model-jaggedness/jev-1.13 "TypeSafe：Jev 1.13 已知能力边界"
[S79]: https://developers.cloudflare.com/ai-gateway/usage/rest-api/ "Cloudflare AI Gateway：统一 REST API"
[S80]: https://developers.cloudflare.com/ai-gateway/features/unified-billing/ "Cloudflare AI Gateway：Unified Billing"
[S81]: https://vercel.com/ai-gateway/models/jev "Vercel AI Gateway：Jev 目录显示价与 SDK 示例"
[S82]: https://huggingface.co/Cloudflare/clef "Cloudflare Clef：开放模型权重与模型卡"
[S83]: https://huggingface.co/Cloudflare/clef-flash "Cloudflare Clef-flash：开放模型权重与模型卡"
