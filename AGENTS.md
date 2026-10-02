# Working in CF Fieldbook

本仓库是面向人和 agent 的参考资料与例子，不是作者的生产环境。先读 README；改架构读 SPEC；改内容生命周期读 docs/lifecycle.md；做出版读 docs/publication.md；视觉读 docs/content-design.md。

正文在原有 Markdown；精确跨页数据在 catalog；算法/请求实现归 examples；Mermaid 归 diagrams/src。维护数据块由 tools/content.py sync 显式更新；三册出版唯一入口为 tools/editions.py freeze/build/check，冻结输入内的 renderer 是该版次的实现。阅读站唯一构建入口为 tools/build_site.py；不要恢复已退役的 design-reader 生成路径。不要给“机版”复制第二份结论，不手改导出的 SVG。

改变一项资料前查询 `python3 tools/fieldbook.py impact <id>`。这只是候选范围，related 不参与传播；历史报告只考虑勘误，不能自动回写。事实核验、代码测试、云端实测与作者接受分开记录。

新增实践先写脱敏因果再构造合成输入。私人原始日志、拓扑、真实账号与凭据不进入仓库；ignore 不构成安全边界。例子默认不联网；云端执行必须另有明确预算、目标、清理与授权。

常规验证：`python3 tools/fieldbook.py check`、`python3 tools/check.py`、`python3 tools/content.py check`、`.venv/bin/python -m unittest discover -s tests -v`、`node --test examples/health-worker/worker.test.mjs`。新候选仅在 .build/editions，dist 是固定 r3 历史。改图后重建并复看；构建不能改变编辑源与核验日期。

GitHub 账号以地址呈现；作者 Faye & Cove；文末签 made by Faye & Cove。当前许可为原创功能代码 SUL-1.0、原创正文/图形/出版物 CC BY-NC-SA 4.0；边界以 LICENSE-STATUS.md 为准。不得擅自改变许可、创建新的远端或公开部署；常规 commit/push 依用户授权执行，不把本地通过写成生产成功。

完成报告写实际变化、观察与未完成项，不输出伪造验收记录。可由源码查清的事情先查源码；需要作者判断的是美术接受、许可与发布范围。实现变化须同步 README、相应 docs/运行命令与 current-state；私人 continuity 留在 Git 外。
