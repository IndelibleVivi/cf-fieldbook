# architecture-1 · 本地核查记录

> 继承的历史核查记录。下文工具、版本与完成状态只描述 architecture-1 输入包；当前机制见 [当前状态](../docs/current-state.md) 与 [贡献说明](../CONTRIBUTING.md)。

日期：2026-10-02。对象是本地候选目录 `cf-fieldbook`，不是已发布的远端仓库。本记录只支持下列明确观察。

## 本轮实际执行

| 检查 | 结果 | 覆盖范围 |
|---|---|---|
| `python3 tools/fieldbook.py check` | 通过 | 内容 ID、单一源路径、依赖闭包约束、日期范围描述、图示配对、三个例子元数据、设计资料的本地链接 |
| `python3 tools/check.py` | 通过 | r3 原有来源标记、日期、链接、出版标记与示例一致性检查 |
| `python3 -m unittest discover -s tests -v` | 42 项通过 | 含原有离线例子，以及新增的依赖/相关区别、历史终止传播、失效日期、越界路径、图示漂移、只读查询与渲染源不回写 |
| `node --test examples/health-worker/worker.test.mjs` | 6 项通过 | health Worker 本地输入与响应合同 |
| 实际 Mermaid render + `--check` | 五张图通过 | Mermaid 11.12.2；本次相同浏览器与字体环境中二次渲染字节一致 |
| `python3 tools/build_design_reader.py --check` | 通过 | 架构 HTML/MD 与指定源文和 SVG 一致 |
| 变更影响查询 | 通过 | 决策路线变化触发当前复核与历史勘误候选；related-only 不成为依赖更新 |
| 到期查询 | 通过 | 以显式的 2026-11-01 为查询时间；不重写核验日期 |

## 图示与阅读检查

五张 SVG 均由 Mermaid 源生成，包含文本、标题、描述与源摘要，不含位图、脚本或 foreignObject。词级 tspan 在不改变同样式文本、行坐标、节点和边的前提下规范化，以便 SVG 打印引擎正确排字。最终图已按完整大小与整组布局查看。

架构阅读页在 Chromium 的 1280、768、390 像素视口检查。各视口文档宽度没有越界；所有内部目录锚点存在；五张图齐全；结尾签名只出现一次；没有外部脚本、字体或图像请求。代码、宽表和宽图在自身容器中滚动，不靠缩小字号塞进手机宽度。这个检查不替代完整的屏幕阅读器与跨浏览器验收。

本次实际引擎来自预装 Gradio 的 Mermaid 11.12.2 bundle；渲染脚本使用本地路由供应模块，不联网。普通 npm 模块入口与安装办法已提供，但没有联网完成 npm 安装与 lockfile 验收。没有将 Gradio、Mermaid 库本体或字体文件打进本包。跨平台字体差异仍需要复看几何。

## 未发生的事情

没有执行 Cloudflare 资源变更、真实模型调用、真实云端例子或 GitHub 发布。没有重新核验 r3 的 Cloudflare 产品事实，没有重做原有 PDF。edition lock、字段级事实迁移、可选官网、自动源差异监测和受控云端 runner 仍是设计目标，不是被这次测试证明已经实现的能力。

原 r3 的 `dist/` 出版物逐字节保留；完整来源与输入关系见 `input-provenance.json`。新图和阅读页是仓库设计的可读表示，不冒充旧出版物的视觉定稿。
