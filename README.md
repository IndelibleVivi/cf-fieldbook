# CF Fieldbook

**Cloudflare 用途、选择与实践的持续参考。**

从手边的问题出发，认识相关服务，比较可选路线，再运行一个能检查的小例子。面向个人开发者、独立创作者与协作 agent；这是 Faye & Cove 编辑的独立参考，不是 Cloudflare 官方文档或一键部署平台。

正文以中文为主，Markdown 本身可以阅读；静态网站提供目录、来源跳转和本地搜索。代码、来源和出版工具留在同一仓库，便于在判断改变时找到受影响的内容。

## 从这里读

| 阅读方向 | 入口 |
|---|---|
| 从一个用途开始 | [有限决策与下一步动作](use-cases/bounded-decision.md) · [任务中断与恢复](use-cases/recoverable-jobs.md) |
| 认识一项服务 | [决策模型：Clef 与 Jev](services/decision-models.md) |
| 本期变化 | [2026-10-02 新发布观察](reports/2026-10-02.md) |
| 连起来理解基础设施 | [个人基础设施实践手册](guides/handbook.md) |
| 比较模型与接入入口 | [Clef / Jev 专题](comparisons/clef-vs-jev.md) |
| 查看代码与精确命令 | [三个离线例子](examples/README.md) · [实施参考](reference/implementation.md) |

## 先运行一个真实机制

只需 Python 3.11+，不登录、不联网、不调用模型：

```sh
python3 examples/job-state/demo.py
```

演示会打印：任务登记后仍是 `pending`；worker 退出后，新的执行者等待租约到期再领取；旧 generation 的迟到完成被拒绝；外部响应丢失后进入 `uncertain`，重复领取不会自动重放。临时 SQLite 在结束时清理。它验证一个恢复机制，不是完整云端队列实现；[使用边界](examples/job-state/README.md)也明确列出没有解决的外部动作崩溃窗口。

## 在本地阅读

Python 环境只负责生成静态文件，阅读页面不需要后端：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-render.txt -r requirements-design.txt
.venv/bin/python tools/build_site.py
python3 -m http.server 8767 --bind 127.0.0.1 --directory .build/site
```

在浏览器打开 `http://127.0.0.1:8767`。依赖安装需要软件源网络；构建与阅读本身不请求云 API，没有追踪、登录或付费执行入口。也可直接阅读仓库 Markdown。网站的生成、附件与撤下规则见[阅读站说明](docs/reading-site.md)。

## 内容如何维护

![来源与重新构造的实践进入 Markdown、事实登记和示例代码；检查后生成阅读网站和版本化出版物，私人运行环境留在仓库外。](assets/diagrams/architecture.svg)

[Mermaid 源码](diagrams/src/architecture.mmd) · [全部五张图](diagrams/README.md)

解释归 Markdown，跨页精确数据归 `catalog/`，执行行为归 `examples/`。网站与 PDF 读取这些来源；事实核验、代码测试和云端实测分别记录。服务页持续维护，带截止日期的报告保留当时判断。后来的改价不自动回写历史报告。

```sh
python3 tools/fieldbook.py impact data.decision-routes
python3 tools/fieldbook.py due --as-of 2026-11-01
python3 tools/fieldbook.py check
python3 tools/check.py
python3 tools/content.py check
.venv/bin/python -m unittest discover -s tests -v
node --test examples/health-worker/worker.test.mjs
```

Node.js 20+ 用于 Worker 测试；Mermaid 只在修改图示时需要安装。[贡献与维护](CONTRIBUTING.md)给出依赖、修改位置与验证方法；[出版流程](docs/publication.md)说明共源数据和冻结版次的构建。

## 状态与边界

这是持续编辑的 source-available 参考仓库；具体实现、验证和未启用能力见[当前状态](docs/current-state.md)。CF 内容继承 2026-10-02 阅读版 r3 的来源记录；局部工程验证不能代表全篇事实重新核验。旧三册 Markdown / HTML / PDF 固定保留在 `dist/`，用于历史阅读；新构建进入 `.build/`，不覆盖旧版。

公共例子使用合成输入，没有账号凭据或真实运行数据。私人聊天、工作记录和原始 exports 不属于本仓库。云端实验、定期上游监控、网站部署和 release 均不由本地检查自动启用。

原创功能代码采用 [SUL-1.0](LICENSE)；原创正文、出版物、独立图形和资料编排采用 [CC BY-NC-SA 4.0](LICENSE-DOCUMENTATION.md)。这是一份 source-available 项目，不是无商业使用限制的 OSI 开源软件；具体路径与第三方例外见[许可与权利范围](LICENSE-STATUS.md)。

[项目规格](SPEC.md) · [架构](docs/architecture.md) · [生命周期](docs/lifecycle.md) · [内容设计](docs/content-design.md) · [AGENTS](AGENTS.md)

---

GitHub · [github.com/IndelibleVivi](https://github.com/IndelibleVivi)  
*made by Faye & Cove*
