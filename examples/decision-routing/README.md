# 同一语义输入，不同模型外壳

这是一个**离线接口准备示例**，不是模型 client，也不是已运行的比较。没有 key、网络请求、推理结果或自动计费。手工编写的中文输入用于查看结构，不来自真实记录。

```bash
python3 examples/decision-routing/payloads.py
python3 -m unittest discover -s tests -v
```

输出三份 CF 统一 `/ai/run` 请求体：`typesafe/jev`、`@cf/cloudflare/clef-flash`、`@cf/cloudflare/clef`。后两份在 input 内保留模型卡要求的 `model` 字段，Jev 不擅自添加该字段。

校验故意保持窄：拒绝未知 route、空题目、不支持的 primitive、过大的演示输入。16 KiB 是示例自己的上限，不是模型的 token 上限；此函数不替代完整供应商 schema 校验、响应校验或 tokenizer。

真正接入前要单独处理：账户与模型权限、结算、deadline、外层 error envelope、cache／log 策略、实际响应版本、usage 和失败记录。不能因为本地结构测试通过就将 live 状态标为可用。

参考：[CF Jev](https://developers.cloudflare.com/ai/models/typesafe/jev/)、[Clef](https://developers.cloudflare.com/workers-ai/models/clef/)、[Clef-flash](https://developers.cloudflare.com/workers-ai/models/clef-flash/)、[统一 REST](https://developers.cloudflare.com/ai-gateway/usage/rest-api/)。文档核对于 2026-10-02。

费用函数只做 `输入 token / 1,000,000 × 标价`。不默认扣减免费额度，也不把所有路线都加上相同充值费。当前价格另见 `catalog/decision-routes.json`，专题见 [Clef 与 Jev](../../comparisons/clef-vs-jev.md)。
