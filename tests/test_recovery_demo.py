from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('recovery_demo', ROOT / 'tools/recovery_demo.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RecoveryDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenarios = {item['id']: item for item in module.scenarios(ROOT)}

    def test_normal_completion_and_duplicate_delivery(self):
        frames = self.scenarios['normal']['frames']
        self.assertEqual((frames[0]['state'], frames[0]['generation']), ('pending', 0))
        self.assertEqual((frames[1]['state'], frames[1]['generation'], frames[1]['lease_until']), ('running', 1, 31))
        self.assertIs(frames[8]['result'], True)
        self.assertEqual((frames[8]['state'], frames[8]['lease_until']), ('done', 0))
        self.assertIsNone(frames[10]['result'])

    def test_reconnect_keeps_lease_and_exact_takeover_boundary(self):
        frames = self.scenarios['interrupted']['frames']
        self.assertEqual((frames[4]['connection'], frames[4]['state'], frames[4]['generation'], frames[4]['lease_until']), (2, 'running', 1, 31))
        self.assertIsNone(frames[30]['result'])
        self.assertEqual(frames[30]['lease_remaining'], 1)
        self.assertEqual((frames[31]['result'], frames[31]['generation'], frames[31]['lease_until']), (2, 2, 61))
        self.assertIs(frames[35]['result'], True)

    def test_late_generation_cannot_overwrite_new_holder(self):
        frames = self.scenarios['stale']['frames']
        self.assertIs(frames[32]['result'], False)
        self.assertEqual((frames[32]['state'], frames[32]['generation'], frames[32]['lease_until']), ('running', 2, 61))
        self.assertIs(frames[35]['result'], True)

    def test_uncertain_persists_and_does_not_auto_replay(self):
        frames = self.scenarios['uncertain']['frames']
        self.assertEqual(frames[3]['external_count'], 1)
        self.assertIs(frames[4]['result'], True)
        self.assertEqual((frames[5]['state'], frames[5]['connection']), ('uncertain', 2))
        for time in [31, 60]:
            self.assertIsNone(frames[time]['result'])
            self.assertEqual((frames[time]['state'], frames[time]['generation'], frames[time]['external_count']), ('uncertain', 1, 1))

    def test_crash_before_uncertain_remains_an_honest_counterexample(self):
        frames = self.scenarios['crash-window']['frames']
        self.assertEqual((frames[4]['state'], frames[4]['external_count'], frames[4]['connection']), ('running', 1, 2))
        self.assertIsNone(frames[30]['result'])
        self.assertEqual(frames[31]['result'], 2)
        self.assertEqual(frames[32]['external_count'], 2)
        self.assertEqual((frames[35]['state'], frames[35]['external_count']), ('done', 2))

    def test_every_scrub_frame_matches_latest_executed_operation(self):
        for scenario in self.scenarios.values():
            for time, frame in enumerate(scenario['frames']):
                event = scenario['events'][frame['event_index']]
                self.assertEqual(frame['time'], time)
                self.assertLessEqual(event['time'], time)
                for field in ('state', 'generation', 'lease_until', 'event', 'result', 'connection', 'external_count'):
                    self.assertEqual(frame[field], event[field])
                self.assertEqual(frame['lease_remaining'], max(0, frame['lease_until'] - time) if frame['state'] == 'running' else 0)

    def test_static_overview_and_json_are_real_results(self):
        body = module.page_body(ROOT)
        encoded = re.search(r'<script id="recovery-data" type="application/json">(.*?)</script>', body, re.S)[1]
        self.assertEqual(json.loads(encoded), list(self.scenarios.values()))
        self.assertIn('id="recovery-interactive" hidden', body)
        self.assertIn('id="recovery-fallback"', body)
        self.assertIn('未解决的崩溃窗口', body)
        self.assertIn('Cloudflare 实测', body)
        self.assertEqual(body.count('<details>'), 5)


if __name__ == '__main__':
    unittest.main()
