# 当前状态

2026-10-02 · [公共源码](https://github.com/IndelibleVivi/cf-fieldbook)，默认分支 `main`。

- 阅读站提供用途、服务与当期观察三条入口，包含产品索引、目录、全文搜索、Markdown 下载和公开例子附件。[CF Fieldbook 正式站](https://indeliblevivi.github.io/cf-fieldbook/) 已上线，使用 GitHub Pages 与 HTTPS。
- `Checks and Pages` 对提交运行离线检查，主分支通过后部署到 GitHub Pages。PR 只检查。构建与回退方法见[阅读站](reading-site.md)。
- 决策模型的路线、选择器、价格、上下文和成本估算由 catalog 与例子实现共源；其余解释由 Markdown 维护。
- 三个例子默认离线。任务恢复演示覆盖中断、租约接管、迟到完成与不确定结果；没有云端实测声明。
- edition freeze 固定输入与渲染代码，生成三册 Markdown / HTML / PDF。`dist/` 保留固定 r3 历史出版物；新版 edition 尚未作为 Release 分发。
- 五张 Mermaid 图由锁定依赖生成。当前引擎为 11.17.2，系统字体可能影响几何。
- 来源核验范围见[来源说明](provenance.md)。网站构建和例子测试不更新事实核验日期。
- 原创功能代码采用 SUL-1.0；原创内容采用 CC BY-NC-SA 4.0。第三方例外见[许可范围](../LICENSE-STATUS.md)。

当前未提供云端例子 runner、定时来源监测或用户账号系统。最新构建和部署结果见[GitHub Actions](https://github.com/IndelibleVivi/cf-fieldbook/actions)。
