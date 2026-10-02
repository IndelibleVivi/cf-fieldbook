"""Reading-site contract: usable public links and no withdrawn redistribution."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_site


class ReadingSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = (Path(cls.temp.name) / 'fieldbook').resolve()
        cls.root.mkdir()
        # Only public build inputs are copied; no working notes or environment.
        for directory in ('catalog', 'services', 'comparisons', 'use-cases', 'guides',
                          'reference', 'reports', 'examples', 'diagrams', 'assets', 'styles', 'templates'):
            shutil.copytree(ROOT / directory, cls.root / directory)
        for path in build_site.PUBLIC_DOCS:
            if (ROOT / path).is_file():
                destination = cls.root / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / path, destination)
        cls.output = cls.root / '.build/site'
        cls.before = {p.relative_to(cls.root): p.read_bytes() for p in cls.root.rglob('*') if p.is_file()}
        cls.manifest = build_site.build_site(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_build_leaves_editing_sources_unchanged(self):
        for path, value in self.before.items():
            self.assertEqual((self.root / path).read_bytes(), value, str(path))

    def test_home_has_three_real_reading_paths(self):
        soup = BeautifulSoup((self.output / 'index.html').read_text(), 'html.parser')
        self.assertEqual([a['href'] for a in soup.select('.path')], [
            'guides/handbook.html', 'services/decision-models.html', 'reports/2026-10-02.html'])
        for path in ('reference/implementation.html', 'examples/job-state/README.html',
                     'examples/health-worker/README.html', 'examples/decision-routing/README.html', 'diagrams/README.html'):
            self.assertTrue((self.output / path).is_file(), path)
        diagrams = BeautifulSoup((self.output / 'diagrams/README.html').read_text(), 'html.parser')
        self.assertEqual(len(diagrams.select('img.technical-diagram')), 5)

    def test_all_generated_local_links_assets_and_anchors_exist(self):
        for page in self.output.rglob('*.html'):
            soup = BeautifulSoup(page.read_text(), 'html.parser')
            for node in soup.find_all(['a', 'img', 'script', 'link']):
                href = node.get('href', node.get('src', ''))
                if not href:
                    continue
                parsed = urlsplit(href)
                if parsed.scheme or parsed.netloc:
                    continue
                target = (page.parent / unquote(parsed.path)).resolve() if parsed.path else page
                self.assertTrue(target.is_relative_to(self.output), f'{page}: {href}')
                self.assertTrue(target.is_file(), f'{page}: {href}')
                if parsed.fragment and target.suffix == '.html':
                    other = soup if target == page else BeautifulSoup(target.read_text(), 'html.parser')
                    self.assertIsNotNone(other.find(id=unquote(parsed.fragment)), f'{page}: {href}')

    def test_markdown_downloads_have_public_local_link_targets(self):
        md = MarkdownIt('commonmark').enable('table')
        for path in self.manifest['pages']:
            download = self.output / path
            self.assertTrue(download.is_file())
            for token in md.parse(download.read_text()):
                for child in token.children or []:
                    href = child.attrGet('href') if child.type == 'link_open' else child.attrGet('src') if child.type == 'image' else None
                    if not href:
                        continue
                    parsed = urlsplit(href)
                    if parsed.scheme or not parsed.path:
                        continue
                    self.assertTrue((download.parent / unquote(parsed.path)).is_file(), f'{download}: {href}')

    def test_sources_and_report_explain_inherited_evidence(self):
        soup = BeautifulSoup((self.output / 'reports/2026-10-02.html').read_text(), 'html.parser')
        note = soup.select_one('.evidence-note').get_text()
        self.assertIn('历史报告', note)
        self.assertIn('2026-10-02', note)
        self.assertIn('没有重新核验', note)
        sources = BeautifulSoup((self.output / 'sources.html').read_text(), 'html.parser')
        self.assertIsNotNone(sources.find(id='S81'))
        self.assertIn('full_page_fetch_failed', sources.find(id='S81').get_text())

    def test_distribution_is_an_allowlist_not_a_repo_copy(self):
        for path in ('editorial', '.git', '.venv', 'tools', 'tests', 'dist', 'AGENTS.md', 'docs/handoff.md'):
            self.assertFalse((self.output / path).exists(), path)
        for script in self.output.rglob('*.html'):
            soup = BeautifulSoup(script.read_text(), 'html.parser')
            self.assertFalse(any(urlsplit(n.get('src', '')).scheme or urlsplit(n.get('src', '')).netloc for n in soup.find_all(['script', 'img'])))

    def test_rebuild_removes_withdrawn_text_download_and_executable_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'fieldbook'
            shutil.copytree(self.root, root, ignore=shutil.ignore_patterns('.build'))
            output = root / '.build/site'
            build_site.build_site(root)
            self.assertTrue((output / 'examples/health-worker/index.mjs').exists())
            catalog_path = root / 'catalog/entries.json'
            catalog = json.loads(catalog_path.read_text())
            entry = next(e for e in catalog['entries'] if e['id'] == 'example.health-worker')
            entry['status'] = 'withdrawn'
            catalog_path.write_text(json.dumps(catalog, ensure_ascii=False))
            (root / entry['path']).write_text('# Secret withdrawn content\n\nNEVER_REDISTRIBUTE_THIS_SENTINEL\n')
            build_site.build_site(root)
            self.assertFalse((output / 'examples/health-worker/index.mjs').exists())
            self.assertFalse((output / 'examples/health-worker/README.md').exists())
            self.assertFalse((output / 'examples/health-worker/example.meta.json').exists())
            stub = (output / 'examples/health-worker/README.html').read_text()
            self.assertIn('已撤下', stub)
            for p in output.rglob('*'):
                if p.is_file() and p.suffix in {'.html', '.md', '.json'}:
                    self.assertNotIn('NEVER_REDISTRIBUTE_THIS_SENTINEL', p.read_text(), str(p))

    def test_bare_sources_resolve_but_report_source_urls_remain_frozen(self):
        site = build_site.Site(self.root, self.root / '.build/source-test')
        path = 'services/decision-models.md'
        site.texts[path] = '# A service\n\nA source [S17].\n'
        rendered, _, _ = site.render_content(path)
        soup = BeautifulSoup(rendered, 'html.parser')
        self.assertEqual(soup.a['href'], '../sources.html#S17')
        report = 'reports/2026-10-02.md'
        site.texts[report] = '# A frozen report\n\nHistorical source [S17].\n\n[S17]: https://example.invalid/historical-original\n'
        rendered, _, _ = site.render_content(report)
        soup = BeautifulSoup(rendered, 'html.parser')
        self.assertEqual(soup.a['href'], 'https://example.invalid/historical-original')

    def test_archived_example_has_no_execution_attachment(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'fieldbook'
            shutil.copytree(self.root, root, ignore=shutil.ignore_patterns('.build'))
            catalog_path = root / 'catalog/entries.json'
            catalog = json.loads(catalog_path.read_text())
            entry = next(e for e in catalog['entries'] if e['id'] == 'example.job-state')
            entry['status'] = 'archived'
            catalog_path.write_text(json.dumps(catalog, ensure_ascii=False))
            build_site.build_site(root)
            output = root / '.build/site'
            self.assertTrue((output / 'examples/job-state/README.html').exists())
            self.assertFalse((output / 'examples/job-state/model.py').exists())
            self.assertFalse((output / 'examples/job-state/example.meta.json').exists())


if __name__ == '__main__':
    unittest.main()
