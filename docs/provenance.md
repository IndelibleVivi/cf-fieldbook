# 来源与历史版本

`dist/` 保存 2026-10-02 阅读版 r3 的三册 Markdown、HTML 和 PDF，作为固定的历史出版物；当前 Markdown 与 catalog 持续维护，五个离线例子使用合成输入。

产品事实引用 Cloudflare 的公开官方资料；第三方模型引用其原厂或供应入口，浏览器与协议行为引用对应维护方。编辑分析与匿名历史观察另标证据范围，不以私人资料作为产品证据。

## 来源核验范围

r3 重新核对来源 S16–S18，并补充 S73–S83，重点覆盖 Clef / Jev、接入入口与价格。其他产品条目沿用此前记录，不表示所有来源都在同一天重新核验。Vercel 目录当时仅有官方搜索摘录，展示价不作为精确计费单价。

各来源的链接与读取日期见 [来源索引](../catalog/sources.json)；每篇维护内容的状态、核验范围与依赖见 [内容索引](../catalog/entries.json)。构建时间、测试时间和事实核验时间分别记录。

2026-10-03 新增 S84–S97，供[三篇实践记录](../practice/README.md)解释 Workers、R2、Vectorize、Access、Tunnel、service worker 与 MCP 授权的通用机制。这些链接在编辑时查阅；各篇的实际系统观察仍使用正文标明的历史日期，没有新的云端验收。MDN 是浏览器技术参考，MCP 规范由协议项目维护，二者不是 Cloudflare 文档。

2026-10-03 新增 S98–S113，核对 Observability、Traces/SQL、PiHarness、Web Search API、Protected Quick Tunnels，以及补充 R2 费用与新项目脚手架。当时观察到 12 GB-month / 10 GB-month 与 Exa ZDR 的官方页面差异；前者已在 10-20 按现行价格更新，历史报告保留，Exa 原核验范围未变。此范围不刷新旧条目或 10-02 历史报告的核验日期，没有账户或付费调用。

2026-10-05 新增 S114–S117，定向核对 Artifacts 官方示例仍使用 Sandbox v0、Sandbox 1.0 的迁移接口、Access 严格 Service Token 认证，以及当日到达移除日期的 Tunnel 私网路由与连接查询 API。结论进入手册、实施参考与首发选编；没有执行账户配置、API 迁移或云端恢复实验。首发图文的三款 CF 模型输入单价另于当日核对，未由此刷新专题的全篇来源日期。

2026-10-08 新增 S118–S122，定向查阅官方 SDK 入口、Go `v7.12.0` README 与 release、OpenAPI schemas 仓库用途、R2 调用入口，并复看 S117 的 Tunnel 字段迁移。Go 默认值固定该版本，不泛化到其他语言；OpenAPI 仅核对仓库用途，没有全量 schema diff。资料进入 API 维护和项目判断指南，操作例子使用语言无关的合成模型。未安装 SDK、访问账户、读取其他项目现状或执行云端调用；旧正文与历史来源日期没有整体刷新。

2026-10-13 新增 S123–S142，定向查阅 Clef 模型变更、Workers 排空、agent search／fetch 和 OpenCodeHarness、Markdown 响应契约、MCP Skills、Queues／D1 地点约束、HTTP/3 499、Logpush 机制及 Go `v7.13.0` release；另复看 S07／S08／S17／S18。Artifacts 价格页／changelog 的 10-14 与博客的 10-15 仍保留冲突。Omni、Clef、Flash 的精确窗口分别按模型卡登记，不能把公告中的 K 一律换算。

这批资料进入当前页与独立的[10 月 13 日观察](../reports/2026-10-13.md)。来源传播、单值／数组引用、事实块同步和四款模型的文本请求做本地检查；不包含真实模型请求、账号权限、harness 云端恢复或账单验收。原 provider 价格、旧性能表、观测费用及历史出版物保留各自核验范围，接口通过不构成全书事实认证。

