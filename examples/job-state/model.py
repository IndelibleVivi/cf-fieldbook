"""Offline teaching model: fenced job states, NOT a D1 or queue adapter.

No network, external action, background scheduler or automatic reconciliation.
The injected clock makes crash/recovery examples deterministic.
"""
from __future__ import annotations
import sqlite3


class Jobs:
    def __init__(self, path: str = ":memory:") -> None:
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            state TEXT NOT NULL CHECK(state IN
                ('pending','running','retryable','done','uncertain','cancelled')),
            generation INTEGER NOT NULL DEFAULT 0,
            lease_until INTEGER NOT NULL DEFAULT 0
        )""")
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def enqueue(self, job_id: str) -> None:
        if not job_id:
            raise ValueError("job_id must not be empty")
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO jobs(id,state) VALUES (?, 'pending')", (job_id,)
            )

    def state(self, job_id: str) -> tuple[str, int] | None:
        row = self.db.execute(
            "SELECT state,generation FROM jobs WHERE id=?", (job_id,)
        ).fetchone()
        return row

    def claim(self, job_id: str, now: int, lease_seconds: int = 30) -> int | None:
        """Reclaiming is valid only for local/idempotent work in this example."""
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        with self.db:
            row = self.db.execute("""UPDATE jobs
                SET state='running', generation=generation+1, lease_until=?
                WHERE id=? AND (
                  state IN ('pending','retryable') OR
                  (state='running' AND lease_until<=?))
                RETURNING generation""", (now + lease_seconds, job_id, now)).fetchone()
        return None if row is None else int(row[0])

    def finish(self, job_id: str, generation: int, now: int, outcome: str) -> bool:
        if outcome not in {'done', 'retryable', 'uncertain'}:
            raise ValueError("invalid outcome")
        with self.db:
            cur = self.db.execute("""UPDATE jobs SET state=?, lease_until=0
                WHERE id=? AND state='running'
                  AND generation=? AND lease_until>?""",
                (outcome, job_id, generation, now))
        return cur.rowcount == 1

    def cancel(self, job_id: str) -> bool:
        # Cancellation fences commits. It cannot undo an external operation.
        with self.db:
            cur = self.db.execute("""UPDATE jobs
                SET state='cancelled', generation=generation+1, lease_until=0
                WHERE id=? AND state IN ('pending','running','retryable')""", (job_id,))
        return cur.rowcount == 1
