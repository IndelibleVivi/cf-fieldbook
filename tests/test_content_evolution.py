from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from content import observability_costs, project_markdown
from recovery_demo import page_body
import publications as pub
from bs4 import BeautifulSoup


class ContentEvolutionTests(unittest.TestCase):
    def test_partial_update_keeps_pricing_date_and_explicit_override(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT / 'catalog', root / 'catalog')
            (root / 'examples/decision-routing').mkdir(parents=True)
            shutil.copyfile(ROOT / 'examples/decision-routing/payloads.py',
                            root / 'examples/decision-routing/payloads.py')
            for relative in ('guides/handbook.md', 'services/observability.md'):
                with self.subTest(page=relative):
                    original = (ROOT / relative).read_text()
                    updated = re.sub(r'^source_cutoff: .*$', 'source_cutoff: 2026-12-01', original, flags=re.M)
                    target = root / relative
                    target.parent.mkdir(exist_ok=True)
                    target.write_text(updated)
                    def block(text):
                        return text.split('<!-- facts: observability-costs -->', 1)[1].split('<!-- /facts -->', 1)[0]
                    self.assertEqual(block(project_markdown(root, relative)), block(original))
                    future = block(project_markdown(root, relative, as_of='2026-12-01'))
                    self.assertIn('固定资料日期：**2026-12-01**', future)
                    self.assertNotIn('当前 Workers Logs', future)
                    target.write_text(re.sub(r'^observability_as_of: .*\n', '', updated, flags=re.M))
                    self.assertEqual(block(project_markdown(root, relative)), future)
                    target.write_text(updated.replace(re.search(r'^observability_as_of: .*$', original, re.M)[0],
                                                      'observability_as_of: 2026-13-99'))
                    with self.assertRaises(ValueError):
                        project_markdown(root, relative)

    def test_announced_pricing_does_not_apply_early(self):
        before = observability_costs(ROOT, '2026-11-30')
        after = observability_costs(ROOT, '2026-12-01')
        self.assertIn('当前 Workers Logs', before)
        self.assertIn('将在 2026-12-01 生效', before)
        self.assertNotIn('当前 Workers Logs', after)
        self.assertIn('未因此刷新核验', after)
        self.assertIn('10 GB-month', after)
        self.assertNotIn('12 GB-month', after)
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
