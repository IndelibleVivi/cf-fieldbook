# 公共例子

这些例子演示机制，不复制作者的生产部署。默认不联网、不带凭据；“运行通过”只指各例子列出的输入与检查。

| 例子 | 能看见什么 | 没有证明什么 |
|---|---|---|
| [health-worker](health-worker/README.md) | 最小路由、响应与错误路径 | 真实 Worker 部署、Access 策略或账户可用 |
| [job-state](job-state/README.md) · [失败与恢复实践](../use-cases/recoverable-jobs.md) | 任务中断、租约恢复、迟到拒绝和未知结果核对的离线过程 | 云队列端到端交付或外部副作用安全 |
| [decision-routing](decision-routing/README.md) | 决策请求外壳、路线与费用算术 | 模型判断正确、阈值可迁移、provider 独立 |

后续例子遵循 [生命周期](../docs/lifecycle.md)，用 [模板](../templates/practice-example.md) 保留问题、因果与退出，而不是只贴一份删掉名字的配置。
