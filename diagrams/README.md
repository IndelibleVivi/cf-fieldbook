# 五张图，五个问题

这些是同一份设计的分视图，不是截图、图片生成或互不相干的手绘示意。每张图由本目录 `.mmd` 通过 Mermaid 渲染，正文中另有等价说明。候选架构不等于所有目标机制已经实现。

| 图 | 看什么 | 可编辑源 | 阅读图 |
|---|---|---|---|
| 架构 | 材料、编辑源、检查与输出 | [Mermaid](src/architecture.mmd) | [SVG](../assets/diagrams/architecture.svg) |
| 更新影响 | 依赖、相关、历史勘误 | [Mermaid](src/change-impact.mmd) | [SVG](../assets/diagrams/change-impact.svg) |
| 内容生命周期 | 修订、取代、归档、撤下 | [Mermaid](src/content-lifecycle.mmd) | [SVG](../assets/diagrams/content-lifecycle.svg) |
| 出版 | 只读构建、版次与勘误 | [Mermaid](src/publication.mmd) | [SVG](../assets/diagrams/publication.svg) |
| 示例执行 | 离线默认、云端授权、清理 | [Mermaid](src/example-lifecycle.mmd) | [SVG](../assets/diagrams/example-lifecycle.svg) |

青色边框表示编辑对象或阅读输出，橙色表示核查/判断位置，浅灰表示外部材料或历史路径。所有状态仍有文字；虚线表示旁路或辅助关系，含义由边上的标签决定。图不使用产品商标、猫脸节点或背景纹样。

## 重建

当前渲染引擎由 `package.json` 精确指定为 Mermaid **11.17.2**，完整依赖树锁在 `package-lock.json`。本地 Chromium 运行 Mermaid 的 render API。实际引擎、模块依赖、源、配置与 SVG 摘要保存在 [manifest](../assets/diagrams/manifest.json)，用于检查源与产物是否配套。

```bash
npm ci --ignore-scripts
.venv/bin/python -m pip install -r requirements-design.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python tools/render_diagrams.py
.venv/bin/python tools/render_diagrams.py --check
```

依赖和浏览器安装会访问软件源；渲染只读本地模块。已有兼容 Playwright Chromium 时不必重新下载，可通过 `--browser` 指定。当前只维护 npm 锁定依赖路径。更换 Mermaid 版本先改 package/lock，再重新渲染、检查配套并看图，不只刷新摘要。

导出做两项统一兼容处理：添加真正的白底矩形；把 Mermaid 生成的同样式词级 tspan 合成单个行级 tspan，避免某些 SVG 打印引擎错误分配词位置。文字、行坐标、节点、边来自 Mermaid；未手改图意或移动节点。

跨字体/浏览器环境可能产生几何差异。本包的 `--check` 比较当前环境的重新渲染结果，不宣称跨平台像素完全相同。任何引擎升级或版面变化都要看实际图。

## 阅读尺度

架构图为横向概览；另外几张以纵向流程为主。网页为宽图保留局部横向滚动，旁边提供完整解释；打印时按实际图宽分配页面。不要把五张拼成一页后再要求读者放大猜文字。
