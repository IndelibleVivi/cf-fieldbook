"""Offline teaching model: paginated inventory reads and an uncertain write.

This is a language-neutral mechanism demonstration written in Python. It is NOT
the real Cloudflare Python or Go SDK, does not perform HTTP, and does not prove
anything about real API behavior. See README.md for source and evidence limits.

Design of this file:

* A synthetic ``CursorAPI`` serves fixed pages from local data. There is no
  transport, no credential, no retry inside the transport. It records every
  dispatched request, so the demo and tests can count real attempts per operation
  and show which retries actually reached the transport.
* ``collect_inventory`` owns the *policy*: a bounded total deadline shared by
  every page request and transient retry, a bounded number of retries per page,
  and a hard limit on pages / repeated cursors so a malformed or looping cursor
  cannot create an endless inventory. It passes the *remaining* budget to each
  request; the request is attempted and times out at the budget boundary, so the
  total deadline is never exceeded.
* No ``time.sleep``. Time is virtual: the caller injects latency through the
  fixture, and the collector advances its own virtual clock by the modeled
  elapsed time of each call. The result is deterministic.
* Results are plain dictionaries suitable for a truthful agent report. Request
  counts are measured from the transport's own call log for *this* operation, so
  they stay correct when the same API object is reused.

Two extra interfaces support the write section:

* ``LedgerAPI`` stores an append-only effect ledger (synthetic standing in for
  what a real service would expose).
* Write helpers are explicit and single-shot: an attempt that loses its response
  reports ``uncertain`` and is never repeated automatically; recovery is an
  explicit, separate readback call with a stable operation identity.

Real idempotency and readback depend on the operation and the specific API. This
model does not solve durable crash recovery: nothing here records an intent
before dispatch, so a real crash between dispatch and a persisted result would
still need an outbox, a stable idempotency key, or explicit reconciliation.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


# --------------------------------------------------------------------------- #
# Synthetic transport
# --------------------------------------------------------------------------- #


class PermanentError(Exception):
    """A read error that is not worth retrying (rejected request, not-found)."""


class TransientError(Exception):
    """A read error that may be worth one bounded retry (timeout, reset)."""


@dataclass
class Page:
    """One synthetic page of a paginated inventory.

    ``outcome`` is ``"ok"``, ``"transient"`` or ``"permanent"``. ``ok`` with a
    non-``None`` ``next_cursor`` means more data follows; ``ok`` with
    ``next_cursor=None`` is the only terminal success.
    """

    items: list[dict[str, Any]]
    next_cursor: str | None = None
    outcome: str = "ok"
    message: str = ""
    latency_ms: int = 0


class CursorAPI:
    """A deterministic, offline cursor API over fixed synthetic pages.

    Pages are looked up by cursor; ``None`` is the first request. A looping
    inventory is expressed simply by pointing a page's ``next_cursor`` back at a
    cursor that was already seen; the bounded collector refuses to follow it
    forever.

    A page's ``outcome`` can also be driven by ``fail_plan``: a mapping from
    cursor to a list of outcomes that are consumed one call at a time, so a
    flaky fixture can fail *then* succeed on the same cursor. When the list for a
    cursor is exhausted, the page's own ``outcome`` is used. ``fail_plan``
    overrides the page outcome but not its items or next cursor.

    The class records an interaction log and advances an internal virtual clock
    by each page's ``latency_ms``; it never sleeps and never touches the network.
    """

    def __init__(
        self,
        pages: dict[str | None, Page],
        fail_plan: dict[str | None, list[str]] | None = None,
    ) -> None:
        self.pages = pages
        self.fail_plan = {c: list(v) for c, v in (fail_plan or {}).items()}
        self.clock_ms = 0
        self.calls: list[dict[str, Any]] = []
        self.closed = False

    def fetch_page_within(self, cursor: str | None, budget_ms: int) -> Page:
        """Dispatch one request and return its page, or raise.

        This is the only read path: the caller always supplies the remaining
        budget, so the synthetic transport is never asked to wait unbounded. A
        page whose latency exceeds ``budget_ms`` is *attempted* and then times
        out at the budget boundary, raising :class:`TransientError`; the clock
        advances by the time actually spent, so a total deadline is preserved.

        Every dispatched request is appended to ``calls``, including requests
        that fail, so a truthful per-operation count is available to the caller.
        """
        if self.closed:
            raise PermanentError("api already closed")
        page = self.pages.get(cursor)
        if page is None:
            page = Page(items=[], next_cursor=None, outcome="permanent",
                        message=f"unknown cursor {cursor!r}")
        plan = self.fail_plan.get(cursor, [])
        outcome = plan.pop(0) if plan else page.outcome
        # The request is dispatched; if it would exceed the budget it times out
        # at the budget boundary rather than waiting for the full latency.
        if page.latency_ms > budget_ms:
            self.calls.append({"cursor": cursor, "outcome": "timeout",
                               "latency_ms": budget_ms})
            self.clock_ms += budget_ms
            raise TransientError(
                f"synthetic timeout: cursor {cursor!r} needs {page.latency_ms}ms "
                f"but only {budget_ms}ms of budget remain")
        self.calls.append({"cursor": cursor, "outcome": outcome,
                           "latency_ms": page.latency_ms})
        self.clock_ms += page.latency_ms
        if outcome == "transient":
            raise TransientError(page.message or "synthetic transient failure")
        if outcome == "permanent":
            raise PermanentError(page.message or "synthetic permanent failure")
        return Page(items=list(page.items), next_cursor=page.next_cursor,
                    outcome="ok", latency_ms=page.latency_ms)

    def close(self) -> None:
        self.closed = True


# --------------------------------------------------------------------------- #
# Inventory collection
# --------------------------------------------------------------------------- #


class InventoryIncomplete(Exception):
    """Internal signal: collection stopped before the terminal page."""

    def __init__(self, error: str, failing_cursor: str | None,
                 next_cursor: str | None) -> None:
        super().__init__(error)
        self.error = error
        self.failing_cursor = failing_cursor
        self.next_cursor = next_cursor


def collect_inventory(
    api: CursorAPI,
    *,
    deadline_ms: int = 5000,
    max_pages: int = 100,
    max_retries_per_page: int = 2,
    initial_cursor: str | None = None,
) -> dict[str, Any]:
    """Collect every page within one bounded total deadline.

    Returns a structured, JSON-serialisable report. A one-page read that still
    has a next cursor is *not* a complete inventory. On any shortfall the report
    is ``status="incomplete"`` and keeps the items already collected.

    ``deadline_ms`` bounds the whole operation: each request advances virtual
    time by the page's modeled latency, or to the deadline on timeout. No
    wall-clock time and no sleeps are used.

    Request counts come from the transport call log for *this* call only, so
    reusing the same ``api`` for a second collection does not carry over the
    first collection's requests:

    * ``attempted_pages`` counts every dispatched request that reached the
      transport, including the final request that failed.
    * ``retries`` counts only retries that actually reached the transport; a
      retry interrupted by the deadline before dispatch is not counted.

    When the budget is exhausted the report keeps the last real error and the
    cursor to resume from, rather than a prospective retry that never happened.
    """
    if deadline_ms <= 0:
        raise ValueError("deadline_ms must be positive")
    if max_pages <= 0:
        raise ValueError("max_pages must be positive")
    if max_retries_per_page < 0:
        raise ValueError("max_retries_per_page must not be negative")

    started_ms = api.clock_ms
    deadline_at = started_ms + deadline_ms
    calls_at_start = len(api.calls)  # per-operation baseline for request counts
    items: list[dict[str, Any]] = []
    pages_read = 0
    retries = 0
    seen_cursors: set[str] = set()
    cursor = initial_cursor
    error: str | None = None

    try:
        while True:
            if pages_read >= max_pages:
                raise InventoryIncomplete(
                    f"page limit reached (max_pages={max_pages})", None, cursor)
            if cursor in seen_cursors:
                raise InventoryIncomplete(
                    f"repeated cursor {cursor!r}: refusing to loop", None, cursor)

            page_retries = 0
            while True:
                if api.clock_ms >= deadline_at:
                    # The budget was consumed by an earlier request; nothing is
                    # dispatched now. Keep the most recent real error if any.
                    raise InventoryIncomplete(
                        error or (
                            f"deadline ({deadline_ms}ms) exhausted before reading "
                            f"cursor {cursor!r}"),
                        cursor, cursor)
                remaining_ms = deadline_at - api.clock_ms
                try:
                    page = api.fetch_page_within(cursor, remaining_ms)
                    break
                except TransientError as exc:
                    error = f"transient read failure at cursor {cursor!r}: {exc}"
                    if api.clock_ms >= deadline_at:
                        # The failing attempt spent the last of the budget; it
                        # is the final request, so no retry occurred.
                        raise InventoryIncomplete(error, cursor, cursor) from exc
                    if page_retries >= max_retries_per_page:
                        raise InventoryIncomplete(
                            f"{error} (no retries left: "
                            f"max_retries_per_page={max_retries_per_page})",
                            cursor, cursor) from exc
                    page_retries += 1
                    # This retry will be dispatched on the next loop iteration.
                    retries += 1
                except PermanentError as exc:
                    # Never retried: a permanent error will not become success.
                    raise InventoryIncomplete(
                        f"permanent read failure at cursor {cursor!r}: {exc}",
                        cursor, cursor) from exc

            error = None  # A recovered page must not leave an outstanding failure.
            pages_read += 1
            items.extend(page.items)
            if page.next_cursor is None:
                break
            seen_cursors.add(cursor)
            cursor = page.next_cursor
    except InventoryIncomplete as incomplete:
        error = incomplete.error
        next_cursor = incomplete.next_cursor
        failing_cursor = incomplete.failing_cursor
        status = "incomplete"
    else:
        # A successful collection has no outstanding error, even if transient
        # failures were retried and recovered along the way.
        next_cursor = None
        failing_cursor = None
        error = None
        status = "complete"

    attempted_pages = len(api.calls) - calls_at_start
    if api.clock_ms - started_ms > deadline_ms:
        raise AssertionError("deadline invariant violated")
    return {
        "status": status,
        "items": items,
        "item_count": len(items),
        "pages_read": pages_read,
        "attempted_pages": attempted_pages,
        "retries": retries,
        "last_cursor": cursor,
        "failing_cursor": failing_cursor,
        "next_cursor": next_cursor,
        "error": error,
        "started_at_ms": started_ms,
        "ended_at_ms": api.clock_ms,
        "virtual_elapsed_ms": api.clock_ms - started_ms,
        "deadline_ms": deadline_ms,
        "api_calls": attempted_pages,
    }


# --------------------------------------------------------------------------- #
# Uncertain writes and explicit resolution
# --------------------------------------------------------------------------- #


class LedgerAPI:
    """Synthetic append-only effect ledger (a stand-in for a real service log).

    ``append`` records an effect and returns its ``index``. ``response_lost_below``
    counts how many initial appends performed the effect but lost the response,
    so the caller sees a timeout. ``entries`` stands in for a control-plane read
    that reports what actually happened.
    """

    def __init__(self, response_lost_below: int = 0) -> None:
        self._effects: list[dict[str, Any]] = []
        self._lost_below = response_lost_below

    def append(self, effect: dict[str, Any]) -> int:
        self._effects.append(dict(effect))
        if len(self._effects) <= self._lost_below:
            # The effect is recorded in memory, but its response is lost.
            raise TimeoutError("synthetic response lost after effect recorded")
        return len(self._effects) - 1

    def entries(self) -> list[dict[str, Any]]:
        return [dict(e) for e in self._effects]

    def clear(self) -> None:
        self._effects.clear()


@dataclass
class Effect:
    key: str
    value: Any


class OperationClient:
    """Single-shot synthetic write client with an explicit readback path.

    It keeps a stable ``operation_id``. ``perform_write`` sends the effect
    exactly once and returns either ``applied`` (with a response) or
    ``uncertain`` (no response). ``resolve_uncertain`` is a *separate, explicit*
    readback; ``recover_after_crash`` re-derives status from the ledger without
    resending.
    """

    def __init__(self, api: LedgerAPI, operation_id: str) -> None:
        if not operation_id:
            raise ValueError("operation_id must not be empty")
        self.api = api
        self.operation_id = operation_id
        self.status = "new"
        self.unresolved = False

    def perform_write(self, effect: Effect) -> dict[str, Any]:
        if self.status != "new" or self.unresolved:
            raise ValueError("perform_write is single-shot for a given operation")
        try:
            index = self.api.append({"operation": self.operation_id,
                                     "key": effect.key, "value": effect.value})
        except TimeoutError as exc:
            self.status = "uncertain"
            self.unresolved = True
            return {"status": "uncertain", "operation_id": self.operation_id,
                    "attempts": 1, "responded": False, "error": str(exc),
                    "effect": {"key": effect.key, "value": effect.value},
                    "note": "do not repeat automatically; read back first"}
        self.status = "applied"
        return {"status": "applied", "operation_id": self.operation_id,
                "attempts": 1, "responded": True, "response_index": index,
                "effect": {"key": effect.key, "value": effect.value}}

    def resolve_uncertain(self, effect: Effect) -> dict[str, Any]:
        """Readback only. Never resends the effect.

        Returns ``resolved_applied`` only when the ledger shows exactly one
        effect matching this operation identity *and* the intended payload. A
        missing observation yields ``not_observed`` and keeps the operation
        unresolved: absence of a record is not proof that replaying is safe. A
        payload mismatch or more than one matching effect yields ``conflict`` and
        also keeps the operation unresolved.
        """
        if not self.unresolved:
            raise ValueError("nothing to resolve for this operation")
        return self._readback(effect, "resolve_uncertain")

    def recover_after_crash(self, effect: Effect) -> dict[str, Any]:
        """Re-derive status from the ledger alone, in a fresh client.

        Same readback as ``resolve_uncertain``, but framed for a new in-memory
        client that lost the previous client's ``unresolved`` flag while the
        synthetic ledger was retained. This models re-reading the service record,
        not an actual process crash or durable storage: the ledger here lives
        only in memory. It still cannot distinguish "not sent" from "sent but
        never observed" without a prior intent record.
        """
        return self._readback(effect, "recover_after_crash")

    def _readback(self, effect: Effect, label: str) -> dict[str, Any]:
        wanted = {"key": effect.key, "value": effect.value}
        matches = [e for e in self.api.entries()
                   if e["operation"] == self.operation_id]

        if not matches:
            # No record seen. Keep the operation unresolved: a missing readback
            # is not real-world proof that the write did not land.
            self.unresolved = True
            return {"status": "not_observed", "operation_id": self.operation_id,
                    "checked": label, "ledger_matches": 0,
                    "intended": wanted, "resent": False, "resolved": False,
                    "reason": "no ledger record for this operation; still unresolved"}

        if len(matches) > 1:
            self.unresolved = True
            return {"status": "conflict", "operation_id": self.operation_id,
                    "checked": label, "ledger_matches": len(matches),
                    "intended": wanted, "resent": False, "resolved": False,
                    "reason": f"{len(matches)} effects share this operation "
                              f"identity; refusing to pick one"}

        observed = {"key": matches[0]["key"], "value": matches[0]["value"]}
        # JSON types are significant: Python equality alone treats True == 1.
        if json.dumps(observed, sort_keys=True) != json.dumps(wanted, sort_keys=True):
            self.unresolved = True
            return {"status": "conflict", "operation_id": self.operation_id,
                    "checked": label, "ledger_matches": 1, "intended": wanted,
                    "observed": observed, "resent": False, "resolved": False,
                    "reason": "the recorded payload differs from the intended one"}

        self.status = "applied"
        self.unresolved = False
        return {"status": "resolved_applied", "operation_id": self.operation_id,
                "checked": label, "ledger_matches": 1, "intended": wanted,
                "observed": observed, "resent": False, "resolved": True,
                "note": "exactly one matching effect; no resend"}
