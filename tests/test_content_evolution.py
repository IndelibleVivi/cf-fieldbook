from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from content import observability_costs, project_markdown
from recovery_demo import page_body
import publications as pub
from bs4 import BeautifulSoup


class ContentEvolutionTests(unittest.TestCase):
    def test_announced_pricing_does_not_apply_early(self):
        before = observability_costs(ROOT, '2026-11-30')
        after = observability_costs(ROOT, '2026-12-01')
        self.assertIn('当前 Workers Logs', before)
        self.assertIn('将在 2026-12-01 生效', before)
        self.assertNotIn('当前 Workers Logs', after)
        self.assertIn('未因此刷新核验', after)
        self.assertIn('12 GB-month', after)
        self.assertEqual(before, observability_costs(ROOT, '2026-11-30'))

    def test_current_projection_and_historical_report_are_separate(self):
        historical = 'reports/2026-10-02.md'
        self.assertEqual(project_markdown(ROOT, historical, as_of='2026-12-01'), (ROOT / historical).read_text())
        self.assertIn('当前 Workers Logs', project_markdown(ROOT, 'guides/handbook.md'))
        future = project_markdown(ROOT, 'guides/handbook.md', as_of='2026-12-01')
        block = future.split('<!-- facts: observability-costs -->', 1)[1].split('<!-- /facts -->', 1)[0]
        self.assertNotIn('当前 Workers Logs', block)
        self.assertNotIn('200,000 events', block)

    def test_controls_own_actual_recorded_feedback(self):
        soup = BeautifulSoup(page_body(ROOT), 'html.parser')
        controls = soup.select_one('.recovery-controls')
        self.assertIsNotNone(controls.select_one('#recovery-explanation'))
        self.assertIsNotNone(controls.select_one('#recovery-next'))
        self.assertEqual(len(soup.select('#recovery-explanation')), 1)
        self.assertEqual(len(soup.select('#recovery-fallback details')), 5)

    def test_insertion_and_actual_reordering_keep_chapter_identity(self):
        import re
        text = (ROOT / 'guides/handbook.md').read_text()
        config = pub.chapter_config(pub.family(pub.load(ROOT), 'handbook'))
        parts = re.split(r'(?=<!-- chapter:)', text)
        original = pub.parse_chapters(text, config)
        changed = parts[0] + parts[2] + '\n<!-- chapter: shelf-lab -->\n## 00 / 新插入的练习\n\n合成段落。\n' + parts[1] + ''.join(parts[3:])
        chapters = pub.parse_chapters(changed, config)
        by_id = {chapter['id']: chapter for chapter in chapters}
        self.assertEqual([chapter['id'] for chapter in chapters[:3]], ['routes', 'shelf-lab', 'start'])
        for chapter in original:
            self.assertEqual(by_id[chapter['id']]['type'], chapter['type'])
            self.assertEqual(by_id[chapter['id']]['anchor'], chapter['anchor'])
        self.assertEqual(by_id['shelf-lab']['type'], '')


if __name__ == '__main__':
    unittest.main()
