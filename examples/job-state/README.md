# 任务失败与恢复：离线教学模型

一次消息被接收，只能说明任务已登记，不能说明工作完成。这个 SQLite 小模型让读者看见 worker 中断、租约到期、重新领取与迟到结果的状态变化。它使用合成输入、注入的整数时钟和临时数据库；没有网络、凭据或真实外部动作。

在仓库根目录运行：

```bash
python3 examples/job-state/demo.py
python3 -m unittest discover -s tests -p 'test_job_recovery.py' -v
python3 -m unittest discover -s tests -p 'test_examples.py' -v
```

演示直接打印模型返回值。开头的 `('pending', 0)` 表示**被登记 ≠ 完成**；worker A 在 generation 1 领取后退出，`t=10` 仍不能并发领取。`t=30` 租约到期后，worker B 拿到 generation 2。A 的迟到 `finish` 返回 `False`，B 的完成返回 `True`。之后重复投递也拿不到已完成任务。

第二个合成任务模拟外部服务已记录动作、响应却丢失。worker 只知道发生了 timeout，因此在租约有效时写入 `uncertain`。重启后即使到了 `t=500`，`claim` 仍返回 `None`。演示最后模拟人工核对：读取**合成外部流水**，看到一次动作；数据库仍保持 `uncertain`，因为这个教学模型没有人工裁决或补偿接口。真实系统须依据外部记录或稳定 idempotency key 核对，再决定后续状态与动作。

核心机制在 [model.py](model.py)，完整因果与适用判断见[可恢复任务实践](../../use-cases/recoverable-jobs.md)。[手册第 8 章](../../reference/implementation.md#08--自动化接收成功执行成功结果可见各有自己的状态)说明队列、outbox 和外部副作用之间的边界。

这里的自动重新领取只适用于本地可重做的工作，或已经在外部建立幂等边界的工作。若 worker 在发出外部请求后、写入 `uncertain` 前崩溃，单靠此表中的租约会允许重新领取；**不能**把这一模型直接用作付款、发布、删除或通知的自动重试器。`generation` 只防旧 worker 改写本地状态，不能撤回已发生的外部动作。模型也没有队列 consumer、D1 适配、outbox、退避与重试预算、DLQ 或完整人工核对流程；本地通过不构成云端实测。

演示结束时临时数据库自动删除；没有云资源需要清理。若把模型改成持久数据库路径，测试数据与该文件由运行者按自己的本地保留策略处理。

*made by Faye & Cove*
