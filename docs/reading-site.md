# 阅读站：使用、构建与部署

静态阅读站从同一份 Markdown、catalog、公开例子和图示构建。[在线阅读](https://indeliblevivi.github.io/cf-fieldbook/)。首页明确提供手册、Clef / Jev 专题、当前新发布观察三部作品入口，服务索引另列，以及三篇真实实践选读；全站导航可直接进入实践记录。全部资料页可按目录阅读，也可以在浏览器内搜索具体小节。

站点由 GitHub Pages 托管。搜索、目录、词义与合成场景回放在浏览器内运行，没有应用后端；构建不更新正文核验日期，不请求来源网页，也不调用模型服务或执行云端例子。任务恢复演示在构建时执行仓库的离线 SQLite 模型，将真实模型事件保存为静态 JSON；浏览器只回放这些记录。

## 构建与打开

使用已有的 Python 渲染依赖，无需前端框架或外部脚本：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-render.txt
.venv/bin/python tools/build_site.py
.venv/bin/python -m http.server 8767 --bind 127.0.0.1 --directory .build/site
```

打开 `http://127.0.0.1:8767/`。构建结果在 `.build/site`；也可直接打开其中的 `index.html`。搜索与词义数据随 HTML 保存，没有搜索服务、外部追踪、登录或后台。页首可以切换暖纸与冷白两种阅读主题，选择只保存在读者自己的浏览器里。JavaScript 关闭时，正文、内链、来源、完整目录、词表、理解题答案与演示的五条执行路径仍可阅读；搜索、就地词义弹窗、场景回放、手机目录自动收起与主题切换需要 JavaScript，无 JavaScript 时保持冷白主题。

重新构建会清空并重建指定的 `.build` 子目录，避免被撤下的附件残留。不要把其他工作文件放进站点产物目录。构建不修改 Markdown、catalog、图示源或核验日期。

## 阅读与带走资料

长文先展示独立题头，再进入正文；桌面左侧是本页目录，随滚动标示当前章节；手机上可以展开目录。标题、副题和版次分别排版；正文使用无衬线章节标题与小号章号，并保留适合连续阅读的行宽。题头母题随资料篇类变化：服务用边缘路径，比较用天平，用途用出发窗口，例子用任务循环，实施参考用台账，实践与带日期报告用记录页，其余用书页；文章结尾盖一枚日出篇尾小印。搜索按 h2/h3 小节索引，结果显示页名与小节名并跳到稳定锚点；空格分隔的多个词需要同时匹配。少量读者问法（如“任务重复”“断了怎么办”“Tunnel 外网访问”）映射到正文已有机制词并优先展示相关解释，额外词仍必须匹配。历史归档与已有替代的结果保留状态说明。

页脚“链接图例”解释站内阅读、词义、项目源码、外部来源与附件的不同标记。正文明确链接的术语可就地展开[词表](glossary.md)首段释义；Escape 或关闭按钮返回原链接焦点，按住 Command / Ctrl 等修饰键则保留浏览器正常打开链接的行为。理解题始终展示问题，答案可展开。核验范围可以展开，正文中会影响重试、权限或部署的提醒保持可见。

搜索支持网页上线、网站部署、R2 价格与产品名旁的中文问法；额外查询词仍需全部满足。同篇的相近结果收在一个可展开组内，作品查询优先整篇入口，普通问题优先当前解释，有日期或历史意图时再提升报告。恢复演示的事件说明在按钮上方，点击推进时与控制一起可见。

实践记录的官方机制链接放在相应段落旁；历史观察日期保留在各篇正文，不把案例的编辑日期当作重新上线验收。

来源编号通向[来源索引](../catalog/sources.json)中的记录；图示保留自己的横向滚动区，也提供全尺寸 SVG。访问路线与任务状态两张图在窄阅读列切换到纵版，并提供纵版 SVG 入口。表格与代码在局部滚动，不缩小整篇正文。

每篇可分发正文提供 Markdown 下载。Markdown 保持可分发内容的相对链接，站点保留相应公开 Markdown、数据和图示的相对位置；明确公开而未分发的工具或测试通向本项目 GitHub 源码，其他未分发文件只保留说明。下载单一文件后，相关附件需要另行带走。当前例子页明确列出可下载的公开附件。[任务恢复演示](https://indeliblevivi.github.io/cf-fieldbook/examples/job-state/demo.html)可以逐步观察中断、接管、迟到提交、响应丢失和未解决的崩溃窗口；没有云端执行或部署按钮。构建目录同时包含代码许可全文及内容许可/范围说明；分发完整站点或例子时保留这些通知。

[2026-10-02 报告](../reports/2026-10-02.md)是有日期的历史资料快照。维护内容与历史报告分别显示 catalog 中的状态、核验日期与范围；[来源说明](provenance.md)记录继承资料的核验范围；网站更新不等于产品事实或云端行为重新核验。

## 分享与版本回访

每篇文章有自己的 title、description、source_cutoff、canonical、Open Graph 与 Twitter metadata。三部作品使用独立的 1200 × 630 PNG 分享图，其余页面使用项目图；元数据仍表达各篇身份。图片由 `tools/share_images.py` 读取编排、源日期和原创 SVG 明确生成，普通网站构建只复制已审阅的 PNG，避免 CI 的字体差异。改变作品身份、日期或母题时，使用现有设计依赖重建并复看：

```bash
.venv/bin/python tools/share_images.py
```

需要时通过 `--browser <已安装的兼容 Chromium 可执行文件>` 选择现有浏览器；命令不安装浏览器、不请求远程资源、不分发字体。正式 base-url 构建才输出社交 metadata，本地预览保持 noindex。真实分享平台是否展示图片仍需该平台抓取验证，HTML metadata 检查不能代替它。

作品与版本入口为 `publications.html`，每册另有 `publications-<family>.html`；版本页显示该册相关修订、当前阅读与固定历史版。新版 PDF 仍是本地候选，站点没有自动发布 Release 或候选下载；出版程序见[出版](publication.md)。draft／withdrawn 的正文与章节不会通过版本页重新分发。

## 分发范围

`tools/build_site.py` 明确选择阅读内容和附件，不递归复制仓库目录。公开阅读范围包括手册、服务、用途、比较、报告、实施参考、匿名实践记录、例子、六张图及明确列出的维护文档与模板。私人工作笔记、handoff、原始输入、Git 状态、运行环境、历史 `dist` 和编辑过程记录不进入站点。

`current` 例子可以分发列出的源码及元数据。`superseded` 和 `archived` 保留状态说明与正文，不分发执行附件；`draft` 不加入默认阅读目录。`withdrawn` 入口只给撤下说明，停止分发原正文、Markdown 和执行附件，也不把其旧正文塞进搜索数据。

任务恢复演示、内嵌模型事件与专用 CSS/JavaScript 仅在 `example.job-state` 为 `current` 时生成。状态改变后重新构建会移除旧演示及数据，首页、目录、正文链接和站点地图同步停止提供演示入口。正文和词义不会自动给所有术语加链接，也不允许任意原始 HTML：理解题增强只识别一个 blockquote 内以粗体“想一想：”开头的问题和以粗体“答案：”开头的答案。

网页呈现只保留页脚一处署名，不重复正文开篇与结尾的独立署名；法律归属说明、作者元数据与 Markdown 下载保持完整。Markdown 注释不显示在正文或搜索摘要中，受控的 `figure:` 注释生成指定图示；行内代码、缩进代码和代码围栏中的注释示例仍按原文显示，不开启任意 HTML 渲染。

维护正文经 `tools/content.py` 的 `project_markdown` 读取：只有明确标记的事实区从 catalog 投影；历史报告保持冻结正文。内容更改仍从原有 Markdown、catalog、examples 或 Mermaid 进行。网站不是第二份编辑源，不能在 `.build/site` 中改事实或核验日期。图示来源与重建办法见[六张图](../diagrams/README.md)。

## 本地检查

```bash
.venv/bin/python -m unittest discover -s tests -p test_site.py -v
node --test tests/site-search.test.cjs
```

这些检查核对公开入口、小节锚点与真实问法排序、词表与理解题约定、生成内链、Markdown 下载、只读构建、维护注释与代码示例的区分、署名呈现、部署路径及状态改变后不留演示或附件。Node 行为检查使用实际生成的索引；可通过 `FIELDBOOK_SEARCH_INDEX` 指向已经构建的 `search-index.json`。页面样式和交互改变时，还应实际检查桌面与手机搜索跳转、键盘词义、无 JavaScript 阅读及局部滚动。

## 发布与回退

`.github/workflows/check.yml` 在 push 和 pull request 上执行离线检查、例子测试与网站构建。只有 `main` 的 push 或手动 workflow dispatch 会上传 `.build/site`，并由 `github-pages` environment 部署；pull request 不部署。

正式构建命令：

```bash
.venv/bin/python tools/build_site.py --base-url https://indeliblevivi.github.io/cf-fieldbook/
```

`--base-url` 用于 canonical 地址、站点地图和 404 导航。网站提供 `sitemap.xml`、`robots.txt`、原创 favicon 和 404 页面；本地预览可以省略该参数。`robots.txt` 只有部署在域名根目录时才是该域名的爬虫入口；GitHub 项目子路径中的同名文件不控制整个域名，页面仍各自声明索引状态。部署只上传显式选出的站点文件，不上传仓库根目录、`.build/editions` 或运行环境。

`tools/build_site.py` 的公共页面模板保留本项目 Search Console 的 `google-site-verification` meta。这是公开的所有权验证标记，不是访问凭据或 analytics 脚本；正式站点验证后也须保留。重排模板时检查生成首页的 `<head>` 仍包含标记；fork 或更换站点所有者时移除原标记，并在自己的 Search Console 获取新的验证值。对应 URL-prefix 为 `https://indeliblevivi.github.io/cf-fieldbook/`，sitemap 为该前缀下的 `sitemap.xml`；验证、提交与实际收录分别确认。

初次为 fork 启用时，在仓库 **Settings → Pages → Build and deployment** 中选择 **GitHub Actions**，并把 workflow 的 `--base-url` 改为该 fork 的实际网址。主分支变更触发构建；也可以在 Actions 中手动运行 **Checks and Pages**。使用自定义域名时同步该地址，DNS 和域名验证按托管平台说明配置。

发布后检查 Actions 中 build 与 deploy 均成功，再打开网站核对首页、深层文章、搜索和下载。失败时检查对应步骤日志：内容或测试失败先修复源文件；部署失败核对 Pages 设置与 environment 权限。失败的构建不会更新当前站点。

需要回退内容时，revert 引入问题的主分支提交并推送，让同一 workflow 重建部署；不要在生成的 HTML 中修补。撤下条目同样修改内容状态后部署，并确认旧正文和附件不再可访问；已下载副本和平台缓存可能仍需另行处理。

GitHub · [https://github.com/IndelibleVivi](https://github.com/IndelibleVivi)  
*made by Faye & Cove*
