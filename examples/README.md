# 公共例子

这些例子演示机制，不复制作者的生产部署。默认不联网、不带凭据；“运行通过”只指各例子列出的输入与检查。

| 例子 | 能看见什么 | 没有证明什么 |
|---|---|---|
| [health-worker](health-worker/README.md) | 最小路由、响应与错误路径 | 真实 Worker 部署、Access 策略或账户可用 |
| [job-state](job-state/README.md) · [失败与恢复实践](../use-cases/recoverable-jobs.md) | 任务中断、租约恢复、迟到拒绝和未知结果核对的离线过程 | 云队列端到端交付或外部副作用安全 |
| [decision-routing](decision-routing/README.md) | 决策请求外壳、路线与费用算术 | 模型判断正确、阈值可迁移、provider 独立 |

后续例子遵循 [生命周期](../docs/lifecycle.md)，用 [模板](../templates/practice-example.md) 保留问题、因果与退出，而不是只贴一份删掉名字的配置。

## 从理解到复现

以任务恢复为例，先读[失败与恢复用例](../use-cases/recoverable-jobs.md)，辨认“登记后退出”和“外部动作发生但响应丢失”为什么需要不同处置。再打开[交互教学模拟](https://indeliblevivi.github.io/cf-fieldbook/examples/job-state/demo.html)，切换合成情景并沿时间观察状态；它不连接云服务。

回到仓库根目录，用 Python 3.11+ 复现实际 SQLite 模型：

```bash
python3 examples/job-state/demo.py
python3 -m unittest discover -s tests -p 'test_job_recovery.py' -v
```

[模型说明](job-state/README.md)列出输出与未解决的崩溃窗口；[恢复任务单](../templates/job-recovery-task.md)可直接交给 agent，限定离线动作、失败证据和清理。遇到不熟悉的词，查[术语小词表](../docs/glossary.md)。完成这条路径后，应能解释哪些本地工作可重新领取，以及为什么 `uncertain` 必须先核对；它没有验证 Cloudflare 的队列交付、云资源或真实外部动作。
