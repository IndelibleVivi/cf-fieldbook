from __future__ import annotations
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('job_model', ROOT / 'examples/job-state/model.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Jobs = module.Jobs


class JobStateTests(unittest.TestCase):
    def setUp(self):
        self.jobs = Jobs()
        self.jobs.enqueue('synthetic-1')

    def tearDown(self):
        self.jobs.close()

    def test_registered_is_not_done(self):
        self.assertEqual(self.jobs.state('synthetic-1'), ('pending', 0))
        self.assertEqual(self.jobs.claim('synthetic-1', 0), 1)

    def test_live_lease_prevents_parallel_claim(self):
        self.jobs.claim('synthetic-1', 0)
        self.assertIsNone(self.jobs.claim('synthetic-1', 1))

    def test_expired_lease_allows_recovery_and_fences_old_attempt(self):
        old = self.jobs.claim('synthetic-1', 0)
        new = self.jobs.claim('synthetic-1', 30)
        self.assertEqual(new, 2)
        self.assertFalse(self.jobs.finish('synthetic-1', old, 31, 'done'))
        self.assertTrue(self.jobs.finish('synthetic-1', new, 31, 'done'))

    def test_lost_ack_does_not_repeat_done_work(self):
        generation = self.jobs.claim('synthetic-1', 0)
        self.assertTrue(self.jobs.finish('synthetic-1', generation, 1, 'done'))
        self.jobs.enqueue('synthetic-1')
        self.assertIsNone(self.jobs.claim('synthetic-1', 40))

    def test_uncertain_is_not_automatically_retried(self):
        generation = self.jobs.claim('synthetic-1', 0)
        self.jobs.finish('synthetic-1', generation, 1, 'uncertain')
        self.assertIsNone(self.jobs.claim('synthetic-1', 500))
        self.assertFalse(self.jobs.cancel('synthetic-1'))

    def test_cancel_fences_running_commit(self):
        generation = self.jobs.claim('synthetic-1', 0)
        self.assertTrue(self.jobs.cancel('synthetic-1'))
        self.assertFalse(self.jobs.finish('synthetic-1', generation, 1, 'done'))

    def test_expired_commit_is_rejected_even_without_new_claim(self):
        generation = self.jobs.claim('synthetic-1', 0)
        self.assertFalse(self.jobs.finish('synthetic-1', generation, 30, 'done'))

    def test_state_survives_connection_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            path = str(Path(temp) / 'synthetic.sqlite3')
            first = Jobs(path)
            first.enqueue('job')
            first.claim('job', 0)
            first.close()
            second = Jobs(path)
            self.assertEqual(second.claim('job', 31), 2)
            second.close()


class CostTests(unittest.TestCase):
    def test_container_examples(self):
        from decimal import Decimal as D
        hours = D(100) * D(2) / D(60)
        self.assertLess(hours * 4, 25)
        self.assertLess(hours * D('.5') * 60, 375)
        self.assertLess(hours * 8, 200)
        idle_hours = D(100) * D(12) / D(60)
        self.assertEqual(idle_hours * 4, 80)
        self.assertEqual((idle_hours * 4 - 25) * D('.009'), D('.495'))

    def test_ai_search_and_artifacts_examples(self):
        from decimal import Decimal as D
        self.assertEqual(D(1) * D('.75') + D(2) * D('.75'), D('2.25'))
        self.assertEqual(D(10) * D('.15') + D(2) * D('.50'), D('2.50'))


if __name__ == '__main__':
    unittest.main()
