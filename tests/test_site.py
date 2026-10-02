"""Reading-site contract: usable public links and no withdrawn redistribution."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

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
        for path in (*build_site.PUBLIC_DOCS, 'LICENSE'):
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

    def test_download_bundle_keeps_software_and_content_license_notices(self):
        self.assertEqual((self.output / 'LICENSE').read_bytes(), (ROOT / 'LICENSE').read_bytes())
        for name in ('LICENSE-STATUS.md', 'LICENSE-DOCUMENTATION.md'):
            self.assertTrue((self.output / name).is_file())
        self.assertIn('SUL-1.0', (self.output / 'LICENSE-STATUS.html').read_text())
        self.assertIn('CC BY-NC-SA 4.0', (self.output / 'LICENSE-DOCUMENTATION.html').read_text())

    def test_home_has_three_real_reading_paths(self):
        soup = BeautifulSoup((self.output / 'index.html').read_text(), 'html.parser')
        self.assertEqual([a['href'] for a in soup.select('.path')], [
            'guides/handbook.html', 'products.html', 'reports/2026-10-02.html'])
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
                if parsed.path.startswith('/'):
                    target = (self.output / unquote(parsed.path).lstrip('/')).resolve()
                else:
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
        self.assertIn('继承 r3', note)
        self.assertIn('不等于账户或云端实测', note)
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
            build_site.build_site(root, base_url='https://reader.example/project/')
            self.assertFalse((output / 'examples/health-worker/index.mjs').exists())
            self.assertFalse((output / 'examples/health-worker/README.md').exists())
            self.assertFalse((output / 'examples/health-worker/example.meta.json').exists())
            stub = (output / 'examples/health-worker/README.html').read_text()
            self.assertIn('已撤下', stub)
            self.assertEqual(BeautifulSoup(stub, 'html.parser').find('meta', attrs={'name': 'robots'})['content'], 'noindex')
            self.assertNotIn('examples/health-worker/README.html', (output / 'sitemap.xml').read_text())
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

    def test_public_copy_and_product_paths_have_reader_purpose(self):
        soup = BeautifulSoup((self.output / 'index.html').read_text(), 'html.parser')
        copy = soup.get_text()
        self.assertIn('Cloudflare® 服务', copy)
        self.assertNotIn('本地阅读候选', copy)
        self.assertNotIn('本轮建站', copy)
        self.assertIn('非 Cloudflare 官方出版物', copy)
        self.assertIn('Cloudflare, Inc.', copy)
        products = BeautifulSoup((self.output / 'products.html').read_text(), 'html.parser')
        self.assertEqual(len(products.select('.product-reading')), 8)
        for name in ('Workers', 'Access', 'Tunnel', 'D1', 'R2', 'Queues', 'Workflows',
                     'AI Search', 'Vectorize', 'Workers AI', 'AI Gateway', 'Containers', 'Sandbox', 'Workers Issues'):
            self.assertIn(name, products.get_text())
        self.assertTrue(all('#' in link['href'] for link in products.select('.product-body h2 a')))

    def test_preview_does_not_invent_a_public_origin(self):
        page = BeautifulSoup((self.output / 'index.html').read_text(), 'html.parser')
        self.assertIsNone(page.find('link', rel='canonical'))
        self.assertEqual(page.find('meta', attrs={'name': 'robots'})['content'], 'noindex')
        self.assertIn('Disallow: /', (self.output / 'robots.txt').read_text())
        self.assertEqual(len(ElementTree.parse(self.output / 'sitemap.xml').getroot()), 0)
        self.assertTrue((self.output / 'assets/motifs/favicon.svg').is_file())

    def test_canonical_sitemap_and_404_support_root_and_project_paths(self):
        for public_url, prefix in [('https://reader.example', '/'), ('https://reader.example/project', '/project/')]:
            with self.subTest(public_url=public_url):
                output = self.root / '.build/public-metadata'
                manifest = build_site.build_site(self.root, output, public_url)
                base = public_url + '/'
                self.assertEqual(manifest['base_url'], base)
                homepage = BeautifulSoup((output / 'index.html').read_text(), 'html.parser')
                self.assertEqual(homepage.find('link', rel='canonical')['href'], base)
                self.assertIsNone(homepage.find('meta', attrs={'name': 'robots'}))
                article = BeautifulSoup((output / 'guides/handbook.html').read_text(), 'html.parser')
                self.assertEqual(article.find('link', rel='canonical')['href'], base + 'guides/handbook.html')
                expected = {base + ('' if page == 'index.html' else page) for page in manifest['html_pages'] if page != '404.html'}
                actual = {node.text for node in ElementTree.parse(output / 'sitemap.xml').getroot().iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')}
                self.assertEqual(actual, expected)
                self.assertIn('Sitemap: ' + base + 'sitemap.xml', (output / 'robots.txt').read_text())
                missing = BeautifulSoup((output / '404.html').read_text(), 'html.parser')
                self.assertEqual(missing.find('meta', attrs={'name': 'robots'})['content'], 'noindex')
                self.assertIsNone(missing.find('link', rel='canonical'))
                self.assertEqual(missing.find('link', rel='stylesheet')['href'], prefix + 'styles/site.css')
                self.assertEqual(missing.select_one('.wordmark')['href'], prefix + 'index.html')
                self.assertEqual(missing.select_one('.not-found-actions a')['href'], prefix + 'directory.html')

    def test_base_url_requires_an_unambiguous_public_site_directory(self):
        for value in ('/project/', 'file:///project/', 'https://reader.example/?q=1', 'https://reader.example/#fragment', 'https://user:password@reader.example/'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_site.normalize_base_url(value)

    def test_product_index_never_reads_inactive_handbook_chapters(self):
        for status in ('draft', 'withdrawn', 'archived', 'superseded'):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / 'fieldbook'
                shutil.copytree(self.root, root, ignore=shutil.ignore_patterns('.build'))
                catalog_path = root / 'catalog/entries.json'
                catalog = json.loads(catalog_path.read_text())
                entry = next(e for e in catalog['entries'] if e['id'] == 'guide.handbook')
                entry['status'] = status
                catalog_path.write_text(json.dumps(catalog, ensure_ascii=False))
                if status in {'draft', 'withdrawn'}:
                    (root / entry['path']).write_text('# PRIVATE_HANDBOOK_SENTINEL\n\nNever distribute this title or summary.\n')
                output = root / '.build/site'
                build_site.build_site(root, base_url='https://reader.example/project/')
                products = BeautifulSoup((output / 'products.html').read_text(), 'html.parser')
                self.assertEqual(len(products.select('.product-reading')), 0)
                self.assertIn('暂时不可用', products.get_text())
                homepage = BeautifulSoup((output / 'index.html').read_text(), 'html.parser')
                expected = 'guides/handbook.html' if status == 'withdrawn' else 'directory.html'
                self.assertEqual(homepage.select_one('.path')['href'], expected)
                self.assertEqual(homepage.select_one('.global-nav a')['href'], expected)
                for page in output.rglob('*.html'):
                    soup = BeautifulSoup(page.read_text(), 'html.parser')
                    for node in soup.find_all('a'):
                        url = urlsplit(node.get('href', ''))
                        if not url.scheme and url.path and not url.path.startswith('/'):
                            self.assertTrue((page.parent / unquote(url.path)).is_file(), f'{status}: {page}: {url.path}')
                if status in {'draft', 'withdrawn'}:
                    self.assertFalse((output / entry['path']).exists())
                    for p in output.rglob('*'):
                        if p.is_file() and p.suffix in {'.html', '.md', '.json'}:
                            self.assertNotIn('PRIVATE_HANDBOOK_SENTINEL', p.read_text(), str(p))


if __name__ == '__main__':
    unittest.main()
