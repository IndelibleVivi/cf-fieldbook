---
id: usecase.recoverable-jobs
reviewed_on: null
services: []
related: [example.job-state]
evidence: local-simulation
---

# 一项任务被登记后，worker 却退出了

这轮练习的产出是一份能解释恢复条件的观察记录：区分登记与完成，指出旧执行者的迟到结果为什么被拒绝，并说明未知外部结果为什么不能自动重放。先读下面的失败因果，再[体验合成模拟](https://indeliblevivi.github.io/cf-fieldbook/examples/job-state/demo.html)，最后用[离线例子](../examples/job-state/README.md)取得模型的实际输出。

## 当时为什么需要它

假设一项合成的本地文档转换任务已经写入任务表。worker 刚领取就退出，结果尚未保存；随后同一消息再次到达。如果系统只保存“这个 ID 见过”，第二次会被当成重复而跳过，工作就永远没有完成。反过来，若外部动作成功后才登记“见过”，响应丢失会使下一次投递重复执行。**被登记 ≠ 完成**，去重标记不能替代可恢复的状态。

这里关注的是失败因果，而非真实账号或生产流水。任务 ID、时间和外部流水均为合成输入；没有从私人运行环境移植配置。

## 选择与取舍

将登记、领取和完成分开记录。新任务是 `pending`；原子领取后为 `running`，带一个到期[租约](../docs/glossary.md#lease--租约)与递增 [generation / 执行代次](../docs/glossary.md#generation--执行代次)。worker 退出后，租约到期允许另一个 worker 取得新 generation。旧 worker 即使后来返回，其旧 generation 也无法提交覆盖新一轮结果。已知安全的失败可标记 `retryable`；已经核实成功才标记 `done`。

租约到期并不说明原 worker 已停止，更不说明它没有调用外部服务。付款、发布、删除或通知等动作发生过却没有可靠响应时，应记录 [uncertain / 结果未知](../docs/glossary.md#uncertain--结果未知)并停止自动领取；依据外部记录、稳定 [idempotency / 幂等](../docs/glossary.md#idempotency--幂等) key 或人工核对判断下一步。取消只能阻止后续本地提交，不能撤销外部动作。状态含义和跨数据库、队列与服务的缺口见[实施参考第 8 章](../reference/implementation.md#08--自动化接收成功执行成功结果可见各有自己的状态)。

> **想一想：外部动作超时后，把任务标为 retryable 并重新领取，能否证明不会重复？**
>
> **答案：不能。** timeout 只说明没有取得可靠响应。先查动作是否发生、是否有稳定幂等约定；证据不足时保留 uncertain，不能把未知结果当作已知安全的失败。

## 可公开复现的部分

在仓库根目录运行 `python3 examples/job-state/demo.py`。演示先打印 `('pending', 0)`，然后观察 worker A 在 `t=0` 领取、退出；`t=10` 租约仍有效，无法再次领取；`t=30` worker B 领取到 generation 2。随后旧 generation 的 `finish` 为 `False`，新 generation 的 `finish` 为 `True`，完成后的重复领取为 `None`。这些值来自实际 SQLite 状态转移，而不是预写的成功报告。

第二段用合成外部流水制造“动作已记入、响应丢失”的分叉。worker 在仍可提交时标记 `uncertain`，重启后的领取返回 `None`；最后模拟人工核对，读取合成流水得到一次动作，而任务状态仍待处置。运行步骤、测试命令和模型文件见[示例说明](../examples/job-state/README.md)。离线资源的[生命周期图](../assets/diagrams/example-lifecycle.svg)说明这轮检查与未来云端实验的分界。

若由 agent 运行，可直接使用[恢复任务单](../templates/job-recovery-task.md)：它限定合成输入、离线命令、应观察到的返回值与失败后的停止条件。网页模拟帮助观察，命令输出来自实际模型；两者都不替代云端交付验收。

## 检查到哪里

本例只验证本地 SQLite 在合成时间与输入下的状态变化，以及跨连接重开后的持久结果。它没有运行 Cloudflare Queues、D1、Workflows 或真实外部服务；也没有验证队列投递、outbox、重试耗尽、DLQ、账单或平台可用性。模型未实现外部动作前的意图记录：如果 worker 在发送请求后、写入 `uncertain` 前崩溃，它仍可能被租约恢复逻辑重新领取。因此，未经外部幂等或核对机制保护的动作不能套用自动恢复段。离线通过不等于生产恢复演练完成。

## 使用条件、成本与退出

这个模型适合解释可重做的本地工作如何从中断恢复，也适合用来审查正式设计是否把未知结果留在可检查的位置。正式接入队列前，需要确定任务身份、原子登记与 outbox、外部幂等边界、退避与预算、未知结果核对、DLQ 和运营责任；不能把本例当成完整 distributed queue 实现。

运行不联网，也不创建云资源；演示使用临时数据库并在退出时清除。检查结束无需云端清理，费用为本地执行资源。若要把它迁到云端，那是独立实验：先给预算、资源、授权和清理方案，再记录真实观察。迁移后的行为需要在目标环境单独验证。

## 还能怎样改

若任务会产生不可逆外部效果，首先决定外部服务是否支持稳定 idempotency key 与结果查询。若二者都没有，恢复策略需要人工核对或明确的业务补偿，不能仅增大租约或重试次数。若只处理可重做本地转换，则可在正式实现中再加入退避、尝试上限与监控积压；本例刻意只保留解释故障所需的状态转移。

*made by Faye & Cove*
