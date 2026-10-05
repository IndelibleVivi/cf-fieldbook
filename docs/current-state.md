# 当前状态

2026-10-05 · [公共源码](https://github.com/IndelibleVivi/cf-fieldbook)，默认分支 `main`。

- 三部作品为[个人基础设施实践手册](../guides/handbook.md)、[Clef / Jev 专题](../comparisons/clef-vs-jev.md)、[2026.10 新发布观察首发选编](../reports/2026-10-first-release.md)。选编保留完整发布主题并整合后续四组变化；10 月 2 日、10 月 3 日观察保持历史身份，不自动同步新价格。服务与实践仍可独立阅读。
- 10 月 5 日定向核查 Access 严格 Service Token 条件、Tunnel 私网路由／连接查询变更与 Artifacts / Sandbox v0、1.0 的接口边界，进入手册与实施参考。没有因此刷新全书事实日期，也没有新的账户或云端实测。
- 新增 Observability、PiHarness、Web Search API、Protected Quick Tunnels 四组主题。新增官方来源查阅截止 2026-10-03，原有条目仍保留各自核验范围，没有新的账户、云端或模型实测。费用记录区分当前 Workers Logs 条款与 2026-12-01 的统一计费；博客／pricing 包含量和 Web Search ZDR 的来源差异保留在正文。
- 四个例子默认离线。[三份文档的小资料架](../examples/reading-shelf/README.md)可直接阅读与下载，由合成原件重建；手册沿同一材料解释权限、版本、任务和检索的扩展设计。它没有运行数据库、云端索引或身份系统。
- [任务恢复观察台](https://indeliblevivi.github.io/cf-fieldbook/examples/job-state/demo.html)回放实际 SQLite 模型的五种合成场景。事件反馈紧邻控制区，支持场景、时间、步骤与播放；没有云端实测声明。外部副作用重复的反例仍保留，继续使用[离线工单](../templates/job-recovery-task.md)可复现。
- 阅读站默认冷白，可切暖纸；选择只存读者本地浏览器，无 JavaScript 时保持冷白。篇类题头、透明母题、篇尾日出印与轻动画沿用青橙视觉；动画遵循减弱动态设置。键盘定位用内部底色与下划线，署名集中于页脚。
- 三部作品的编排归 `catalog/publications.json`，Markdown 仍拥有正文。稳定章节 ID 与显示编号分开，旧网页锚点保留；新增报告按条目和正文身份编排，不再修改 renderer 内的固定日期。
- edition 可独立冻结一个作品，也可一次生成三部作品的独立候选。冻结固定所需正文、数据、图示、词表与渲染代码；所引用词义嵌入当版附录。2026.10 首发的三册完整 PDF 已生成本地候选并检查分页与链接，没有发布新的 Release；`dist/` 固定 r3 历史文件未改。
- 首发兼容候选 `first-release-20261005-r4-{comparison,launches,handbook}` 修复本机 PingFang SC 的 OpenType / CFF 封装在 PDFKit 与 Quick Look 下缺字和错字形的问题。三册仍为 10 / 22 / 27 页，正文文字、链接和书签逐页保留；59 页正文已用 macOS 原生引擎复看，Quick Look 正文复现页恢复。读者确认 iPhone 微信中 r4 专题正文显示正常；其他分册与合订本没有逐页手机验收。新文件没有登记为 GitHub Release；旧冻结文件保留。
- 六张 Mermaid 图由锁定的 11.17.2 引擎生成；新增资料架更新／撤下图明确为扩展设计。入口路线与任务状态的横／窄 SVG 继续共用语义源。
- 当前正文、来源说明与阅读投影不保留与本作品无关的材料致谢；历史固定出版物不在本轮改写。来源核验与分发边界见[来源说明](provenance.md)。
- `Checks and Pages` 对提交运行离线检查，主分支通过后更新[正式阅读站](https://indeliblevivi.github.io/cf-fieldbook/)，PR 只检查。最新运行结果见[GitHub Actions](https://github.com/IndelibleVivi/cf-fieldbook/actions)；网站部署与出版物 Release 是两件事。
- 原创功能代码采用 SUL-1.0，原创内容采用 CC BY-NC-SA 4.0。第三方例外见[许可范围](../LICENSE-STATUS.md)。

当前没有云端例子 runner、定时来源监测或用户账号系统。构建与测试不会刷新来源日期；具体命令见[阅读站](reading-site.md)与[出版](publication.md)。
