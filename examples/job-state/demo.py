"""Deterministic, offline walk-through of recovery and an uncertain effect."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from model import Jobs


def show(label: str, actual: object, expected: object) -> None:
    print(f"{label}: {actual}")
    if actual != expected:
        raise RuntimeError(f"{label}: expected {expected!r}, got {actual!r}")


def main() -> None:
    with TemporaryDirectory() as directory:
        path = str(Path(directory) / "synthetic-jobs.sqlite3")

        first = Jobs(path)
        first.enqueue("local-transform")
        show("登记后状态", first.state("local-transform"), ("pending", 0))
        old_generation = first.claim("local-transform", now=0, lease_seconds=30)
        show("worker A 领取 generation", old_generation, 1)
        first.close()  # 模拟 worker 在完成前退出；数据库文件仍在。

        recovered = Jobs(path)
        show("t=10 租约内不可再领取", recovered.claim("local-transform", now=10), None)
        new_generation = recovered.claim("local-transform", now=30)
        show("t=30 worker B 恢复领取 generation", new_generation, 2)
        show(
            "t=31 旧 generation 迟到提交被拒绝",
            recovered.finish("local-transform", old_generation, now=31, outcome="done"),
            False,
        )
        show(
            "t=31 新 generation 完成",
            recovered.finish("local-transform", new_generation, now=31, outcome="done"),
            True,
        )
        show("完成后的重复领取", recovered.claim("local-transform", now=100), None)

        recovered.enqueue("external-effect")
        effect_generation = recovered.claim("external-effect", now=100)
        show("外部任务领取 generation", effect_generation, 1)
        # 合成服务先记下动作，再丢失响应；worker 只能观察到 timeout。
        synthetic_ledger: dict[str, int] = {}
        try:
            synthetic_ledger["external-effect"] = 1
            raise TimeoutError("synthetic response lost")
        except TimeoutError:
            show(
                "响应丢失后记录 uncertain",
                recovered.finish("external-effect", effect_generation, now=101, outcome="uncertain"),
                True,
            )
        recovered.close()

        restarted = Jobs(path)
        show("t=500 uncertain 仍不可自动领取", restarted.claim("external-effect", now=500), None)
        show("模拟人工核对：合成外部流水的动作次数", synthetic_ledger["external-effect"], 1)
        show("核对后状态仍待人工处置", restarted.state("external-effect"), ("uncertain", 1))
        restarted.close()


if __name__ == "__main__":
    main()
