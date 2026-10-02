# Working in CF Fieldbook

CF Fieldbook 是独立的参考资料与离线例子仓库。先读 [README](README.md)；产品边界见 [SPEC](SPEC.md)，内容状态见 [生命周期](docs/lifecycle.md)，构建与发布见 [出版](docs/publication.md)和[阅读站](docs/reading-site.md)。

## Canonical paths

- Markdown 拥有正文；`catalog/` 拥有精确跨页数据、来源和内容索引；`examples/` 拥有可执行行为。
- `tools/content.py sync` 显式更新维护事实块，`check` 检测漂移。历史报告不读入当前事实。
- `tools/build_site.py` 是唯一阅读站构建入口，只分发显式 allowlist。
- `tools/editions.py freeze/build/check` 是三册出版入口，使用冻结输入内的 renderer；`.build/editions/` 是本地产物，`dist/` 是固定 r3 历史。
- Mermaid 在 `diagrams/src/` 编辑，SVG 由工具生成；不要手改导出图。原创装饰在 `assets/motifs/`。

## Change boundaries

改变条目前查询 `python3 tools/fieldbook.py impact <id>`；结果是候选范围，`related` 不传播。不要自动重写历史报告或刷新事实核验日期。来源审阅、代码测试和云端实测分别记录。

例子默认离线。新增云端执行、付费调用、外部资源或账户变更需要该任务的明确授权。网站只发布静态阅读文件，不运行例子。未经授权不改变许可、远端或既有部署配置。

公共资料使用合成输入与可公开来源。凭据、私人原始日志、实际账号配置、内部讨论和工作接续不进入仓库或站点；`.gitignore` 不替代分发边界。原创代码与内容的许可划分以 [LICENSE-STATUS.md](LICENSE-STATUS.md) 为准。

## Verification and docs

```sh
python3 tools/fieldbook.py check
python3 tools/check.py
python3 tools/content.py check
.venv/bin/python -m unittest discover -s tests -v
node --test examples/health-worker/worker.test.mjs
```

页面改动检查桌面和移动端实际渲染、导航、搜索与下载；图示改动重建并复看。构建不能改变编辑源。提交前检查 intended diff 与 staged paths。

能力、命令或边界改变时更新 README 与相应指南；稳定维护合同改变时更新本文件；部署和出版事实更新 `docs/current-state.md` 与 CHANGELOG。内部工作接续留在 Git 外。
