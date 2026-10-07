"""Deterministic, offline walk-through of inventory reads and an uncertain write.

Run from the repository root:

    python3 examples/api-operations/demo.py

Everything here is synthetic: fixed pages, virtual time (no sleeps), and a local
effect ledger. Nothing touches the network.

Terminology used below: a *request* is one dispatch to the synthetic transport;
``attempted_pages`` counts requests, ``retries`` counts only retries that really
reached the transport, and the ledger lives only in memory (so nothing here is a
durable-storage or process-crash test).
"""
from __future__ import annotations

from model import CursorAPI, Effect, LedgerAPI, OperationClient, Page, collect_inventory


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def show(label: str, report: dict, *fields: str) -> None:
    detail = ", ".join(f"{name}={report[name]!r}" for name in fields)
    print(f"{label}: status={report['status']!r} {detail}")


def page(index: int, *, next_cursor: str | None, latency_ms: int = 10,
         outcome: str = "ok", message: str = "") -> Page:
    return Page(items=[{"id": f"item-{index}"}], next_cursor=next_cursor,
                outcome=outcome, message=message, latency_ms=latency_ms)


def main() -> None:
    # ------------------------------------------------------------------ #
    section("1. 所有页被收集：一页成功不等于完整清单")
    api = CursorAPI({
        None: page(1, next_cursor="c1"),
        "c1": page(2, next_cursor="c2"),
        "c2": page(3, next_cursor=None),
    })
    report = collect_inventory(api, deadline_ms=1000)
    show("三页收集", report, "item_count", "pages_read", "attempted_pages",
         "next_cursor", "error")
    print(f"  收集到的条目：{[item['id'] for item in report['items']]}")
    print("  终止条件是 next_cursor 为 None；只看第一页会漏掉后面的页。")

    # ------------------------------------------------------------------ #
    section("2. 跨页请求与重试共享一个有界总截止时间（虚拟时间，无 sleep）")
    api = CursorAPI({
        None: page(1, next_cursor="c1", latency_ms=400),
        "c1": page(2, next_cursor=None, latency_ms=600),
    })
    report = collect_inventory(api, deadline_ms=500)
    show("第二页会超过 500ms 截止", report, "pages_read", "attempted_pages",
         "item_count", "virtual_elapsed_ms", "failing_cursor", "next_cursor", "error")
    print("  第一页(400ms)之后仅剩 100ms；第二页请求已发出，但在剩余预算处超时，")
    print("  虚拟时钟停在 500ms。attempted_pages=2 含这次失败的请求；")
    print("  已收集的 item-1 被保留，报告 incomplete 并给出下一位置。")

    # ------------------------------------------------------------------ #
    section("3. 可重试的读失败：同一截止时间内重试后成功")
    api = CursorAPI({
        None: page(1, next_cursor=None, message="synthetic timeout", latency_ms=20),
    }, fail_plan={None: ["transient"]})
    report = collect_inventory(api, deadline_ms=1000, max_retries_per_page=2)
    show("一次性瞬时失败后重试成功", report, "attempted_pages", "retries",
         "pages_read", "virtual_elapsed_ms", "error")
    print("  一次失败 + 一次成功 = attempted_pages=2，retries=1，最终 complete。")

    # ------------------------------------------------------------------ #
    section("4. 后续页失败：保留已收集项并报告不完整")
    api = CursorAPI({
        None: page(1, next_cursor="c1", latency_ms=10),
        "c1": page(2, next_cursor="c2", latency_ms=10, outcome="transient",
                   message="synthetic timeout"),
    })
    report = collect_inventory(api, deadline_ms=1000, max_retries_per_page=1)
    show("第二页瞬时失败且重试耗尽", report, "item_count", "pages_read",
         "attempted_pages", "retries", "failing_cursor", "next_cursor", "error")
    print(f"  已收集：[{[item['id'] for item in report['items']]}]；未读完，故为 incomplete。")
    print("  实际发生 3 次请求（首页 + 失败 + 1 次重试），attempted_pages=3；")
    print("  retries=1，最终错误保留最后一次超时文本。")

    # ------------------------------------------------------------------ #
    section("4b. 重试耗尽总截止时间：真正发生的重试才计入")
    api = CursorAPI({
        None: page(1, next_cursor="c1", latency_ms=10),
        "c1": page(2, next_cursor=None, latency_ms=40,
                   message="synthetic timeout"),
    }, fail_plan={"c1": ["transient", "transient", "transient"]})
    report = collect_inventory(api, deadline_ms=120, max_retries_per_page=5)
    show("重试在截止时间内逐步耗尽", report, "pages_read", "attempted_pages",
         "retries", "virtual_elapsed_ms", "failing_cursor", "next_cursor", "error")
    print("  首页(10ms) + 每次失败(40ms)；预算在第二次重试后耗尽，")
    print("  没有发出更多请求，也没有把未发生的重试计入 retries。")

    # ------------------------------------------------------------------ #
    section("5. 空首页 + next cursor：不能提前停止")
    api = CursorAPI({
        None: Page(items=[], next_cursor="c1", latency_ms=10),
        "c1": Page(items=[{"id": "item-2"}], next_cursor=None, latency_ms=10),
    })
    report = collect_inventory(api, deadline_ms=1000)
    show("空首页不是终止", report, "item_count", "pages_read", "next_cursor", "error")

    # ------------------------------------------------------------------ #
    section("6. 永久错误：不重试")
    api = CursorAPI({
        None: page(1, next_cursor="c1", latency_ms=10),
        "c1": page(2, next_cursor=None, outcome="permanent",
                   message="synthetic 403 forbidden", latency_ms=10),
    })
    report = collect_inventory(api, deadline_ms=1000, max_retries_per_page=5)
    show("永久错误停止收集", report, "retries", "pages_read",
         "attempted_pages", "failing_cursor", "next_cursor", "error")
    print("  首页 + 1 次永久失败请求 = attempted_pages=2，retries=0。")

    # ------------------------------------------------------------------ #
    section("7. 损坏/循环 cursor：有界，不会无限收集")
    api = CursorAPI({
        None: Page(items=[{"id": "item-1"}], next_cursor="loop", latency_ms=1),
        "loop": Page(items=[{"id": "item-loop"}], next_cursor="loop", latency_ms=1),
    })
    report = collect_inventory(api, deadline_ms=100_000, max_pages=50)
    show("重复 cursor 被拒绝", report, "pages_read", "attempted_pages",
         "item_count", "next_cursor", "error")
    print("  循环由页自身的 next_cursor 指回已见游标形成，收集器主动停止。")

    # ------------------------------------------------------------------ #
    section("8. 已生效但响应丢失的写：报告 uncertain，不自动重放")
    ledger = LedgerAPI(response_lost_below=1)  # 首次 append 生效但响应丢失
    client = OperationClient(ledger, operation_id="op-0001")
    effect = Effect(key="synthetic/settings.enabled", value=True)
    attempt = client.perform_write(effect)
    show("写入尝试", attempt, "attempts", "responded", "error")
    print(f"  合成流水条数（外部已经生效）：{len(ledger.entries())}")
    print("  没有自动重复动作：attempts 仍为 1。")

    print("\n  显式回读以解决 uncertain：")
    resolution = client.resolve_uncertain(effect)
    show("回读结果", resolution, "operation_id", "ledger_matches", "resolved", "resent")
    print(f"  合成流水显示 1 次动作；稳定 operation_id={resolution['operation_id']!r}。")
    print("  真实幂等/回读取决于具体操作与 API；本模型不解决崩溃后的持久恢复。")

    # ------------------------------------------------------------------ #
    section("9. 新客户端凭内存合成流水重建状态（仍不重发）")
    ledger2 = LedgerAPI(response_lost_below=1)
    first = OperationClient(ledger2, operation_id="op-0002")
    first.perform_write(Effect(key="synthetic/flag", value="on"))
    # 新的内存客户端：旧客户端的内存状态丢失，但合成流水仍被保留。
    # 这不是真实进程崩溃或持久存储测试；流水本身只在内存里。
    restarted = OperationClient(ledger2, operation_id="op-0002")
    recovery = restarted.recover_after_crash(Effect(key="synthetic/flag", value="on"))
    show("新客户端回读", recovery, "operation_id", "ledger_matches", "resolved", "resent")
    print(f"  流水条数：{len(ledger2.entries())}（没有出现第二次动作）。")
    print("  真实持久恢复需要 outbox、稳定 idempotency key 或人工核对，本模型不含。")


if __name__ == "__main__":
    main()
