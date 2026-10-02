# 出版：从可编辑资料到可引用版本

![人工编辑的源进入离线检查和预览；确认后从冻结输入生成版本化出版物，勘误以新修订发布。](../assets/diagrams/publication.svg)

[Mermaid](../diagrams/src/publication.mmd)

## 当前资料与历史报告

`tools/content.py` 从 `catalog/decision-routes.json`、来源索引和例子中的成本函数生成三个维护页的显式 fact blocks。只有 `sync` 会修改这些块；`check` 发现漂移并失败。叙述与结论仍由编辑者维护，不能因为数字同步就推定解释仍成立。

```bash
python3 tools/content.py sync
python3 tools/content.py check
```

构建阅读站时使用只读投影；正式冻结前要求源中的 fact blocks 已同步并经过审阅。模型、入口、选择器、价格、tokenizer 和上下文都取自同一记录，未知费用不作零计算。估算是给定计费 token 数的乘法，不是跨模型同文本 token 数相同的承诺。

`reports/` 拥有自己的历史文字与来源定义，不参与上述同步；报告重排时也从自己的定义生成书目。旧 `dist/` 继续保留 r3 bytes，本轮构建不会覆盖它。之后的改价或开放状态变化进入当前维护页，只有原报告在当时已经错误才作勘误。

## 冻结并生成三册

先按 [贡献说明](../CONTRIBUTING.md) 安装依赖。以下命令生成新本地候选 ID；已有 ID 不能覆盖，失败后的候选也保留供检查，修正后用新 ID。

```bash
.venv/bin/python tools/editions.py freeze 2026-10-02-r4
.venv/bin/python tools/editions.py build 2026-10-02-r4
.venv/bin/python tools/editions.py check 2026-10-02-r4
```

默认生成带日期观察、实践手册、Clef/Jev 比较的 Markdown、HTML、PDF。只需要前两种时可用 `build <id> --formats md html`。macOS 的 WeasyPrint 动态库路径说明见贡献文档。

输出在 `.build/editions/<id>/`，不会自动进入 Git 或被阅读站分发：

- `inputs/`：显式允许的正文、catalog、例子、SVG/Mermaid、样式、渲染工具及依赖声明的文件快照。
- `outputs/`：三册的新产物；相互关联的 HTML 要放在一起阅读。
- `edition.json`：版次身份、输入和产物摘要、可得的 source commit、实际 Python/库版本、系统字体政策、沿用的核验范围。

输入摘要是内容身份的依据，commit 只是辅助来源，未提交的输入也如实记录。冻结后的渲染使用 `inputs/tools/render.py` 和快照里的数据、图与样式，不读取工作树的实时材料。编辑源、原有 PDF 与核验日期不会被构建改写。输入清单、摘要或已生成输出不符时，检查失败。

快照固定内容和渲染代码，不打包 Python、浏览器或字体。依赖按记录安装；跨系统排版可能不同，要重新视觉验收，不能承诺 PDF 跨平台逐字节重现。PDF 只保留网络来源和文内目录链接，仓库相对链接不转换成本机 `file:` 地址。渲染禁止远程资产请求，既不补抓事实，也不调用云端例子。

## 检查、分发与撤下

普通检查包括元数据、引用与依赖、例子测试、算术、事实块一致性，以及图示源与产物同步。页面和印刷样式变更还需要实际视觉检查。结构检查不能证明事实为真；本地例子通过不能证明云服务表现。

`.build/editions/` 是本地候选快照，不是可以整目录自动公开的 release 包；它含构建输入和例子。公开前审阅具体 revision、许可、核验范围及待分发文件。静态站仅分发当前允许的内容及明确附件，见 [阅读站](reading-site.md)。旧版本的撤下需要同时处理既有站点、附件、下载和缓存；修改索引不会远程清除曾经发出的文件。

明确触发的 live 实验另需预算、资源清单、目标、清理与授权，不属于出版构建。正式发布及部署也仍由维护者决定；本地候选不意味着 release、GitHub 仓库或公网网址已经存在。

## 图与署名

Mermaid 结构和文字只在 `diagrams/src/` 编辑；SVG 是阅读投影。`assets/diagrams/manifest.json` 记录源、配置、产物摘要和实际引擎版本。摘要用于发现漂移，不能证明图的语义正确。升级引擎后重建并逐图检查，操作见 [图示说明](../diagrams/README.md)。

封面写作品名、日期和版次，作者为 Faye & Cove。GitHub 以明确地址呈现；文末为 *made by Faye & Cove*。来源、署名和许可各自独立，不从署名推定公开授权。
