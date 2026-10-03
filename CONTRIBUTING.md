# 贡献与维护

先读 [README](README.md) 找到要改的内容；涉及项目边界看 [SPEC](SPEC.md)，涉及证据、时效与退役看 [生命周期](docs/lifecycle.md)。本仓库的公共内容以中文为主，代码标识、命令、产品名保留原文。

## 本地环境

Python 3.11+ 用于维护与出版，Node.js 20+ 用于 health Worker 和阅读交互的离线测试。创建项目内虚拟环境，避免修改系统 Python：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-render.txt -r requirements-design.txt
```

PDF 渲染还需要系统 Pango 和合适的中文字体；字体仅从本机读取，不随仓库分发。只跑基础离线检查时无需 PDF 或浏览器依赖。

macOS 已安装 Homebrew Pango/GLib、却遇到 `cannot load library libgobject-2.0-0` 时，在出版命令前设置本机实际的库目录，例如 `DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib"`。先确认目录确有相应 dylib；这是 [WeasyPrint 官方的缺失库排查路径](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#missing-library)，不是需要再安装一套 Python。

## 修改应该落在哪里

正文解释归各自 Markdown；来源登记归 `catalog/sources.json`；决策模型路线与价格归 `catalog/decision-routes.json`；内容关系归 `catalog/entries.json`。请求外壳、任务状态等行为改 `examples/` 源码。图形结构改 `diagrams/src/*.mmd`，导出方法见 [图示说明](diagrams/README.md)。

作品编排改 `catalog/publications.json`；章节身份用正文的稳定 `chapter` 标记，改标题、插章或重排不要改掉已发布的锚点。Observability 费用数值改 `catalog/observability-pricing.json`，未来计费日期归 `catalog/launches.json`；`tools/content.py` 根据 source_cutoff 或明确 as-of 生成对应时间的说明。报告新增为独立条目，历史报告不参与同步。资料架例子改三份 `materials/` 原件后，运行 `python3 examples/reading-shelf/build.py` 重建页面。

先查一项变更影响哪里，再判断哪些候选真的需要修改：

```sh
python3 tools/fieldbook.py impact data.decision-routes
python3 tools/fieldbook.py due --as-of 2026-11-01
```

`related` 是相关阅读；不驱动重写。旧报告只进入历史核对候选，后来的改价不自动成为旧报告的错误。

## 提交前检查

```sh
python3 tools/fieldbook.py check
python3 tools/check.py
python3 tools/content.py check
.venv/bin/python -m unittest discover -s tests -v
node --test examples/health-worker/worker.test.mjs
node --test tests/*.test.cjs
```

这些检查默认不登录、不调用模型 API、不创建云资源。搜索回归使用实际生成的小节索引，构建后运行 `node --test tests/*.test.cjs`；页面变化后看桌面与手机真实渲染、真实问法跳转、释义的 Escape／焦点返回和无 JavaScript 阅读。恢复演示还要验证场景切换、时间、播放与重置。图示变化后查看 SVG；出版变更按 [出版流程](docs/publication.md) 检查冻结版次。

词条定义只改 `docs/glossary.md` 的对应首段，网页与冻结版次自行读取。恢复演示数据由 `tools/recovery_demo.py` 调用现有 `Jobs` 模型生成；不要在 JavaScript 或说明文字里另写一份状态判断。读者可以直接使用[离线恢复工单](templates/job-recovery-task.md)。入口路线与任务状态的手机图由 `python3 tools/figures.py` 同源生成，改后同时复看横版与窄版。

## 提交内容与证据

新增实践从可公开的失败因果开始，重新构造合成输入；不要把私人生产目录复制过来再删账号。说明实际运行的命令、观察结果和没有证明的部分。源码测试、来源核验、云端实测分别记录。修改措辞或重新排版不能刷新产品事实核验日期。

提交前检查完整 diff 与 staged files。私人记录、原始聊天、账号配置、凭据、临时 QA 文件、依赖缓存不进 Git。开发产物留在被忽略的 `.build/`；继承的 r3 出版物在 `dist/` 固定保留，仅用于历史引用。新内容不得覆盖它们。

贡献时只提交你有权提供的材料；除非另有明确约定，对相应材料的贡献按 [许可与权利范围](LICENSE-STATUS.md) 中已有的条款提供，不表示转让著作权。新引入的第三方材料须保留适用许可与来源，不得套用项目默认许可覆盖。合入主分支后，现有 workflow 会更新静态阅读站；新增远端、域名、云端实验或收费操作需要独立授权。

站点构建、部署失败处理与回退见[阅读站运行说明](docs/reading-site.md)。
