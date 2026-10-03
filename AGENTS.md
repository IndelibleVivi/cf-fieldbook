# Working in CF Fieldbook

CF Fieldbook 是独立的参考资料与离线例子仓库。先读 [README](README.md)；产品边界见 [SPEC](SPEC.md)，内容状态见 [生命周期](docs/lifecycle.md)，构建与发布见 [出版](docs/publication.md)和[阅读站](docs/reading-site.md)。

## Canonical paths

- Markdown 拥有正文；`catalog/` 拥有精确跨页数据、来源和内容索引；`examples/` 拥有可执行行为。
- `catalog/publications.json` 拥有三部作品的编排与阅读入口，`tools/publications.py` 共用读取。Markdown 的 `chapter` 标记是稳定身份，章节编号只表示顺序；改名或重排须保持旧网页锚点。报告身份来自所选条目与正文日期，不写死 renderer 日期。
- `practice/` 拥有匿名重构的历史案例，catalog 的 `practice` 条目把它们纳入阅读、搜索与撤下规则。历史观察与编辑时查阅的官方机制分别注明；私人原始证据、项目身份与实际配置留在仓库外，不记为新的云端执行。
- `tools/content.py sync` 显式更新维护事实块，`check` 检测漂移。历史报告不读入当前事实。
- Observability 费用取 `catalog/observability-pricing.json`，生效日期归 `catalog/launches.json`；投影使用显式 as-of 或正文 source_cutoff，不用构建当天刷新事实。
- `tools/build_site.py` 是唯一阅读站构建入口，只分发显式 allowlist。阅读呈现的注释过滤与单次署名不回写 Markdown；代码中的注释示例和权利声明须保留，不通过开启任意 HTML 来处理维护标记。
- `docs/glossary.md` 的词条首段拥有短释义；站点从它生成就地解释，冻结出版物嵌入当版所引用的定义。术语链接保留普通 Markdown 锚点。
- `styles/search.js` 拥有本地问题别名与排序；索引来自实际正文小节。搜索目标必须有答案，不能用别名掩盖缺失内容。
- `examples/job-state/model.py` 拥有恢复规则；`tools/recovery_demo.py` 执行模型生成合成场景，`styles/recovery.js` 只控制场景与播放。演示只随 current 例子分发，不增加云端执行。
- `examples/reading-shelf/materials/` 拥有三份合成原件；`build.py` 生成 `index.html`，不另行编辑生成正文。静态例子不包含手册扩展设计中的权限、数据库或索引。
- `tools/editions.py freeze/build/check` 是三册出版入口，使用冻结输入内的 renderer；`.build/editions/` 是本地产物，`dist/` 是固定 r3 历史。
- `tools/share_images.py` 从作品编排、日期与原创 SVG 生成 `assets/share/` PNG；普通站点构建只复制。作品身份、截止日或母题变化须重建并复看分享卡。
- Mermaid 在 `diagrams/src/` 编辑，SVG 由工具生成；不要手改导出图。原创装饰在 `assets/motifs/`。
- 阅读概念图由 `tools/figures.py` 显式生成；入口与任务状态的横／窄布局共用语义，不单改一份导出。
- README 的 `assets/motifs/repository-banner.svg` 也由 `tools/figures.py` 生成，复用 `cat-sunrise.svg`；调整标题排布改生成函数，调整猫与日出改原母题。仅仓库 README 展示横幅，站点 HTML 投影省略，Markdown 下载保持原样。

## Change boundaries

改变条目前查询 `python3 tools/fieldbook.py impact <id>`；结果是候选范围，`related` 不传播。不要自动重写历史报告或刷新事实核验日期。来源审阅、代码测试和云端实测分别记录。

例子默认离线。新增云端执行、付费调用、外部资源或账户变更需要该任务的明确授权。网站只发布静态阅读文件，不运行例子。未经授权不改变许可、远端或既有部署配置。

公共例子使用合成输入；正文使用可公开来源与经过匿名重构的历史实践。凭据、私人原始日志、实际账号配置、内部讨论和工作接续不进入仓库或站点；`.gitignore` 不替代分发边界。原创代码与内容的许可划分以 [LICENSE-STATUS.md](LICENSE-STATUS.md) 为准。

## Verification and docs

```sh
python3 tools/fieldbook.py check
python3 tools/check.py
python3 tools/content.py check
.venv/bin/python -m unittest discover -s tests -v
node --test examples/health-worker/worker.test.mjs
node --test tests/*.test.cjs
```

页面改动检查桌面和移动端实际渲染、导航、真实问法搜索、释义焦点返回与下载；演示改动还检查场景切换、时间／步骤、播放／暂停／重置及无 JavaScript 出口。图示改动重建并复看。构建不能改变编辑源。提交前检查 intended diff 与 staged paths。

能力、命令或边界改变时更新 README 与相应指南；稳定维护合同改变时更新本文件；部署和出版事实更新 `docs/current-state.md` 与 CHANGELOG。内部工作接续留在 Git 外。
