# 从阅读版 r3 接续

此页帮助阅读过固定 r3 出版物的读者找到当前正文、代码与构建入口。初始来源与核验范围见[来源说明](provenance.md)。

## 文件与行为的去向

| 材料 | 当前处理 |
|---|---|
| reports | 原文与来源定义保留，后续事实同步不回写历史报告 |
| guides、comparisons、services | 叙述保留；决策模型的重复数据改由显式 fact blocks 共源 |
| catalog | 原路径保留；内容索引加入恢复任务用例及本地合成测试证据 |
| examples | 保留三个可运行机制；job-state 增加失败与恢复 demo、回归检查与限制说明 |
| reference/implementation | 保留稳定入口，供阅读站与例子引用 |
| 来源与修订 | 读者所需的核验范围集中于 docs/provenance.md，现行维护步骤归 docs/ |
| tools/render.py | canonical 三册 renderer；只读冻结输入，禁止默认覆盖 dist |
| tools/content.py、editions.py | 显式同步维护数据，固定版次输入并验证输出身份 |
| tools/build_site.py | 唯一阅读站构建入口，生成静态 HTML、目录和搜索索引 |
| dist | 原始三册 MD/HTML/PDF 保留；新本地候选在 .build/editions |
| assets/motifs | 首页插画、青猫与日出 SVG、云与边缘节点线稿；用途见内容设计 |
| docs 与 CONTRIBUTING | 当前机制、读者说明和维护操作；私人 handoff 不导入 |

## 现有边界

静态站、事实投影和本地版次冻结已经实现。字段级全库事实登记、来源自动监测、定时维护、云端例子适配器尚未实现。静态阅读站使用独立部署流程，见[阅读站](reading-site.md)。

结构检查不理解产品事实真假。新增测试证明本地机制，不替代云端实测。新 PDF 属于视觉候选，旧 r3 PDF 仍是继承作品；公开状态见 [当前状态](current-state.md)。
