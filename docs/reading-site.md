# 本地阅读站

静态阅读站从同一份 Markdown、catalog、公开例子和图示构建。首页提供“从用途开始”“认识服务”“本期变化”三条入口；全部资料页可按目录阅读，也可以在浏览器内搜索标题与全文。

这是本地构建候选。网站生成、浏览器检查、作者的美术接受与公共发布是分别发生的事情。建站不更新正文的来源核验日期，不访问来源网站，不调用模型、不登录账户，也不部署服务。

## 构建与打开

使用已有的 Python 渲染依赖，无需前端框架或外部脚本：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-render.txt
.venv/bin/python tools/build_site.py
.venv/bin/python -m http.server 8767 --bind 127.0.0.1 --directory .build/site
```

打开 `http://127.0.0.1:8767/`。构建结果在 `.build/site`；也可直接打开其中的 `index.html`。搜索数据随 HTML 保存，没有搜索服务、外部追踪、登录或后台。JavaScript 关闭时，正文、内链、来源与完整目录仍可阅读；搜索与手机目录自动收起需要 JavaScript。

重新构建会清空并重建指定的 `.build` 子目录，避免被撤下的附件残留。不要把其他工作文件放进站点产物目录。构建不修改 Markdown、catalog、图示源或核验日期。

## 阅读与带走资料

长文页左侧是本页目录；手机上可以展开目录。来源编号通向[来源索引](../catalog/sources.json)中的记录；图示保留自己的横向滚动区，也提供全尺寸 SVG。表格与代码在局部滚动，不缩小整篇正文。

每篇可分发正文提供 Markdown 下载。Markdown 保持编辑源的相对链接，站点保留相应公开 Markdown、数据和图示的相对位置；下载单一文件后，相关附件需要另行带走。当前例子页明确列出可下载的公开附件，没有在线执行或部署按钮。

[2026-10-02 报告](../reports/2026-10-02.md)是有日期的历史资料快照。维护内容与历史报告分别显示 catalog 中的状态、核验日期与范围；继承 r3 的来源记录不代表本轮重新核验 Cloudflare 产品事实，更不代表账户或云端实测。

## 分发范围

`tools/build_site.py` 明确选择阅读内容和附件，不递归复制仓库目录。公开阅读范围包括手册、服务、用途、比较、报告、实施参考、例子、五张图及明确列出的维护文档与模板。私人工作笔记、handoff、原始输入、Git 状态、运行环境、历史 `dist` 和编辑过程记录不进入站点。

`current` 例子可以分发列出的源码及元数据。`superseded` 和 `archived` 保留状态说明与正文，不分发执行附件；`draft` 不加入默认阅读目录。`withdrawn` 入口只给撤下说明，停止分发原正文、Markdown 和执行附件，也不把其旧正文塞进搜索数据。

维护正文经 `tools/content.py` 的 `project_markdown` 读取：只有明确标记的事实区从 catalog 投影；历史报告保持冻结正文。内容更改仍从原有 Markdown、catalog、examples 或 Mermaid 进行。网站不是第二份编辑源，不能在 `.build/site` 中改事实或核验日期。图示来源与重建办法见[五张图](../diagrams/README.md)。

## 本地检查

```bash
.venv/bin/python -m unittest discover -s tests -p test_site.py -v
```

这些检查核对公开入口、生成内链、Markdown 下载、源码只读构建以及撤下后重建不留附件。它们不证明产品事实、云端可用或作者已接受视觉。

GitHub · [https://github.com/IndelibleVivi](https://github.com/IndelibleVivi)  
*made by Faye & Cove*
