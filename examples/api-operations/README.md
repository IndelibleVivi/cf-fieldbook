# 可靠的清单读取与结果未知的写：离线教学模型

这是一份**离线教学例子**，不是 Cloudflare 官方 SDK，也不是任何真实 API 的证明。它用固定的合成页、虚拟时间和内存里的合成流水，演示两件容易被低估的事：

1. **“取回一页”不等于“取回全部”。** 只有读到终止页（`next_cursor` 为空）才算完整清单；而 `next_cursor=None` 单独并不能证明完成——首页请求也可能失败，此时 `None` 只是未更改的初始游标。因此必须**同时**看 `status` 与 `next_cursor`。只成功一页、或首页为空但有续页游标，都不能提前收工；判定无法继续时同样是不完整。
2. **写请求已经生效、响应却丢失时，不能当作已知失败自动重放。** 此时结果未知，应先显式回读或核对，而不是再发一次。

模型是**用 Python 写的语言无关机制演示**。它没有 HTTP、没有传输层、没有凭据，也不验证真实游标、分页上限、限流或错误码。真实幂等与回读取决于具体操作与具体 API；本模型**不解决崩溃后的持久恢复**。

阅读站正文另见 [可恢复任务实践](../../use-cases/recoverable-jobs.md)、[API 维护](../../reference/api-maintenance.md)与[项目上下文](../../use-cases/project-context.md)。

## 问题

一次“列出自某游标开始的资源”的读取，会在什么条件下才算完整？当某次读或写失败时，哪一步的输出足以支撑一份如实的报告？

## 输入

全部输入都是合成的、写死的：

- `model.py` 里的 `Page` 固定页与 `CursorAPI` 固定游标表；`latency_ms` 是**虚拟毫秒**，只推进计数器，不做真实等待。循环场景由某页自身的 `next_cursor` 指回已见游标形成，没有额外的开关参数。
- `LedgerAPI` 是一个**内存**追加式合成流水，用来模拟“外部已经生效”的记录；`response_lost_below` 让最初若干次 `append` 生效但不返回响应。没有持久存储。
- 没有账号、区域、token 或真实资源 ID。操作身份是形如 `op-0001` 的演示字符串。

## 从仓库根目录运行

```bash
python3 examples/api-operations/demo.py
python3 -m unittest discover -s tests -p 'test_api_operations.py' -v
```

只需要 Python 3.11+ 标准库。不联网、不安装、不调用任何服务。

## 期望输出（实际打印，来自本次实现）

演示按 10 段打印（含 4b），关键行如下（节选）：

```
=== 1. 所有页被收集：一页成功不等于完整清单 ===
三页收集: status='complete' item_count=3, pages_read=3, attempted_pages=3, next_cursor=None, error=None

=== 2. 跨页请求与重试共享一个有界总截止时间（虚拟时间，无 sleep） ===
第二页会超过 500ms 截止: status='incomplete' pages_read=1, attempted_pages=2, item_count=1,
  virtual_elapsed_ms=500, failing_cursor='c1', next_cursor='c1',
  error="transient read failure at cursor 'c1': synthetic timeout: cursor 'c1' needs 600ms but only 100ms of budget remain"

=== 3. 可重试的读失败：同一截止时间内重试后成功 ===
一次性瞬时失败后重试成功: status='complete' attempted_pages=2, retries=1, pages_read=1,
  virtual_elapsed_ms=40, error=None

=== 4. 后续页失败：保留已收集项并报告不完整 ===
第二页瞬时失败且重试耗尽: status='incomplete' item_count=1, pages_read=1, attempted_pages=3,
  retries=1, failing_cursor='c1', next_cursor='c1',
  error="transient read failure at cursor 'c1': synthetic timeout (no retries left: max_retries_per_page=1)"

=== 4b. 重试耗尽总截止时间：真正发生的重试才计入 ===
重试在截止时间内逐步耗尽: status='incomplete' pages_read=1, attempted_pages=4, retries=2,
  virtual_elapsed_ms=120, failing_cursor='c1', next_cursor='c1',
  error="transient read failure at cursor 'c1': synthetic timeout: cursor 'c1' needs 40ms but only 30ms of budget remain"

=== 5. 空首页 + next cursor：不能提前停止 ===
空首页不是终止: status='complete' item_count=1, pages_read=2, next_cursor=None, error=None

=== 6. 永久错误：不重试 ===
永久错误停止收集: status='incomplete' retries=0, pages_read=1, attempted_pages=2, next_cursor='c1',
  failing_cursor='c1', error="permanent read failure at cursor 'c1': synthetic 403 forbidden"

=== 7. 损坏/循环 cursor：有界，不会无限收集 ===
重复 cursor 被拒绝: status='incomplete' pages_read=2, attempted_pages=2, item_count=2,
  next_cursor='loop', error="repeated cursor 'loop': refusing to loop"

=== 8. 已生效但响应丢失的写：报告 uncertain，不自动重放 ===
写入尝试: status='uncertain' attempts=1, responded=False,
  error='synthetic response lost after effect recorded'
  合成流水条数（外部已经生效）：1
回读结果: status='resolved_applied' operation_id='op-0001', ledger_matches=1, resolved=True, resent=False

=== 9. 新客户端凭内存合成流水重建状态（仍不重发） ===
新客户端回读: status='resolved_applied' operation_id='op-0002', ledger_matches=1, resolved=True, resent=False
```

