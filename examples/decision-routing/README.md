# 同一语义输入，不同模型外壳

这是一个**离线接口准备示例**，不是模型 client，也不是已运行的比较。没有 key、网络请求、推理结果或自动计费。手工编写的中文输入用于查看结构，不来自真实记录。

```bash
python3 examples/decision-routing/payloads.py
python3 -m unittest discover -s tests -p 'test_decision_example.py' -v
```

输出四份 CF 统一 `/ai/run` 请求体：`typesafe/jev`、`@cf/cloudflare/clef-flash`、`@cf/cloudflare/clef-omni`、`@cf/cloudflare/clef`。统一 REST 使用外层 `{ model, input }`。[S79] 三款 Clef 在 input 内保留对应的 `model` 字段；Jev 无此内层字段。[S17] [S18] [S73] [S124]

校验故意保持窄：拒绝未知 route、空题目、不支持的 primitive、过大的演示输入。四款模型都只构造文字／JSON state；没有媒体参数、编码或 tokenizer。16 KiB 是示例自己的字节上限，与托管模型的 token 窗口分别处理；此函数不替代完整供应商 schema 或响应校验。

真正接入前要单独处理：账户与模型权限、结算、deadline、外层 error envelope、cache／log 策略、实际响应版本、usage 和失败记录。不能因为本地结构测试通过就将 live 状态标为可用。

2026-10-13 定向核对 Clef 系列的选择器和文字／JSON 输入字段；Jev 与统一 REST 沿用 2026-10-02 的核对范围。Omni 的音视频能力不在本例执行范围内。

费用函数只做 `输入 token / 1,000,000 × 标价`。不默认扣减免费额度，也不把所有路线都加上相同充值费。当前价格另见 `catalog/decision-routes.json`，专题见 [Clef 与 Jev](../../comparisons/clef-vs-jev.md)。

测试分别检查固定数字的费用算术，以及当前路由目录的全部 CF 选择器和费用。后者会在新增目录路线但漏接示例时失败；通过测试不代表真实输入的 token 数已知。

[S17]: https://developers.cloudflare.com/workers-ai/models/clef/ "Clef 模型卡"
[S18]: https://developers.cloudflare.com/workers-ai/models/clef-flash/ "Clef-flash 模型卡"
[S73]: https://developers.cloudflare.com/ai/models/typesafe/jev/ "CF Jev 模型目录"
[S79]: https://developers.cloudflare.com/ai-gateway/usage/rest-api/ "Cloudflare AI Gateway：统一 REST API"
[S124]: https://developers.cloudflare.com/workers-ai/models/clef-omni/ "Clef-omni 模型卡"
