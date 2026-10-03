"""Publication isolation, family selection and structure, using the real manuscripts."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from urllib.parse import unquote

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import content
import editions
import publications as pub


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('catalog', 'guides', 'comparisons', 'services', 'use-cases', 'reference',
                     'reports', 'examples', 'practice', 'diagrams', 'assets', 'styles', 'docs',
                     'templates', 'tools'):
            shutil.copytree(ROOT / name, self.root / name)
        for name in ('package.json', 'package-lock.json', 'requirements-render.txt'):
            shutil.copyfile(ROOT / name, self.root / name)

    # --- family structure and stable IDs -----------------------------------

    def test_publications_catalog_owns_three_families_and_product_rows(self):
        data = pub.load(self.root)
        self.assertEqual([f['id'] for f in pub.families(data)], ['launches', 'handbook', 'comparison'])
        self.assertEqual(pub.default_family(data)['id'], 'launches')
        handbook = pub.family(data, 'handbook')
        rows = pub.product_rows(handbook)
        self.assertEqual(len(rows), 8)
        for row in rows:
            self.assertIn(row['chapter'], pub.chapter_config(handbook))

    def test_chapter_ids_come_from_markers_not_positions(self):
        collection = pub.Collection(self.root, pub.load(self.root))
        handbook = collection.family('handbook')
        ids = [c['id'] for c in collection.chapters(handbook)]
        self.assertEqual(ids, ['start', 'routes', 'first-worker', 'access', 'content', 'jobs', 'retrieval',
                               'models', 'workspace', 'release', 'observability', 'economics', 'recovery',
                               'edition-notes'])
        # Reordering the visible number must not change the stable IDs.
        text = collection.text(pub.source_entry(handbook))
        shuffled = text.replace('## 01 /', '## 99 /', 1)
        plan = pub.parse_chapters(shuffled, pub.chapter_config(handbook))
        self.assertEqual([c['id'] for c in plan], ids)
        self.assertEqual(plan[0]['number'], '99')

    def test_missing_marker_falls_back_to_slug_and_empty_type(self):
        text = '## 03 / 一个没有标记的新章\n\n正文\n'
        chapters = pub.parse_chapters(text, {'known': 'TYPE'})
        self.assertEqual(chapters[0]['id'], pub.slug('一个没有标记的新章'))
        self.assertEqual(chapters[0]['type'], '')
        self.assertEqual(chapters[0]['number'], '03')

    def test_legacy_anchors_recorded_for_renamed_chapters(self):
        handbook = pub.family(pub.load(self.root), 'handbook')
        aliases = handbook.get('legacy_anchors', {})
        self.assertEqual(aliases.get('workspace'), '09--给机一间临时工作室')
        self.assertEqual(aliases.get('observability'), '11--留下够用的记录')

    def test_report_identity_reads_frontmatter_without_yaml(self):
        text = (self.root / 'reports/2026-10-03.md').read_text()
        ident = pub.report_identity(text, 'report.2026-10-03')
        self.assertIn('2026-10-03', ident['date'])
        self.assertFalse(ident['token'].startswith('faye'))

    # --- freeze scoping -----------------------------------------------------

    def test_family_freeze_reads_only_its_own_reading_closure(self):
        target = editions.freeze(self.root, 'scope', 'comparison')
        manifest = json.loads((target / 'edition.json').read_text())
        digests = manifest['input_digests']
        self.assertEqual(manifest['family'], 'comparison')
        self.assertIn('comparisons/clef-vs-jev.md', digests)
        # Unrelated manuscripts and maintenance docs are not packaged.
        for absent in ('guides/handbook.md', 'reports/2026-10-03.md', 'reports/2026-10-02.md',
                       'docs/lifecycle.md', 'docs/provenance.md', 'practice/private-reader.md'):
            self.assertNotIn(absent, digests)
        # Shared material and the renderer travel with every family.
        for present in ('tools/render.py', 'tools/publications.py', 'catalog/publications.json',
                        'docs/glossary.md', 'styles/report.css'):
            self.assertIn(present, digests)

    def test_handbook_freeze_covers_practice_figures_and_linked_example(self):
        target = editions.freeze(self.root, 'practice-fig', 'handbook')
        digests = json.loads((target / 'edition.json').read_text())['input_digests']
        for present in ('practice/private-reader.md', 'practice/protected-status.md',
                        'assets/two-routes.svg', 'examples/reading-shelf/README.md',
                        'examples/reading-shelf/index.html', 'examples/reading-shelf/materials/welcome.md'):
            self.assertIn(present, digests)
        # A report the handbook explicitly links is part of its closure; an unlinked
        # maintenance document is not.
        self.assertIn('reports/2026-10-03.md', digests)
        self.assertNotIn('docs/lifecycle.md', digests)
        self.assertNotIn('docs/provenance.md', digests)

    def test_offline_reading_has_no_file_uri_or_remote_asset(self):
        editions.freeze(self.root, 'offline', 'handbook')
        output = editions.build(self.root, 'offline', ['html'])
        html = next(output.glob('*.html')).read_text()
        soup = BeautifulSoup(html, 'html.parser')
        self.assertTrue(soup.select('figure.figure'))
        self.assertFalse([a for a in soup.select('a[href]') if a['href'].startswith('file:')])
        self.assertFalse([n for n in soup.select('[src]') if n['src'].startswith(('http://', 'https://'))])

    # --- build identity, report adaptivity, tamper -------------------------

    def test_report_stem_and_date_come_from_identity_not_renderer(self):
        editions.freeze(self.root, 'report-a', 'launches')
        output = editions.build(self.root, 'report-a', ['md'])
        produced = {p.name for p in output.iterdir()}
        self.assertTrue(any('2026-10-03' in name for name in produced), produced)

    def test_swapping_report_entry_needs_no_renderer_change(self):
        rel = 'reports/2026-12-31.md'
        text = (self.root / 'reports/2026-10-03.md').read_text().replace('2026-10-03', '2026-12-31')
        (self.root / rel).write_text(text)
        catalog = json.loads((self.root / 'catalog/entries.json').read_text())
        next(e for e in catalog['entries'] if e['id'] == 'report.2026-10-03').update(
            id='report.2026-12-31', path=rel)
        (self.root / 'catalog/entries.json').write_text(json.dumps(catalog, ensure_ascii=False))
        data = json.loads((self.root / 'catalog/publications.json').read_text())
        next(f for f in data['families'] if f['id'] == 'launches')['source_entry'] = 'report.2026-12-31'
        (self.root / 'catalog/publications.json').write_text(json.dumps(data, ensure_ascii=False))
        editions.freeze(self.root, 'report-b', 'launches')
        output = editions.build(self.root, 'report-b', ['md'])
        produced = {p.name for p in output.iterdir()}
        self.assertTrue(any('2026-12-31' in name for name in produced), produced)
        self.assertNotIn('cf-cloudflare-新发布观察-2026-10-03.md', produced)

    def test_frozen_renderer_is_used_not_the_live_tree(self):
        target = editions.freeze(self.root, 'isolated', 'handbook')
        included = editions.included(self.root, pub.family(pub.load(self.root), 'handbook'))
        before = {p.relative_to(self.root): p.read_bytes() for p in included if p.suffix == '.md'}
        (self.root / 'tools/render.py').write_text('raise RuntimeError("live renderer was used")')
        (self.root / 'styles/report.css').write_text('LIVE_STYLE_SENTINEL')
        output = editions.build(self.root, 'isolated', ['md', 'html'])
        self.assertNotIn('LIVE_STYLE_SENTINEL', next(output.glob('*.html')).read_text())
        for relative, value in before.items():
            self.assertEqual((target / 'inputs' / relative).read_bytes(), value)
            self.assertEqual((self.root / relative).read_bytes(), value)

    def test_duplicate_or_mutated_edition_is_rejected(self):
        with self.assertRaises(ValueError):
            editions.freeze(self.root, '../outside')
        target = editions.freeze(self.root, 'dup', 'comparison')
        with self.assertRaises(FileExistsError):
            editions.freeze(self.root, 'dup', 'comparison')
        (target / 'inputs/comparisons/clef-vs-jev.md').write_text('changed after freeze')
        with self.assertRaisesRegex(ValueError, 'frozen input changed'):
            editions.build(self.root, 'dup', ['md'])
        self.assertFalse((target / 'outputs').exists())

    def test_unlisted_bytecode_is_not_part_of_a_frozen_edition(self):
        target = editions.freeze(self.root, 'cache-check', 'comparison')
        cache = target / 'inputs/tools/__pycache__/content.cpython-313.pyc'
        cache.parent.mkdir()
        cache.write_bytes(b'unlisted cached implementation')
        with self.assertRaisesRegex(ValueError, 'inventory changed'):
            editions.build(self.root, 'cache-check', ['md'])
        self.assertFalse((target / 'outputs').exists())

    def test_unknown_family_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unknown publication family'):
            editions.freeze(self.root, 'nofam', 'nonexistent')

    # --- historical report stays frozen ------------------------------------

    def test_live_catalog_edits_do_not_rewrite_history(self):
        report = (self.root / 'reports/2026-10-02.md').read_bytes()
        sources = self.root / 'catalog/sources.json'
        data = json.loads(sources.read_text())
        # Mutate a source actually cited by the selected report, so the HTML
        # bibliography cannot silently replace the report's own definition.
        next(row for row in data if row['id'] == 'S98').update(
            title='LIVE_SOURCE_SENTINEL', url='https://example.invalid/changed')
        sources.write_text(json.dumps(data))
        content.sync(self.root, check=False)
        editions.freeze(self.root, 'hist', 'launches')
        output = editions.build(self.root, 'hist', ['md', 'html'])
        self.assertEqual(report, (self.root / 'reports/2026-10-02.md').read_bytes())
        self.assertNotIn('LIVE_SOURCE_SENTINEL', next(output.glob('cf-cloudflare*.html')).read_text())

    def test_glossary_is_frozen_and_embedded_in_portable_outputs(self):
        target = editions.freeze(self.root, 'glossary-test', 'handbook')
        self.assertTrue((target / 'inputs/docs/glossary.md').is_file())
        (self.root / 'docs/glossary.md').write_text('LIVE_GLOSSARY_SENTINEL')
        output = editions.build(self.root, 'glossary-test', ['md', 'html'])
        html = next(output.glob('*.html')).read_text()
        soup = BeautifulSoup(html, 'html.parser')
        links = [unquote(a['href'])[1:] for a in soup.select('a[href^="#glossary-"]')]
        self.assertIn('glossary-binding--资源绑定', links)
        for ident in links:
            self.assertIsNotNone(soup.find(id=ident), ident)
        self.assertIn('它决定程序能访问什么资源', html)
        self.assertNotIn('LIVE_GLOSSARY_SENTINEL', html)


    def test_unrelated_fact_drift_does_not_block_comparison_freeze(self):
        guide = self.root / 'guides/handbook.md'
        guide.write_text(guide.read_text().replace('200,000 events', 'DRIFTED EVENTS'))
        target = editions.freeze(self.root, 'independent-comparison', 'comparison')
        self.assertNotIn('guides/handbook.md', json.loads((target / 'edition.json').read_text())['input_digests'])
        with self.assertRaisesRegex(ValueError, 'fact blocks have drifted'):
            editions.freeze(self.root, 'drifted-handbook', 'handbook')

    def test_cli_build_uses_frozen_selection_after_live_config_is_removed(self):
        import subprocess
        target = editions.freeze(self.root, 'cli-isolated', 'comparison')
        (self.root / 'catalog/publications.json').unlink()
        result = subprocess.run([sys.executable, str(self.root / 'tools/editions.py'), '--root', str(self.root),
                                 'build', 'cli-isolated', '--formats', 'md'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(list((target / 'outputs').glob('*.md'))), 1)

    def test_latest_cannot_point_to_a_candidate_or_unknown_release(self):
        path = self.root / 'catalog/publication-releases.json'
        data = json.loads(path.read_text())
        data['latest'] = {'handbook': 'not-reviewed'}
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'latest must point'):
            pub.releases(self.root)
        data['latest'] = {}
        data['releases'] = [{'id': 'candidate', 'family': 'handbook', 'state': 'local-candidate'}]
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'reviewed, distributed'):
            pub.releases(self.root)


if __name__ == '__main__':
    unittest.main()