### 报告字段怎么读

`collect_inventory` 返回一个普通字典，供 agent 如实转述。请求计数按**本次操作**从传输日志的增量统计，因此同一个 `CursorAPI` 复用做第二次收集时不会带上第一次的请求：

| 字段 | 含义 |
|---|---|
| `status` | `complete` 只表示读到了终止页；`incomplete` 表示还没读完。它与 `next_cursor` 一起读：`status='complete'` 且 `next_cursor is None` 才是完成 |
| `items` / `item_count` | 已经收集到的条目；不完整时**保留**已完成的部分 |
| `pages_read` | 成功读取的页数 |
| `attempted_pages` | 本次操作实际发到传输层的请求数，**含最后一次失败的请求** |
| `retries` | 实际发到传输层的重试次数；被截止时间挡下、未发出的重试不计入 |
| `last_cursor` | 最后处理到的游标位置 |
| `failing_cursor` | 失败发生时正在请求的游标；完成时为 `None` |
| `next_cursor` | 未读完时下一个应读取的位置；`None` 表示没有续页 |
| `error` | 停止原因的文本；完整时为 `None`（即使中途重试过也清空） |
| `virtual_elapsed_ms` | 虚拟耗时；`deadline_ms` 是本次操作的总预算 |
| `api_calls` | 等同本次操作的 `attempted_pages`，便于直接核对 |

`perform_write` / `resolve_uncertain` / `recover_after_crash` 返回 `status`、稳定的 `operation_id`、`attempts`、`ledger_matches`、`resent`，以及回读的 `resolved` 与 `intended` / `observed`。

## 失败怎么解释

- **`status='incomplete'`**：不要当成“清单为空”或“读取完成”。用 `items` 里的已完成部分、`next_cursor` 的续读位置、`attempted_pages` / `retries` 的数量和 `error` 文本说明卡在哪里。agent 报告必须保留这些字段，而不是只写“失败”。
- **`error` 含 `permanent`**：永久错误（如被拒、not-found）不会重试，`retries` 应为 0，但该次失败请求仍计入 `attempted_pages`。继续重试这类错误没有意义。
- **`error` 含 `transient` 且 `retries` 达到上限**：可重试错误已经用完本页的预算，仍未成功。同一总截止时间内允许先重试；这里刻意限制每页重试次数，避免无休止重试。
- **`error` 含 `deadline` 或 `synthetic timeout`**：总截止时间耗尽。截止时间**跨页请求与重试共享**，所以慢页或连续重试会挤占后续预算。报告保留的是**最后一次真实错误**，不会用“即将重试”的措辞掩盖一次超时。
- **`error` 含 `repeated cursor` 或 `page limit`**：游标循环或页数上限触发。这是防止损坏或重复游标制造“无限清单”的边界；不是服务器错误，而是客户端主动停止。
- **写返回 `status='uncertain'`**：**不要**自动重发。先用 `resolve_uncertain` / `recover_after_crash` 回读：
  - 恰好一条记录、且 `key`/`value` 与预期一致 → `resolved_applied`（`resolved=True`、`resent=False`）。
  - 没有记录 → `not_observed`（仍**未解决**）。缺少记录**不是**“重放安全”的证明，必须留待人工或其他核对。
  - 同一 `operation_id` 有多条记录，或记录内容与预期不符 → `conflict`（仍**未解决**），并给出 `reason`、`intended` 与 `observed`。

## 来源与证据范围

- 这是**本地合成模拟**。通过 `python3 -m unittest ... test_api_operations.py` 得到的结论，只说明本模型在合成输入与虚拟时间下的行为。
- **没有**运行 Cloudflare 或任何真实 API；**没有**验证真实分页游标、错误码、限流、响应 schema、权限、费用或平台可用性。
- 关于 Cloudflare Go v7.12.0 等真实 SDK 的默认行为，由维护者在正文中另行说明，不以本模型为依据。
- 第 9 段只是**同一进程里换一个新的内存客户端、复用同一个内存合成流水**，用来演示“凭外部记录重建状态、不重发”。它**不是**真实进程崩溃测试，也**不是**持久存储验证：流水对象本身只在内存中。本模型**不解决**崩溃后的持久恢复：它没有在发送前记录意图。真实持久恢复仍需 outbox、稳定 idempotency key 或人工核对；`uncertain` 的处置也不能替代业务补偿。
- 记录在案的语义与边界见[恢复实践](../../use-cases/recoverable-jobs.md)；术语如 [idempotency / 幂等](../../docs/glossary.md#idempotency--幂等)与 [uncertain / 结果未知](../../docs/glossary.md#uncertain--结果未知)另有词条。

## 清理

演示只使用内存中的合成页与合成流水，不写文件、不建数据库、不创建云资源。运行结束后**无需清理**；退出 Python 进程即释放全部状态。

## 还能怎样改

- 把固定页换成从本地 JSON 读取的合成页，观察同样的失败族。
- 为写路径加入“发送前先记录意图”，把本模型升级为可讨论 outbox 的形态，并单独记录仍未解决的部分。
- 对照真实 SDK 的分页与重试默认值（由维护者在正文中给出）讨论差异；差异属于来源核对，不并入本地结果。

*made by Faye & Cove*
