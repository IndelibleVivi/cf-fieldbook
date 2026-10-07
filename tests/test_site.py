"""Reading-site contract: usable public links and no withdrawn redistribution."""
from __future__ import annotations

import json
import re
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
                          'reference', 'reports', 'examples', 'practice', 'diagrams', 'assets', 'styles', 'templates'):
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

    def test_api_guides_task_sheet_and_current_example_downloads_are_selected(self):
        for path in ('reference/api-maintenance', 'use-cases/project-context', 'templates/project-context-task'):
            self.assertTrue((self.output / (path + '.html')).is_file())
            self.assertTrue((self.output / (path + '.md')).is_file())
        for filename in ('model.py', 'demo.py', 'example.meta.json'):
            self.assertEqual((self.output / 'examples/api-operations' / filename).read_bytes(),
                             (ROOT / 'examples/api-operations' / filename).read_bytes())
        home = BeautifulSoup((self.output / 'index.html').read_text(), 'html.parser')
        for href in ('reference/api-maintenance.html', 'use-cases/project-context.html'):
            self.assertIsNotNone(home.find('a', href=href))
        sources = BeautifulSoup((self.output / 'sources.html').read_text(), 'html.parser')
        self.assertIsNotNone(sources.find(id='S119'))

    def test_api_operation_withdrawal_removes_code_downloads_and_search_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'fieldbook'
            shutil.copytree(self.root, root, ignore=shutil.ignore_patterns('.build'))
            build_site.build_site(root)
            output = root / '.build/site'
            self.assertTrue((output / 'examples/api-operations/model.py').is_file())
            catalog_path = root / 'catalog/entries.json'
            catalog = json.loads(catalog_path.read_text())
            entry = next(e for e in catalog['entries'] if e['id'] == 'example.api-operations')
            entry['status'] = 'withdrawn'
            catalog_path.write_text(json.dumps(catalog, ensure_ascii=False))
            (root / entry['path']).write_text('# Withdrawn\n\nAPI_WITHDRAWAL_SENTINEL\n')
            build_site.build_site(root)
            for filename in ('model.py', 'demo.py', 'example.meta.json', 'README.md'):
                self.assertFalse((output / 'examples/api-operations' / filename).exists())
            self.assertNotIn('API_WITHDRAWAL_SENTINEL', (output / 'search-index.json').read_text())
            self.assertIn('已撤下', (output / 'examples/api-operations/README.html').read_text())

    def test_download_bundle_keeps_software_and_content_license_notices(self):
        self.assertEqual((self.output / 'LICENSE').read_bytes(), (ROOT / 'LICENSE').read_bytes())
        for name in ('LICENSE-STATUS.md', 'LICENSE-DOCUMENTATION.md'):
            self.assertTrue((self.output / name).is_file())
        self.assertIn('SUL-1.0', (self.output / 'LICENSE-STATUS.html').read_text())
        self.assertIn('CC BY-NC-SA 4.0', (self.output / 'LICENSE-DOCUMENTATION.html').read_text())

    def test_home_has_three_real_reading_paths(self):
        soup = BeautifulSoup((self.output / 'index.html').read_text(), 'html.parser')
        # The home page names the three works: handbook, Clef/Jev comparison, current report.
        self.assertEqual([a['href'] for a in soup.select('.path')], [
            'guides/handbook.html', 'comparisons/clef-vs-jev.html', 'reports/2026-10-first-release.html'])
        for path in ('reference/implementation.html', 'examples/job-state/README.html',
                     'examples/health-worker/README.html', 'examples/decision-routing/README.html',
                     'examples/reading-shelf/README.html', 'diagrams/README.html'):
            self.assertTrue((self.output / path).is_file(), path)
        diagrams = BeautifulSoup((self.output / 'diagrams/README.html').read_text(), 'html.parser')
        self.assertEqual(len(diagrams.select('img.technical-diagram')), 6)
        self.assertIsNotNone(diagrams.find(id='diagram-reading-shelf'))

    def test_real_practice_is_discoverable_without_claiming_a_new_cloud_run(self):
        home = BeautifulSoup((self.output / 'index.html').read_text(), 'html.parser')
        directory = BeautifulSoup((self.output / 'directory.html').read_text(), 'html.parser')
        index = json.loads((self.output / 'search-index.json').read_text())
        routes = {f'practice/{name}.html' for name in ('private-reader', 'access-pwa', 'protected-status')}
        self.assertEqual({a['href'] for a in home.select('.practice-card')}, routes)
        for route in routes:
            self.assertIsNotNone(directory.find('a', href=route))
            self.assertTrue(any(item['url'].split('#')[0] == route and item['kind'] == '实践' for item in index))
            page = BeautifulSoup((self.output / route).read_text(), 'html.parser')
            self.assertIn('未进行新的云端实验', page.select_one('.evidence-note').get_text())
            self.assertTrue((self.output / Path(route).with_suffix('.md')).is_file())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'fieldbook'
            shutil.copytree(self.root, root, ignore=shutil.ignore_patterns('.build'))
            catalog_path = root / 'catalog/entries.json'
            catalog = json.loads(catalog_path.read_text())
            entry = next(e for e in catalog['entries'] if e['id'] == 'practice.access-pwa')
            entry['status'] = 'withdrawn'
            catalog_path.write_text(json.dumps(catalog, ensure_ascii=False))
            (root / entry['path']).write_text('# WITHDRAWN_PRACTICE_SENTINEL')
            build_site.build_site(root)
            output = root / '.build/site'
            self.assertFalse((output / 'practice/access-pwa.md').exists())
            self.assertNotIn('practice/access-pwa.html', (output / 'index.html').read_text())
            self.assertNotIn('WITHDRAWN_PRACTICE_SENTINEL', (output / 'search-index.json').read_text())

    def test_all_generated_local_links_assets_and_anchors_exist(self):
        for page in self.output.rglob('*.html'):
            soup = BeautifulSoup(page.read_text(), 'html.parser')
            for node in soup.find_all(['a', 'img', 'script', 'link', 'source']):
                href = node.get('href', node.get('src', node.get('srcset', '')))
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

    def test_real_authoring_comments_do_not_leak_into_body_or_search(self):
        index = json.loads((self.output / 'search-index.json').read_text())
        for path in ('guides/handbook.html', 'reports/2026-10-02.html',
                     'reports/2026-10-first-release.html'):
            soup = BeautifulSoup((self.output / path).read_text(), 'html.parser')
            for marker in ('<!-- facts:', '<!-- /facts -->', '<!-- SOURCES -->', '<!-- figure:'):
                self.assertNotIn(marker, soup.select_one('.prose').get_text())
                for item in index:
                    if item['url'].split('#')[0] == path:
                        self.assertNotIn(marker, item['text'])
        # Presentation filtering does not alter either maintained MD downloads or frozen reports.
        for path in ('guides/handbook.md', 'reports/2026-10-02.md'):
            self.assertIn('<!-- SOURCES -->', (self.output / path).read_text())

    def test_comment_filter_preserves_code_and_never_enables_raw_html(self):
        site = build_site.Site(self.root, self.root / '.build/comment-test')
        site.texts['README.md'] = '''# Markup

<!-- facts: cf-routes -->
Text <!-- hidden inline note --> stays.
<!-- /facts -->
<!-- SOURCES -->
<!-- multiline

authoring note -->

```html
<!-- facts: cf-routes -->
<!-- figure: workspace -->
<script>example()</script>
cat < input > output
```

    <!-- SOURCES -->
    echo a > result

`<!-- SOURCES -->` and `<value>`.

<script>alert(1)</script>
<aside>plain HTML example</aside>

<!-- figure: workspace -->
'''
        rendered, _, _ = site.render_content('README.md')
        soup = BeautifulSoup(rendered, 'html.parser')
        self.assertFalse(site.md.options['html'])
        self.assertFalse(soup.find_all(['script', 'aside']))
        code = [node.get_text() for node in soup.find_all('code')]
        self.assertTrue(any('<!-- figure: workspace -->' in text and 'cat < input > output' in text for text in code))
        self.assertTrue(any('<!-- SOURCES -->' in text and 'echo a > result' in text for text in code))
        self.assertIn('<!-- SOURCES -->', code)
        self.assertIn('<value>', code)
        for node in soup.find_all(['pre', 'code']):
            node.decompose()
        self.assertNotIn('<!--', soup.get_text())
        self.assertIn('Text  stays.', soup.get_text())
        self.assertIn('<script>alert(1)</script>', soup.get_text())
        self.assertIn('<aside>plain HTML example</aside>', soup.get_text())
        self.assertEqual(len(soup.find_all('img')), 1)
        self.assertEqual(soup.img['src'], 'assets/workspace.svg')

    def test_repository_banner_stays_in_readme_source_not_web_pages(self):
        banner = 'assets/motifs/repository-banner.svg'
        self.assertIn(banner, (self.root / 'README.md').read_text())
        self.assertIn(banner, (self.output / 'README.md').read_text())
        self.assertTrue((self.output / banner).is_file())
        download = BeautifulSoup(MarkdownIt().render((self.output / 'README.md').read_text()), 'html.parser')
        self.assertEqual(download.find('img', src=banner).parent['href'], build_site.PUBLIC_SITE_URL)
        for path in ('README.html', 'index.html'):
            self.assertNotIn(banner, (self.output / path).read_text())

    def test_shared_footer_owns_signature_and_opening_metadata_is_semantic(self):
        for path in ('guides/handbook.html', 'reports/2026-10-02.html',
                     'reports/2026-10-first-release.html'):
            soup = BeautifulSoup((self.output / path).read_text(), 'html.parser')
            self.assertEqual(soup.body.get_text().count('Faye & Cove'), 1)
            self.assertEqual(soup.select_one('.site-footer .signature').get_text(), 'made by Faye & Cove')
            self.assertIsNotNone(soup.select_one('.site-footer .link-legend'))
            self.assertFalse(soup.select('body > .reading-legend'))
            self.assertNotIn('Faye & Cove', soup.select_one('.article-header').get_text())
            self.assertEqual(len(soup.find_all('h1')), 1)
            self.assertNotIn('Faye & Cove', soup.select_one('.article-deck').get_text())
            self.assertTrue(soup.select_one('.edition-line').get_text().startswith('2026.10'))
            self.assertFalse(soup.select_one('.prose').find('p').strong)
            profile = soup.select_one('.site-footer a[href="https://github.com/IndelibleVivi"]')
            self.assertEqual(profile.get_text(), 'GitHub · IndelibleVivi')
            for link in soup.select('.prose a'):
                if re.fullmatch(r'S\d{2,3}', link.get_text()):
                    self.assertIn('source-ref', link.get('class', []))

    def test_signature_filter_retains_narrative_and_rights_statements(self):
        site = build_site.Site(self.root, self.root / '.build/signature-test')
        site.texts['README.md'] = '''# A title · Faye & Cove

Faye & Cove retain the copyright to these diagrams.

The phrase made by Faye & Cove identifies the authors; GitHub is a source host.

`made by Faye & Cove`

*made by Faye & Cove*

GitHub · [https://github.com/IndelibleVivi](https://github.com/IndelibleVivi)
'''
        rendered, _, _ = site.render_content('README.md')
        text = BeautifulSoup(rendered, 'html.parser').get_text()
        self.assertIn('Faye & Cove retain the copyright', text)
        self.assertIn('The phrase made by Faye & Cove', text)
        self.assertEqual(text.count('made by Faye & Cove'), 2)  # Narrative plus literal code.
        self.assertNotIn('https://github.com/IndelibleVivi', text)
        self.assertEqual(build_site.source_title(site.texts['README.md'], 'README.md'), 'A title')

    def test_numbered_chapter_markup_preserves_old_ids_and_search_labels(self):
        site = build_site.Site(self.root, self.root / '.build/heading-test')
        for path in ('guides/handbook.md', 'reports/2026-10-03.md'):
            page = str(Path(path).with_suffix('.html'))
            soup = BeautifulSoup((self.output / page).read_text(), 'html.parser')
            labels = re.findall(r'^## (\d{2} / .+)$', build_site.split_frontmatter(site.texts[path])[1], re.M)
            for label in labels:
                legacy = build_site.heading_id(label)
                # The stable chapter ID carries the markup; the legacy slug remains as
                # an alias anchor resolving to the same chapter.
                alias = soup.find(id=legacy)
                self.assertIsNotNone(alias, legacy)
                chapter = alias.find_parent('h2') if alias.name != 'h2' else alias
                self.assertIn('numbered-chapter', chapter['class'])
                self.assertEqual(chapter.select_one('.chapter-number').get_text(), label[:2])
                self.assertEqual(chapter.select_one('.chapter-separator').get_text(), ' / ')
                self.assertEqual(chapter.select_one('.chapter-title').get_text(), label[5:])
                toc = soup.select_one(f'.contents a[href="#{chapter["id"]}"]')
                self.assertEqual(toc.get_text(), label)
                self.assertEqual(toc.select_one('.toc-separator').get_text(), ' / ')
            for link in soup.select('.contents ol a'):
                self.assertIsNotNone(link.select_one('.toc-label'))
        index = json.loads((self.output / 'search-index.json').read_text())
        self.assertTrue(any(item['section'] == '08 / 模型、路由与三种缓存' for item in index))

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
        # The eight groups extend the existing purposes with current services and products.
        for name in ('Workers', 'Access', 'Tunnel', 'Protected Quick Tunnels', 'D1', 'R2', 'Queues',
                     'Workflows', 'Durable Objects', 'AI Search', 'Vectorize', 'Web Search API',
                     'Workers AI', 'AI Gateway', 'Agents', 'PiHarness', 'Containers', 'Sandbox',
                     'Cloudflare Traces', 'SQL API', 'MCP', 'Issues', 'Alerts'):
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

    def test_section_search_points_to_real_headings_and_omits_script_data(self):
        index = json.loads((self.output / 'search-index.json').read_text())
        self.assertGreater(len(index), len(self.manifest['pages']))
        for item in index:
            parsed = urlsplit(item['url'])
            page = BeautifulSoup((self.output / parsed.path).read_text(), 'html.parser')
            if parsed.fragment:
                heading = page.find(id=unquote(parsed.fragment))
                self.assertIsNotNone(heading, item['url'])
                self.assertIn(heading.name, ['h2', 'h3'])
            self.assertNotIn('"frames":', item['text'])
            self.assertNotIn(item['status'], ['draft', 'withdrawn'])

    def test_glossary_links_and_controlled_questions_are_progressive(self):
        soup = BeautifulSoup((self.output / 'guides/handbook.html').read_text(), 'html.parser')
        terms = json.loads(soup.find(id='term-data').string)
        # The in-place glossary covers every term the handbook links, at least the
        # original eight; the exact set follows the manuscript, not a fixed count.
        self.assertGreaterEqual(len(terms), 8)
        glossary = BeautifulSoup((self.output / 'docs/glossary.html').read_text(), 'html.parser')
        for anchor, term in terms.items():
            self.assertIsNotNone(glossary.find(id=anchor))
            self.assertTrue(term['definition'])
        for link in soup.select('a[data-term]'):
            self.assertTrue(link['href'].startswith('../docs/glossary.html#'))
            self.assertEqual(link['data-link-kind'], 'term')
            self.assertEqual(link['aria-describedby'], 'link-term')
        questions = soup.select('blockquote.understanding-question')
        self.assertEqual(len(questions), 3)
        for question in questions:
            self.assertIn('想一想：', question.find('p', recursive=False).get_text())
            self.assertIn('答案：', question.select_one('details.understanding-answer').get_text())
            self.assertFalse(question.details.has_attr('open'))
        self.assertFalse(soup.select_one('.evidence-note').has_attr('open'))

    def test_mobile_figures_and_link_destinations_are_explicit(self):
        soup = BeautifulSoup((self.output / 'guides/handbook.html').read_text(), 'html.parser')
        pictures = soup.select('picture.responsive-figure')
        self.assertEqual(len(pictures), 2)
        self.assertEqual({p.source['srcset'] for p in pictures}, {'../assets/two-routes-mobile.svg', '../assets/task-state-mobile.svg'})
        self.assertTrue(all(p.source['media'] == '(max-width: 1100px)' for p in pictures))
        for link in soup.select('a[data-link-kind]'):
            self.assertIsNotNone(soup.find(id=link['aria-describedby']))
        svg = soup.select_one('a[data-attachment-action=open]')
        self.assertEqual(svg['data-link-kind'], 'attachment')
        markdown = soup.select_one('.reader-tools a[download]')
        self.assertEqual(markdown['data-attachment-action'], 'download')
        readme = BeautifulSoup((self.output / 'README.html').read_text(), 'html.parser')
        self.assertTrue(readme.select('a[data-link-kind=repository]'))

    def test_safe_repo_links_are_real_without_general_path_fallback(self):
        site = build_site.Site(self.root, self.root / '.build/link-test')
        site.texts['README.md'] = '# Link test\n\n[Tool](tools/check.py) [Private](docs/private-note.md) [Code](examples/not-public/model.py)\n'
        rendered, _, _ = site.render_content('README.md')
        soup = BeautifulSoup(rendered, 'html.parser')
        self.assertEqual(soup.a['href'], build_site.REPOSITORY_URL + 'tools/check.py')
        self.assertEqual(len(soup.find_all('a')), 1)
        self.assertEqual(len(soup.select('span.repository-ref')), 2)

    def test_demo_is_current_only_and_rebuild_removes_frames_assets_and_links(self):
        self.assertIn('examples/job-state/demo.html', self.manifest['html_pages'])
        demo = BeautifulSoup((self.output / 'examples/job-state/demo.html').read_text(), 'html.parser')
        self.assertEqual(len(json.loads(demo.find(id='recovery-data').string)), 5)
        self.assertTrue(demo.find('script', src='../../styles/recovery.js'))
        for status in ('draft', 'withdrawn', 'archived', 'superseded'):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / 'fieldbook'
                shutil.copytree(self.root, root, ignore=shutil.ignore_patterns('.build'))
                output = root / '.build/site'
                build_site.build_site(root)
                catalog_path = root / 'catalog/entries.json'
                catalog = json.loads(catalog_path.read_text())
                next(e for e in catalog['entries'] if e['id'] == 'example.job-state')['status'] = status
                catalog_path.write_text(json.dumps(catalog, ensure_ascii=False))
                manifest = build_site.build_site(root, base_url='https://reader.example/project/')
                self.assertNotIn('examples/job-state/demo.html', manifest['html_pages'])
                for path in ('examples/job-state/demo.html', 'styles/recovery.css', 'styles/recovery.js'):
                    self.assertFalse((output / path).exists())
                for page in output.rglob('*.html'):
                    soup = BeautifulSoup(page.read_text(), 'html.parser')
                    self.assertIsNone(soup.find(id='recovery-data'))
                    self.assertFalse(any('examples/job-state/demo.html' in a.get('href', '') or a.get('href') == 'demo.html' for a in soup.find_all('a')), page)


    def test_version_pages_respect_withdrawn_and_draft_body_boundaries(self):
        for status in ('withdrawn', 'draft'):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / 'fieldbook'
                shutil.copytree(self.root, root, ignore=shutil.ignore_patterns('.build'))
                path = root / 'catalog/entries.json'
                data = json.loads(path.read_text())
                entry = next(e for e in data['entries'] if e['id'] == 'guide.handbook')
                entry['status'] = status
                path.write_text(json.dumps(data, ensure_ascii=False))
                (root / entry['path']).write_text('# PRIVATE_SENTINEL_TITLE\n\n## 01 / PRIVATE_SENTINEL_CHAPTER\nPRIVATE_SENTINEL_BODY')
                result = build_site.build_site(root, base_url=build_site.PUBLIC_SITE_URL)
                for page in result['html_pages']:
                    self.assertNotIn('PRIVATE_SENTINEL', (root / '.build/site' / page).read_text(), page)

    def test_article_metadata_and_reviewed_png_are_portable(self):
        with tempfile.TemporaryDirectory() as temp:
            output = self.root / '.build/social-check'
            build_site.build_site(self.root, output, build_site.PUBLIC_SITE_URL)
            for path, key in [('guides/handbook.html', 'handbook'), ('comparisons/clef-vs-jev.html', 'comparison'),
                              ('reports/2026-10-first-release.html', 'launches')]:
                soup = BeautifulSoup((output / path).read_text(), 'html.parser')
                self.assertIn(self.root.joinpath('assets/share/' + key + '.png').name, soup.select_one('meta[property="og:image"]')['content'])
                self.assertIn(build_site.PUBLIC_SITE_URL + path, soup.select_one('link[rel="canonical"]')['href'])
                self.assertEqual(len(soup.select('meta[name="twitter:description"]')), 1)
                self.assertEqual((output / ('assets/share/' + key + '.png')).read_bytes(),
                                 (ROOT / ('assets/share/' + key + '.png')).read_bytes())
            self.assertIn('2026-10-03', BeautifulSoup((output / 'guides/handbook.html').read_text(), 'html.parser').select_one('meta[name="description"]')['content'])


if __name__ == '__main__':
    unittest.main()
