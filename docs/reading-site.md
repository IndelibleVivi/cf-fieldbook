# 阅读站：使用、构建与部署

静态阅读站从同一份 Markdown、catalog、公开例子和图示构建。[在线阅读](https://indeliblevivi.github.io/cf-fieldbook/)。首页提供“从用途开始”“认识服务”“本期变化”三条入口；全部资料页可按目录阅读，也可以在浏览器内搜索标题与全文。

站点由 GitHub Pages 托管。搜索、目录和阅读交互在浏览器内运行，没有应用后端；构建不更新正文核验日期，不请求来源网页，也不调用模型或执行云端例子。

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

每篇可分发正文提供 Markdown 下载。Markdown 保持编辑源的相对链接，站点保留相应公开 Markdown、数据和图示的相对位置；下载单一文件后，相关附件需要另行带走。当前例子页明确列出可下载的公开附件，没有在线执行或部署按钮。构建目录同时包含代码许可全文及内容许可/范围说明；分发完整站点或例子时保留这些通知。

[2026-10-02 报告](../reports/2026-10-02.md)是有日期的历史资料快照。维护内容与历史报告分别显示 catalog 中的状态、核验日期与范围；[来源说明](provenance.md)记录继承资料的核验范围；网站更新不等于产品事实或云端行为重新核验。

## 分发范围

`tools/build_site.py` 明确选择阅读内容和附件，不递归复制仓库目录。公开阅读范围包括手册、服务、用途、比较、报告、实施参考、例子、五张图及明确列出的维护文档与模板。私人工作笔记、handoff、原始输入、Git 状态、运行环境、历史 `dist` 和编辑过程记录不进入站点。

`current` 例子可以分发列出的源码及元数据。`superseded` 和 `archived` 保留状态说明与正文，不分发执行附件；`draft` 不加入默认阅读目录。`withdrawn` 入口只给撤下说明，停止分发原正文、Markdown 和执行附件，也不把其旧正文塞进搜索数据。

维护正文经 `tools/content.py` 的 `project_markdown` 读取：只有明确标记的事实区从 catalog 投影；历史报告保持冻结正文。内容更改仍从原有 Markdown、catalog、examples 或 Mermaid 进行。网站不是第二份编辑源，不能在 `.build/site` 中改事实或核验日期。图示来源与重建办法见[五张图](../diagrams/README.md)。

## 本地检查

```bash
.venv/bin/python -m unittest discover -s tests -p test_site.py -v
```

这些检查核对公开入口、生成内链、Markdown 下载、只读构建、部署路径及撤下后重建不留附件。页面样式和交互改变时，还应实际检查桌面与手机阅读。

## 发布与回退

`.github/workflows/check.yml` 在 push 和 pull request 上执行离线检查、例子测试与网站构建。只有 `main` 的 push 或手动 workflow dispatch 会上传 `.build/site`，并由 `github-pages` environment 部署；pull request 不部署。

正式构建命令：

```bash
.venv/bin/python tools/build_site.py --base-url https://indeliblevivi.github.io/cf-fieldbook/
```

`--base-url` 用于 canonical 地址、站点地图和 404 导航。网站提供 `sitemap.xml`、`robots.txt`、原创 favicon 和 404 页面；本地预览可以省略该参数。`robots.txt` 只有部署在域名根目录时才是该域名的爬虫入口；GitHub 项目子路径中的同名文件不控制整个域名，页面仍各自声明索引状态。部署只上传显式选出的站点文件，不上传仓库根目录、`.build/editions` 或运行环境。

初次为 fork 启用时，在仓库 **Settings → Pages → Build and deployment** 中选择 **GitHub Actions**，并把 workflow 的 `--base-url` 改为该 fork 的实际网址。主分支变更触发构建；也可以在 Actions 中手动运行 **Checks and Pages**。使用自定义域名时同步该地址，DNS 和域名验证按托管平台说明配置。

发布后检查 Actions 中 build 与 deploy 均成功，再打开网站核对首页、深层文章、搜索和下载。失败时检查对应步骤日志：内容或测试失败先修复源文件；部署失败核对 Pages 设置与 environment 权限。失败的构建不会更新当前站点。

需要回退内容时，revert 引入问题的主分支提交并推送，让同一 workflow 重建部署；不要在生成的 HTML 中修补。撤下条目同样修改内容状态后部署，并确认旧正文和附件不再可访问；已下载副本和平台缓存可能仍需另行处理。

GitHub · [https://github.com/IndelibleVivi](https://github.com/IndelibleVivi)  
*made by Faye & Cove*