2026-10-20 定向查阅近期公开来源：AI Search 的 CJK tokenizer、匹配模式、限制与新计价；Clairic preview、typed extraction 与 context/pass 疑点；Browser 跨轮存活和中断、MCP Events 与 step-up、cf docs search；CWS／Gateway Forward 的实际请求路径；Local Explorer Cron、infrastructure SSH、Tunnel 额度与 Builds 工具链，以及 DeepSeek V4.1 Flash 1017。各来源的实际查阅范围由目录逐条记录，不因资料截止日推进就重核全部旧事实。

另复看 S07／S08／S10／S100／S111 的相关价格与日期：Observability 公布方案现为 10 GB-month，仍在 12-01 生效，页面算例却未对齐；Artifacts 10-14／15 的日期冲突继续保留，但两日已过去。当前正文和费用表同步，原报告与冻结文件保留。中文查询样本、Clairic 短材料与出站路径是合成验收设计；没有调用模型、建立云索引、安装 CWS proxy、修改 Gateway、读取账号或核对真实账单。网页、本地测试与官方来源分别记录。

2026-10-26 新增 S172–S174，仅查阅 Workers Static Assets 静态站、纯静态 `assets.directory`／脚本和 binding 边界，以及 Wrangler 本地预览、部署与删除命令。资料架的可选开发依赖实际安装为 Wrangler `4.152.0`，真实 lockfile 随源保留；普通构建和例子检查不安装或运行 Wrangler。新增完整取得、漏重建观察与独立四文件发布目录；本地目录、预览、dry run 和手册候选分别检查，没有登录账号、上传、更新或删除云资源。手册资料上界推进至 10-26，实施参考题头对齐其已有 10-20 范围；Observability 与其他未复核来源日期不因此刷新。

2026-10-28 新增 S175–S203，从官方 changelog 与博客 10-20 至 10-27 的变化进入机制文档，定向核对 Computer／Think／Pi 恢复和迁移、createAI、MCP 旧入口、Workflows／D1、Tunnel／Access、source maps／Builds／Sandbox、观测与字段变化，以及 WAF 和 GLM-5.3 已修复事故的披露。调查范围与未扩成教程的方向见[10 月 28 日观察](../reports/2026-10-28.md)。事故披露日与发生／修复日分开；没有迁移 schema、安装 SDK、测试真实模型或变更账户。

本轮另复看 S07／S08／S10／S17／S18／S73／S100／S111／S124／S164 的指定条款。Observability 官方算例已与 $7.25 一致，费用固定 `as_of` 单独推进至 10-28，生效仍为 12-01；Artifacts 日期冲突与 Clairic context/pass 疑点保留。CF 决策路线只复看标价、输出费和窗口，其他 provider、性能和旧输入细节不刷新；原复核期限继续覆盖尚未查阅部分。历史报告、独立增补、`dist/` 和冻结候选未改写，也没有新 PDF Release。

[首发选编](../reports/2026-10-first-release.md)是独立的新编排，按主题吸收两篇历史观察，保留继承事实、后续增补和定向核查各自的范围。原 10 月 2 日和 10 月 3 日报告不被覆盖，构建日期也不作为它们的新事实日期。

## 历史资料的使用

实践手册和实施参考分别解释入口与权限、数据职责、异步恢复、私有回源及浏览器会话边界。[实施参考第 16 章](../reference/implementation.md)集中列出容易误判的做法及其核查依据。

历史实践用于解释机制；离线例子使用重新构造的合成输入，不继承私人运行环境或真实账号数据。出版物和本地测试都不构成云端实测结果。

带截止日期的报告保留当时的文字与来源定义。后续价格变化进入当前服务页；原报告的错误通过明确勘误修正，不能由构建过程自动改写。维护方式见[内容生命周期](lifecycle.md)与[出版流程](publication.md)。
