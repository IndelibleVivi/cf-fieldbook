from __future__ import annotations

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("job_recovery_model", ROOT / "examples/job-state/model.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Jobs = module.Jobs


class RecoveryTests(unittest.TestCase):
    def test_interrupted_local_work_recovers_without_accepting_old_result(self):
        with TemporaryDirectory() as directory:
            path = str(Path(directory) / "jobs.sqlite3")
            worker_a = Jobs(path)
            worker_a.enqueue("local-work")
            self.assertEqual(worker_a.state("local-work"), ("pending", 0))
            old = worker_a.claim("local-work", now=0, lease_seconds=30)
            worker_a.close()  # A exits before committing a result.

            worker_b = Jobs(path)
            self.assertIsNone(worker_b.claim("local-work", now=29))
            new = worker_b.claim("local-work", now=30)
            self.assertEqual(new, 2)
            self.assertFalse(worker_b.finish("local-work", old, now=31, outcome="done"))
            self.assertEqual(worker_b.state("local-work"), ("running", 2))
            self.assertTrue(worker_b.finish("local-work", new, now=31, outcome="done"))
            worker_b.close()

            repeated_delivery = Jobs(path)
            repeated_delivery.enqueue("local-work")
            self.assertIsNone(repeated_delivery.claim("local-work", now=100))
            self.assertEqual(repeated_delivery.state("local-work"), ("done", 2))
            repeated_delivery.close()

    def test_known_retryable_failure_and_unknown_external_result_diverge(self):
        with TemporaryDirectory() as directory:
            path = str(Path(directory) / "jobs.sqlite3")
            first = Jobs(path)
            first.enqueue("safe-local-work")
            first.enqueue("external-effect")
            local = first.claim("safe-local-work", now=0)
            external = first.claim("external-effect", now=0)
            self.assertTrue(first.finish("safe-local-work", local, now=1, outcome="retryable"))
            synthetic_effects = ["external-effect"]  # Response lost after this action.
            self.assertTrue(first.finish("external-effect", external, now=1, outcome="uncertain"))
            first.close()

            recovered = Jobs(path)
            self.assertEqual(recovered.claim("safe-local-work", now=100), 2)
            replay = recovered.claim("external-effect", now=100)
            if replay is not None:
                synthetic_effects.append("external-effect")
            self.assertIsNone(replay)
            recovered.enqueue("external-effect")  # A repeated delivery does not reset it.
            self.assertIsNone(recovered.claim("external-effect", now=500))
            self.assertEqual(synthetic_effects, ["external-effect"])
            self.assertEqual(recovered.state("external-effect"), ("uncertain", 1))
            recovered.close()


if __name__ == "__main__":
    unittest.main()
