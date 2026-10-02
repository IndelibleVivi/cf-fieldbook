"""Edition isolation and maintained facts, using actual reader manuscripts."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import content
import editions


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for source in editions.included(ROOT):
            target = self.root / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

    def routes(self, edit):
        path = self.root / 'catalog/decision-routes.json'
        data = json.loads(path.read_text())
        edit(data['routes'])
        path.write_text(json.dumps(data, ensure_ascii=False))

    def test_new_price_and_token_basis_reach_all_consumers_but_not_history(self):
        report = (self.root / 'reports/2026-10-02.md').read_bytes()
        def edit(rows):
            rows[0].update(input_usd_per_million=2, model='Changed model',
                           tokenizer='different accounting', selector='new/selector')
        self.routes(edit)
        self.assertEqual(set(content.sync(self.root, check=True)), set(content.PAGES))
        with self.assertRaisesRegex(ValueError, 'drifted'):
            editions.freeze(self.root, 'stale')
        content.sync(self.root, check=False)
        for page in content.PAGES:
            text = (self.root / page).read_text()
            self.assertIn('Changed model', text)
            self.assertIn('new/selector', text)
        comparison = (self.root / 'comparisons/clef-vs-jev.md').read_text()
        self.assertIn('$100.00', comparison)
        self.assertIn('different accounting', comparison)
        self.assertEqual(report, (self.root / 'reports/2026-10-02.md').read_bytes())

    def test_unknown_cost_and_missing_marker_cannot_pass_as_current(self):
        self.routes(lambda rows: rows[0].update(input_usd_per_million=None))
        text = content.project_markdown(self.root, 'comparisons/clef-vs-jev.md')
        self.assertIn('未知，不能计算', text)
        page = self.root / 'services/decision-models.md'
        page.write_text(content.BLOCK.sub('', page.read_text()))
        with self.assertRaisesRegex(ValueError, 'fact block'):
            content.sync(self.root, check=True)

    def test_frozen_code_prices_styles_and_historical_sources_survive_live_edits(self):
        # Catalog can evolve; the report's own references still own its old bibliography.
        sources = self.root / 'catalog/sources.json'
        data = json.loads(sources.read_text())
        data[0].update(title='LIVE_SOURCE_SENTINEL', url='https://example.invalid/changed')
        sources.write_text(json.dumps(data))
        content.sync(self.root, check=False)
        target = editions.freeze(self.root, 'test-1')
        before = {p.relative_to(self.root): p.read_bytes() for p in editions.included(self.root)}
        (self.root / 'tools/render.py').write_text('raise RuntimeError("live renderer was used")')
        (self.root / 'styles/report.css').write_text('LIVE_STYLE_SENTINEL')
        self.routes(lambda rows: rows[0].update(input_usd_per_million=999))
        output = editions.build(self.root, 'test-1', ['md', 'html'])
        self.assertEqual(len(list(output.iterdir())), 6)
        self.assertNotIn('LIVE_SOURCE_SENTINEL', next(output.glob('cf-launches*.html')).read_text())
        self.assertNotIn('LIVE_STYLE_SENTINEL', next(output.glob('cf-practical*.html')).read_text())
        self.assertIn('$2.10', next(output.glob('cf-clef*.md')).read_text())
        # Snapshot and original edited prose retain exact bytes after rendering.
        for relative, data in before.items():
            self.assertEqual((target / 'inputs' / relative).read_bytes(), data)
            if relative.suffix == '.md':
                self.assertEqual((self.root / relative).read_bytes(), data)
        self.assertEqual(editions.check(self.root, 'test-1')['build_state'], 'built-local-candidate')
        with self.assertRaisesRegex(ValueError, 'already exist'):
            editions.build(self.root, 'test-1', ['html'])
        next(output.glob('*.html')).write_text('modified')
        with self.assertRaisesRegex(ValueError, 'output changed'):
            editions.check(self.root, 'test-1')

    def test_unlisted_bytecode_is_not_part_of_a_frozen_edition(self):
        target = editions.freeze(self.root, 'cache-check')
        cache = target / 'inputs/tools/__pycache__/content.cpython-313.pyc'
        cache.parent.mkdir()
        cache.write_bytes(b'unlisted cached implementation')
        with self.assertRaisesRegex(ValueError, 'inventory changed'):
            editions.build(self.root, 'cache-check', ['html'])
        self.assertFalse((target / 'outputs').exists())

    def test_duplicate_or_mutated_edition_is_rejected(self):
        with self.assertRaises(ValueError):
            editions.freeze(self.root, '../outside')
        target = editions.freeze(self.root, 'test-1')
        with self.assertRaises(FileExistsError):
            editions.freeze(self.root, 'test-1')
        (target / 'inputs/guides/handbook.md').write_text('changed after freeze')
        with self.assertRaisesRegex(ValueError, 'frozen input changed'):
            editions.build(self.root, 'test-1', ['md'])
        self.assertFalse((target / 'outputs').exists())


if __name__ == '__main__':
    unittest.main()
