"""Focused checks for the offline api-operations teaching example.

These import the example's model directly and drive it with synthetic pages and
virtual time. They assert the failure families the example claims to show, so a
passing run is evidence about this model, not about any real API.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/api-operations"


def _load_model():
    spec = importlib.util.spec_from_file_location(
        "api_operations_model", EXAMPLE / "model.py")
    module = importlib.util.module_from_spec(spec)
    # Registered so dataclasses can resolve the defining module on older
    # Pythons; harmless on 3.11+.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


model = _load_model()
CursorAPI = model.CursorAPI
Page = model.Page
Effect = model.Effect
LedgerAPI = model.LedgerAPI
OperationClient = model.OperationClient
collect_inventory = model.collect_inventory


def _items(*ids: str) -> list[dict]:
    return [{"id": name} for name in ids]


class InventoryTests(unittest.TestCase):
    def test_all_pages_collected_and_terminal_outcome_checked(self):
        api = CursorAPI({
            None: Page(items=_items("a"), next_cursor="c1"),
            "c1": Page(items=_items("b"), next_cursor="c2"),
            "c2": Page(items=_items("c"), next_cursor=None),
        })
        report = collect_inventory(api, deadline_ms=1000)
        self.assertEqual(report["status"], "complete")
        self.assertEqual([i["id"] for i in report["items"]], ["a", "b", "c"])
        self.assertEqual(report["pages_read"], 3)
        self.assertEqual(report["attempted_pages"], 3)
        self.assertEqual(report["retries"], 0)
        self.assertIsNone(report["next_cursor"])
        self.assertIsNone(report["error"])

    def test_one_page_with_a_next_cursor_is_not_complete(self):
        # A caller that stopped at page one would report a partial inventory;
        # the model must keep following the cursor to the terminal page.
        api = CursorAPI({
            None: Page(items=_items("a"), next_cursor="c1"),
            "c1": Page(items=_items("b"), next_cursor=None),
        })
        report = collect_inventory(api, deadline_ms=1000)
        self.assertEqual(report["item_count"], 2)
        self.assertEqual(report["status"], "complete")

    def test_empty_first_page_with_next_cursor_does_not_stop_early(self):
        api = CursorAPI({
            None: Page(items=[], next_cursor="c1"),
            "c1": Page(items=_items("real"), next_cursor=None),
        })
        report = collect_inventory(api, deadline_ms=1000)
        self.assertEqual(report["status"], "complete")
        self.assertEqual([i["id"] for i in report["items"]], ["real"])
        self.assertEqual(report["pages_read"], 2)

    def test_transient_failure_then_success_within_one_deadline(self):
        api = CursorAPI(
            {None: Page(items=_items("a"), next_cursor=None, latency_ms=20)},
            fail_plan={None: ["transient"]},
        )
        report = collect_inventory(api, deadline_ms=1000, max_retries_per_page=2)
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["retries"], 1)
        # One failed dispatch plus the successful retry both reached the transport.
        self.assertEqual(report["attempted_pages"], 2)
        self.assertEqual(len(api.calls), 2)
        self.assertEqual([c["outcome"] for c in api.calls], ["transient", "ok"])
        self.assertIsNone(report["error"])

    def test_later_page_failure_preserves_items_and_reports_location(self):
        api = CursorAPI(
            {
                None: Page(items=_items("a"), next_cursor="c1", latency_ms=10),
                "c1": Page(items=[], next_cursor="c9", latency_ms=10,
                           outcome="transient", message="synthetic timeout"),
            },
            fail_plan={"c1": ["transient", "transient"]},
        )
        report = collect_inventory(api, deadline_ms=1000, max_retries_per_page=1)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual([i["id"] for i in report["items"]], ["a"])
        self.assertEqual(report["pages_read"], 1)
        self.assertEqual(report["retries"], 1)
        # 3 requests really reached the transport: page 1, the failure, the retry.
        self.assertEqual(report["attempted_pages"], 3)
        self.assertEqual(len(api.calls), 3)
        self.assertEqual([c["outcome"] for c in api.calls],
                         ["ok", "transient", "transient"])
        self.assertEqual(report["next_cursor"], "c1")
        self.assertIn("transient", report["error"])

    def test_deadline_bounds_the_whole_operation(self):
        api = CursorAPI({
            None: Page(items=_items("a"), next_cursor="c1", latency_ms=400),
            "c1": Page(items=_items("b"), next_cursor=None, latency_ms=600),
        })
        report = collect_inventory(api, deadline_ms=500)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual([i["id"] for i in report["items"]], ["a"])
        self.assertEqual(report["pages_read"], 1)
        # The second request was dispatched and timed out; it is counted.
        self.assertEqual(report["attempted_pages"], 2)
        self.assertEqual([c["outcome"] for c in api.calls], ["ok", "timeout"])
        self.assertEqual(report["next_cursor"], "c1")
        self.assertEqual(report["failing_cursor"], "c1")
        self.assertLessEqual(report["virtual_elapsed_ms"], 500)
        # The real timeout message is preserved rather than a prospective retry.
        self.assertIn("synthetic timeout", report["error"])

    def test_retries_consume_the_deadline_and_only_dispatched_retries_count(self):
        api = CursorAPI(
            {
                None: Page(items=_items("a"), next_cursor="c1", latency_ms=10),
                "c1": Page(items=[], next_cursor=None, latency_ms=40,
                           message="synthetic timeout"),
            },
            fail_plan={"c1": ["transient", "transient", "transient"]},
        )
        # Deadline 120ms: page1=10, then 40ms attempts fail at 50, 90, 120.
        report = collect_inventory(api, deadline_ms=120, max_retries_per_page=5)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["pages_read"], 1)
        self.assertEqual(report["next_cursor"], "c1")
        # 4 dispatches: page 1 + initial c1 + 2 retries; the budget stopped more.
        self.assertEqual(report["attempted_pages"], 4)
        self.assertEqual(report["retries"], 2)
        self.assertEqual(len(api.calls), 4)
        # No extra retry was dispatched after the deadline, so retries never
        # counts a retry that did not reach the transport.
        self.assertEqual(sum(1 for c in api.calls if c["outcome"] == "timeout"), 1)
        self.assertLessEqual(report["virtual_elapsed_ms"], 120)

    def test_recovered_page_does_not_mask_the_next_pages_deadline(self):
        api = CursorAPI({
            None: Page(items=_items('a'), next_cursor='c1', latency_ms=25),
            'c1': Page(items=_items('b'), next_cursor=None, latency_ms=10),
        }, fail_plan={None: ['transient']})
        report = collect_inventory(api, deadline_ms=50)
        self.assertEqual(report['status'], 'incomplete')
        self.assertEqual(report['failing_cursor'], 'c1')
        self.assertEqual(report['items'], _items('a'))
        self.assertEqual(report['attempted_pages'], 2)
        self.assertEqual(report['retries'], 1)
        self.assertIn('deadline', report['error'])
        self.assertNotIn('transient read failure', report['error'])

    def test_reusing_the_same_api_reports_per_operation_request_counts(self):
        api = CursorAPI({
            None: Page(items=_items("a"), next_cursor="c1", latency_ms=5),
            "c1": Page(items=_items("b"), next_cursor=None, latency_ms=5),
        })
        first = collect_inventory(api, deadline_ms=1000)
        self.assertEqual(first["attempted_pages"], 2)
        self.assertEqual(first["api_calls"], 2)
        # A second collection starts from a fresh cursor against the same object.
        second = collect_inventory(api, deadline_ms=1000)
        self.assertEqual(second["status"], "complete")
        self.assertEqual(second["attempted_pages"], 2)  # not 4
        self.assertEqual(second["api_calls"], 2)
        # The transport log itself is cumulative across both operations.
        self.assertEqual(len(api.calls), 4)

    def test_permanent_error_is_not_retried(self):
        api = CursorAPI({
            None: Page(items=_items("a"), next_cursor="c1", latency_ms=10),
            "c1": Page(items=[], outcome="permanent",
                       message="synthetic 403", latency_ms=10),
        })
        report = collect_inventory(api, deadline_ms=1000, max_retries_per_page=5)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["retries"], 0)
        self.assertEqual(report["pages_read"], 1)
        # The failing permanent request is still a dispatched attempt.
        self.assertEqual(report["attempted_pages"], 2)
        self.assertEqual(report["next_cursor"], "c1")
        self.assertIn("permanent", report["error"])
        self.assertEqual(report["failing_cursor"], "c1")
        # Only one call reached the transport for the failing cursor.
        self.assertEqual(sum(1 for c in api.calls if c["cursor"] == "c1"), 1)

    def test_repeated_cursor_is_bounded(self):
        # The loop uses only page.next_cursor; the collector must refuse it.
        api = CursorAPI({
            None: Page(items=_items("a"), next_cursor="loop", latency_ms=1),
            "loop": Page(items=_items("b"), next_cursor="loop", latency_ms=1),
        })
        report = collect_inventory(api, deadline_ms=1_000_000, max_pages=50)
        self.assertEqual(report["status"], "incomplete")
        self.assertIn("repeated cursor", report["error"])
        self.assertLess(report["pages_read"], 50)

    def test_page_limit_is_bounded_even_without_repeats(self):
        # A cursor chain longer than max_pages must stop at the limit.
        pages = {None: Page(items=_items("a"), next_cursor="0", latency_ms=1)}
        for n in range(30):
            pages[str(n)] = Page(items=_items(f"i{n}"), next_cursor=str(n + 1),
                                 latency_ms=1)
        report = collect_inventory(CursorAPI(pages), deadline_ms=1_000_000,
                                   max_pages=5)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["pages_read"], 5)
        self.assertIn("page limit", report["error"])

    def test_invalid_bounds_are_rejected(self):
        api = CursorAPI({None: Page(items=[])})
        with self.assertRaises(ValueError):
            collect_inventory(api, deadline_ms=0)
        with self.assertRaises(ValueError):
            collect_inventory(api, max_pages=0)
        with self.assertRaises(ValueError):
            collect_inventory(api, max_retries_per_page=-1)

    def test_no_sleep_and_no_retired_read_path(self):
        # Guardrail: virtual time is a counter, never a sleep, and the retired
        # unbounded read path / looping option must not come back.
        import ast
        source = (EXAMPLE / "model.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "sleep":
                self.fail("model.py must not call sleep")
        self.assertNotIn("repeat_cursor", source)
        self.assertNotIn("def fetch_page(", source)
        self.assertNotIn("_resolve_next", source)


class UncertainWriteTests(unittest.TestCase):
    def test_lost_response_reports_uncertain_without_repeating(self):
        ledger = LedgerAPI(response_lost_below=1)
        client = OperationClient(ledger, operation_id="op-1")
        attempt = client.perform_write(Effect(key="synthetic.k", value=1))
        self.assertEqual(attempt["status"], "uncertain")
        self.assertEqual(attempt["attempts"], 1)
        self.assertFalse(attempt["responded"])
        # The effect happened once; the client must not have sent it again.
        self.assertEqual(len(ledger.entries()), 1)

    def test_readback_resolves_uncertain_with_stable_identity(self):
        ledger = LedgerAPI(response_lost_below=1)
        client = OperationClient(ledger, operation_id="op-2")
        client.perform_write(Effect(key="synthetic.k", value=1))
        resolution = client.resolve_uncertain(Effect(key="synthetic.k", value=1))
        self.assertEqual(resolution["status"], "resolved_applied")
        self.assertEqual(resolution["operation_id"], "op-2")
        self.assertTrue(resolution["resolved"])
        self.assertFalse(resolution["resent"])
        self.assertFalse(client.unresolved)
        # Readback did not create a second effect.
        self.assertEqual(len(ledger.entries()), 1)

    def test_readback_with_absent_record_stays_unresolved(self):
        ledger = LedgerAPI(response_lost_below=0)
        client = OperationClient(ledger, operation_id="op-3")
        client.unresolved = True  # simulate an observed timeout without an effect
        resolution = client.resolve_uncertain(Effect(key="synthetic.k", value=1))
        self.assertEqual(resolution["status"], "not_observed")
        self.assertEqual(resolution["ledger_matches"], 0)
        self.assertFalse(resolution["resolved"])
        self.assertTrue(client.unresolved)  # still unresolved for a human/agent

    def test_readback_with_payload_mismatch_reports_conflict(self):
        ledger = LedgerAPI(response_lost_below=1)
        client = OperationClient(ledger, operation_id="op-6")
        client.perform_write(Effect(key="synthetic.k", value=1))
        resolution = client.resolve_uncertain(Effect(key="synthetic.k", value=2))
        self.assertEqual(resolution["status"], "conflict")
        self.assertEqual(resolution["ledger_matches"], 1)
        self.assertFalse(resolution["resolved"])
        self.assertTrue(client.unresolved)
        self.assertEqual(resolution["observed"]["value"], 1)
        self.assertEqual(resolution["intended"]["value"], 2)

    def test_readback_preserves_json_boolean_and_number_types(self):
        ledger = LedgerAPI(response_lost_below=1)
        client = OperationClient(ledger, operation_id='op-types')
        client.perform_write(Effect(key='synthetic.enabled', value=True))
        resolution = client.resolve_uncertain(Effect(key='synthetic.enabled', value=1))
        self.assertEqual(resolution['status'], 'conflict')
        self.assertFalse(resolution['resolved'])
        self.assertTrue(client.unresolved)
        self.assertEqual(len(ledger.entries()), 1)

    def test_readback_with_duplicate_identity_reports_conflict(self):
        ledger = LedgerAPI()
        ledger.append({"operation": "op-7", "key": "synthetic.k", "value": 1})
        ledger.append({"operation": "op-7", "key": "synthetic.k", "value": 1})
        client = OperationClient(ledger, operation_id="op-7")
        client.unresolved = True
        resolution = client.resolve_uncertain(Effect(key="synthetic.k", value=1))
        self.assertEqual(resolution["status"], "conflict")
        self.assertEqual(resolution["ledger_matches"], 2)
        self.assertFalse(resolution["resolved"])
        self.assertTrue(client.unresolved)
        self.assertFalse(resolution["resent"])

    def test_recover_after_crash_reads_ledger_without_resending(self):
        ledger = LedgerAPI(response_lost_below=1)
        first = OperationClient(ledger, operation_id="op-4")
        first.perform_write(Effect(key="synthetic.k", value=1))
        # A new in-memory client; the synthetic ledger object is retained.
        restarted = OperationClient(ledger, operation_id="op-4")
        recovery = restarted.recover_after_crash(Effect(key="synthetic.k", value=1))
        self.assertEqual(recovery["status"], "resolved_applied")
        self.assertTrue(recovery["resolved"])
        self.assertFalse(recovery["resent"])
        self.assertEqual(len(ledger.entries()), 1)

    def test_recover_after_crash_with_no_record_stays_unresolved(self):
        ledger = LedgerAPI()
        restarted = OperationClient(ledger, operation_id="op-8")
        recovery = restarted.recover_after_crash(Effect(key="synthetic.k", value=1))
        self.assertEqual(recovery["status"], "not_observed")
        self.assertFalse(recovery["resolved"])
        self.assertFalse(recovery["resent"])

    def test_fresh_client_cannot_write_after_unresolved_readback(self):
        ledger = LedgerAPI()
        restarted = OperationClient(ledger, operation_id='op-missing')
        effect = Effect(key='synthetic.k', value=1)
        recovery = restarted.recover_after_crash(effect)
        self.assertEqual(recovery['status'], 'not_observed')
        with self.assertRaises(ValueError):
            restarted.perform_write(effect)
        self.assertEqual(ledger.entries(), [])

    def test_perform_write_is_single_shot(self):
        ledger = LedgerAPI()
        client = OperationClient(ledger, operation_id="op-5")
        client.perform_write(Effect(key="synthetic.k", value=1))
        with self.assertRaises(ValueError):
            client.perform_write(Effect(key="synthetic.k", value=1))
        self.assertEqual(len(ledger.entries()), 1)

    def test_resolve_requires_a_pending_operation(self):
        ledger = LedgerAPI()
        client = OperationClient(ledger, operation_id="op-9")
        with self.assertRaises(ValueError):
            client.resolve_uncertain(Effect(key="synthetic.k", value=1))


class DemoInvocationTests(unittest.TestCase):
    def test_demo_runs_offline_and_prints_expected_markers(self):
        result = subprocess.run(
            [sys.executable, "examples/api-operations/demo.py"],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        for marker in ("三页收集", "virtual_elapsed_ms", "attempted_pages",
                       "status='incomplete'", "status='uncertain'",
                       "resolved_applied", "operation_id", "新客户端回读"):
            self.assertIn(marker, output)


if __name__ == "__main__":
    unittest.main()
