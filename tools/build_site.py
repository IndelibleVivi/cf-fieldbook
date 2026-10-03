#!/usr/bin/env python3
"""Build the offline reading site from public Markdown and catalog, read-only.

No repository tree copy, remote fetch, source edits, cloud calls or deployment.
"""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re
import shutil
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from xml.etree import ElementTree

from bs4 import BeautifulSoup, NavigableString
from markdown_it import MarkdownIt
from markdown_it.token import Token
import yaml

from content import project_markdown
import publications as pub

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = (
    'README.md', 'CHANGELOG.md', 'SPEC.md', 'CONTRIBUTING.md', 'LICENSE-STATUS.md', 'LICENSE-DOCUMENTATION.md', 'docs/architecture.md',
    'docs/lifecycle.md', 'docs/publication.md', 'docs/content-design.md',
    'docs/migration-r3.md', 'docs/current-state.md', 'docs/reading-site.md', 'docs/provenance.md', 'docs/glossary.md', 'examples/README.md',
    'diagrams/README.md', 'templates/practice-example.md', 'templates/release-card.md', 'templates/job-recovery-task.md',
)
PUBLIC_REPOSITORY_PATHS = {
    'AGENTS.md', '.github/workflows/check.yml', 'requirements-render.txt', 'requirements-design.txt',
    'package.json', 'package-lock.json',
    *(f'tools/{name}.py' for name in ('build_site', 'content', 'editions', 'render', 'figures', 'fieldbook', 'check', 'render_diagrams', 'recovery_demo', 'publications', 'share_images')),
    *(f'tests/{name}.py' for name in ('test_examples', 'test_fieldbook', 'test_job_recovery', 'test_decision_example', 'test_site', 'test_publication')),
    'tests/site-search.test.cjs',
}
REPOSITORY_URL = 'https://github.com/IndelibleVivi/cf-fieldbook/blob/main/'
PUBLIC_SITE_URL = 'https://indeliblevivi.github.io/cf-fieldbook/'
SITE_ASSETS = {'styles/site.css', 'styles/site.js', 'styles/search.js', 'assets/motifs/cat-sunrise.svg',
               'assets/motifs/edge-route.svg', 'assets/motifs/reading-pages.svg', 'assets/motifs/field-notes.svg', 'assets/motifs/favicon.svg',
               'assets/motifs/weigh-routes.svg', 'assets/motifs/launch-window.svg', 'assets/motifs/task-loop.svg',
               'assets/motifs/ledger.svg', 'assets/motifs/colophon.svg',
               'assets/share/fieldbook.png', 'assets/share/handbook.png', 'assets/share/comparison.png', 'assets/share/launches.png',
               'assets/motifs/repository-banner.svg'}
READER_MOTIFS = {'service': 'edge-route', 'comparison': 'weigh-routes', 'use-case': 'launch-window',
                 'example': 'task-loop', 'reference': 'ledger', 'practice': 'field-notes', 'report': 'field-notes'}
LINK_LABELS = {'internal': '站内阅读', 'term': '词义，可就地展开或打开词表', 'repository': '本项目公开源码，前往 GitHub',
               'source': '外部来源，离开本站', 'attachment': '附件；下载或打开文件'}
READER_PREFIXES = {'services', 'comparisons', 'use-cases', 'guides', 'reference', 'reports', 'examples', 'practice'}
EXAMPLE_FILES = {
    'decision-routing': ('payloads.py', 'example.meta.json'),
    'health-worker': ('index.mjs', 'worker.test.mjs', 'wrangler.example.json', 'example.meta.json'),
    'job-state': ('model.py', 'demo.py', 'example.meta.json'),
    # A small offline reading shelf: three synthetic documents plus a static index.
    'reading-shelf': ('build.py', 'index.html', 'materials/welcome.md', 'materials/notes.md',
                      'materials/checklist.md', 'example.meta.json'),
}
KIND_LABELS = {'use-case': '用途', 'guide': '手册', 'service': '服务', 'comparison': '比较',
               'example': '例子', 'reference': '实施参考', 'report': '带日期报告', 'practice': '实践', 'doc': '资料维护'}
STATUS_LABELS = {'current': '当前资料', 'superseded': '已有替代', 'archived': '历史归档',
                 'withdrawn': '已撤下', 'draft': '草稿'}
FIGCAP = {
    'workspace': '文件系统可以复用；进程与任务状态另行接续。示意一种工作方式，不是自动合并。',
    'runtime-cost': '同一任务数与配置，条长按每次运行分钟数绘制；详细假设与来源见邻近正文。',
    'two-routes': '两种常见路线，不要求同时采用。Tunnel 不替原设备运行程序。',
    'task-state': '接收、执行与完成分开记录。示意主线；完整状态与失败分支见邻近正文。',
}
# Product reading paths, home entries and publication identity come from
# catalog/publications.json through the shared publications helper.


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def relative_url(page: str, target: str) -> str:
    return Path(os.path.relpath(target, Path(page).parent)).as_posix()


def normalize_base_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {'https', 'http'} or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError('--base-url must be an absolute HTTP(S) site directory URL without query or fragment')
    if parsed.username or parsed.password:
        raise ValueError('--base-url must not contain credentials')
    path = parsed.path.rstrip('/') + '/'
    return urlunsplit((parsed.scheme, parsed.netloc, path, '', ''))


def heading_id(label: str) -> str:
    return re.sub(r'[^\w\s-]', '', label.lower()).replace(' ', '-')


def public_entry(path: str) -> bool:
    p = Path(path)
    return p.suffix == '.md' and p.parts[0] in READER_PREFIXES and '..' not in p.parts


def split_frontmatter(text: str) -> tuple[dict, str]:
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
    if match:
        return yaml.safe_load(match[1]) or {}, match[2]
    return {}, text


def source_title(text: str, path: str) -> str:
    meta, body = split_frontmatter(text)
    heading = re.search(r'^#\s+(.+)$', body, re.M)
    title = heading[1] if heading else meta.get('title', Path(path).stem)
    return re.sub(r'\s*·\s*Faye\s*&\s*Cove\s*$', '', title)


def reading_comment_inline(state, silent: bool) -> bool:
    """Consume authoring comments at the Markdown boundary, after code parsing."""
    if not state.src.startswith('<!--', state.pos):
        return False
    closing = state.src.find('-->', state.pos + 4, state.posMax)
    if closing < 0:
        return False
    comment = state.src[state.pos + 4:closing].strip()
    figure = re.fullmatch(r'figure:\s*([\w-]+)', comment)
    if not silent and figure and figure[1] in FIGCAP:
        token = state.push('image', 'img', 0)
        token.attrSet('src', relative_url(state.env.get('source_path', 'README.md'), f'assets/{figure[1]}.svg'))
        text = Token('text', '', 0)
        text.content = FIGCAP[figure[1]]
        token.children = [text]
    state.pos = closing + 3
    return True


def reading_comment_block(state, start_line: int, end_line: int, silent: bool) -> bool:
    """Remove standalone comments, including multiline notes, never indented code."""
    if state.is_code_block(start_line):
        return False
    start = state.bMarks[start_line] + state.tShift[start_line]
    if not state.src.startswith('<!--', start):
        return False
    for line in range(start_line, end_line):
        ending = state.src.find('-->', start, state.eMarks[line])
        if ending < 0:
            continue
        if state.src[ending + 3:state.eMarks[line]].strip():
            return False
        comment = state.src[start + 4:ending].strip()
        figure = re.fullmatch(r'figure:\s*([\w-]+)', comment)
        if figure and figure[1] in FIGCAP:
            return False  # The ordinary paragraph's inline rule emits the public figure.
        if not silent:
            state.line = line + 1
        return True
    return False


def chapter_markup(label: str, number_class: str, title_class: str, separator_class: str) -> str:
    numbered = re.fullmatch(r'(\d{2}) / (.+)', label)
    if numbered:
        return (f'<span class="{number_class}">{escape(numbered[1])}</span>'
                f'<span class="{separator_class}"> / </span>'
                f'<span class="{title_class}">{escape(numbered[2])}</span>')
    return f'<span class="{title_class}">{escape(label)}</span>'


class Site:
    def __init__(self, root: Path, output: Path, base_url: str | None = None):
        self.root, self.output = root.resolve(), output.resolve()
        self.base_url = normalize_base_url(base_url)
        catalog = json.loads((root / 'catalog/entries.json').read_text(encoding='utf-8'))
        self.entries = {e['path']: e for e in catalog['entries']}
        self.paths = [p for p in PUBLIC_DOCS if (root / p).is_file()]
        self.paths += [p for p, e in self.entries.items() if public_entry(p) and e['status'] != 'draft']
        self.paths = list(dict.fromkeys(self.paths))
        self.diagrams = json.loads((root / 'diagrams/index.json').read_text(encoding='utf-8'))
        self.sources = json.loads((root / 'catalog/sources.json').read_text(encoding='utf-8'))
        self.attachments = self.select_attachments()
        self.texts = {p: self.page_markdown(p) for p in self.paths}
        self.titles = {p: source_title(t, p) for p, t in self.texts.items()}
        self.search = []
        self.directory_items = []
        self.presentation = {}
        self.publications = pub.Collection(root, pub.load(root))
        self.md = MarkdownIt('commonmark', {'html': False}).enable('table')
        self.md.inline.ruler.before('html_inline', 'reading_comment', reading_comment_inline)
        self.md.block.ruler.before('html_block', 'reading_comment', reading_comment_block,
                                   {'alt': ['paragraph', 'reference', 'blockquote', 'list']})
        self.terms = self.glossary_terms()

    def demo_available(self) -> bool:
        return self.entries.get('examples/job-state/README.md', {}).get('status') == 'current'

    def glossary_terms(self) -> dict:
        if 'docs/glossary.md' not in self.texts:
            return {}
        soup = BeautifulSoup(self.md.render(split_frontmatter(self.texts['docs/glossary.md'])[1]), 'html.parser')
        terms = {}
        for heading in soup.find_all('h2'):
            paragraph = heading.find_next_sibling()
            if paragraph and paragraph.name == 'p':
                terms[heading_id(heading.get_text())] = {'title': heading.get_text(), 'definition': paragraph.get_text(' ', strip=True)}
        return terms

    def index_content(self, soup: BeautifulSoup, page: str, title: str, kind: str, status: str = 'current') -> None:
        """Index each h2/h3's own body, with its parent heading as context."""
        if status == 'withdrawn':
            return
        clean = BeautifulSoup(str(soup), 'html.parser')
        for node in clean.select('script, .heading-link'):
            node.decompose()
        section, parent, chunks, chapter = '', '', [], ''
        anchor = ''
        def emit():
            text = ' '.join(chunks).strip()
            if text or section:
                self.search.append({'title': title, 'section': section, 'context': parent,
                                    'chapter': chapter,
                                    'url': page + ('#' + quote(anchor, safe='-') if anchor else ''),
                                    'kind': kind, 'status': status, 'text': text})
        for node in clean.descendants:
            if getattr(node, 'name', None) in {'h2', 'h3'}:
                emit()
                section, anchor = node.get_text(' ', strip=True), node.get('id', '')
                if node.name == 'h2':
                    parent = section
                    chapter = anchor
                chunks = []
            elif isinstance(node, NavigableString) and not node.find_parent(['h2', 'h3', 'script', 'button', 'select', 'nav']):
                chunks.append(str(node).strip())
        emit()

    def select_attachments(self) -> set[str]:
        selected = {'LICENSE', 'catalog/sources.json', 'catalog/launches.json', 'catalog/decision-routes.json',
                    'catalog/observability-pricing.json', 'catalog/publications.json', 'catalog/publication-releases.json',
                    'assets/diagrams/manifest.json'}
        for diagram in self.diagrams:
            selected.update((diagram['source'], diagram['output']))
        selected.update(f'assets/{key}.svg' for key in FIGCAP)
        selected.update(('assets/two-routes-mobile.svg', 'assets/task-state-mobile.svg'))
        for name, filenames in EXAMPLE_FILES.items():
            path = f'examples/{name}/README.md'
            # Executable bytes are distributed only for catalog-current examples.
            if self.entries.get(path, {}).get('status') == 'current':
                selected.update(f'examples/{name}/{f}' for f in filenames)
        return {p for p in selected if (self.root / p).is_file()}

    def page_markdown(self, path: str) -> str:
        entry = self.entries.get(path, {})
        if entry.get('status') == 'withdrawn':
            return f"# 已撤下：{entry['id']}\n\n此资料已停止分发。为避免继续传播问题内容，本站不提供原正文、执行附件或原 Markdown。修复后的 revision 需重新审阅。\n"
        return project_markdown(self.root, path)

    def url(self, page: str, target: str) -> str:
        if page == '404.html':
            # A host can serve 404.html at any missing depth. Relative paths would break.
            prefix = urlsplit(self.base_url).path if self.base_url else '/'
            return prefix + target
        return relative_url(page, target)

    def canonical(self, page: str) -> str | None:
        if not self.base_url or page == '404.html':
            return None
        return self.base_url + ('' if page == 'index.html' else quote(page, safe='/'))

    def chapter_url(self, family_key: str, chapter_id: str) -> str:
        """A stable chapter target: family entry + `<!-- chapter: ID -->`, not a position."""
        fam = self.publications.family(family_key)
        chapter = self.publications.chapter(fam, chapter_id)
        path = self.publications.entry_path(pub.source_entry(fam))
        return str(Path(path).with_suffix('.html')) + '#' + quote(chapter['id'], safe='-')

    def chapter_ids_for(self, path: str) -> dict:
        """Map a `## ` display label to its stable `<!-- chapter: ID -->` marker and
        any explicit legacy anchor (for chapters whose title changed)."""
        legacy = {}
        for fam in self.publications.families():
            if self.publications.entry_path(pub.source_entry(fam)) == path:
                legacy = fam.get('legacy_anchors', {})
        _, body = split_frontmatter(self.texts[path])
        mapping, pending = {}, None
        for line in body.splitlines():
            marker = re.match(r'^\s*<!--\s*chapter:\s*([\w.-]+)\s*-->\s*$', line)
            if marker:
                pending = marker[1]
                continue
            if not line.startswith('## '):
                continue
            label = line[3:].strip()
            if pending:
                mapping[label] = {'id': pending, 'legacy': legacy.get(pending)}
            pending = None
        return mapping

    def reading_url(self, page: str) -> str:
        return page if str(Path(page).with_suffix('.md')) in self.paths else 'directory.html'

    def starting_path(self) -> str:
        status = self.entries.get('guides/handbook.md', {}).get('status')
        return self.reading_url('guides/handbook.html') if status in {'current', 'withdrawn'} else 'directory.html'

    def work_entries(self) -> str:
        """The three reading works: handbook, comparison, current report — from publications.json."""
        cards = []
        labels = {'handbook': '01 / GUIDE', 'comparison': '02 / TOPIC', 'launches': '03 / DISPATCH'}
        order = {'handbook': 0, 'comparison': 1, 'launches': 2}
        families = sorted(self.publications.families(), key=lambda f: order.get(f['id'], 9))
        for fam in families:
            source = pub.source_entry(fam)
            path = self.publications.entry_path(source)
            status = self.entries.get(path, {}).get('status')
            # The handbook always leads the works list; its card falls back to the
            # directory when the guide is unavailable. Other works appear only when
            # their manuscript is current.
            if fam['id'] != 'handbook' and status != 'current':
                continue
            number = labels.get(fam['id'], '00 / WORK')
            href = self.starting_path() if fam['id'] == 'handbook' else self.reading_url(str(Path(path).with_suffix('.html')))
            if fam['id'] == 'handbook':
                title, deck = fam['label'], '发布、访问、数据与恢复。<br>从正在做的事，找到合适的服务。'
            else:
                title, deck = fam['cover'].get('short', fam['label']), fam['cover'].get('deck', '').replace('<br>', '')
                identity = self.work_identity(fam, path)
                if identity:
                    deck = f'{identity}。<br>保留当时的开放条件与来源。' if fam['id'] == 'launches' else deck
            cards.append(f'<a class="path" href="{escape(href)}"><span class="path-number">{number}</span><h2>{escape(title)} <span>→</span></h2><p>{deck}</p></a>')
        return ''.join(cards)

    def work_identity(self, fam: dict, path: str) -> str:
        text = self.texts.get(path, '')
        ident = pub.report_identity(text, pub.source_entry(fam))
        return ident['date'] if fam['id'] == 'launches' else ''

    def page_description(self, path: str) -> str:
        """Each article carries its own description and date, not the site default."""
        meta, _ = split_frontmatter(self.texts[path])
        subtitle = meta.get('subtitle')
        entry = self.entries.get(path, {})
        date = meta.get('source_cutoff') or (entry.get('review') or {}).get('checked_on')
        parts = [p for p in (subtitle, (f'资料截至 {date}' if date else None)) if p]
        text = '。'.join(parts) if parts else self.titles[path]
        return text[:280]

    def share_image(self, path: str) -> str:
        if self.entries.get(path, {}).get('status') == 'withdrawn':
            return 'assets/share/fieldbook.png'
        for fam in self.publications.families():
            if self.publications.entry_path(pub.source_entry(fam)) == path:
                return fam['share_image']
        return 'assets/share/fieldbook.png'

    def nav(self, page: str) -> str:
        items = [(self.starting_path(), '从用途开始'), ('products.html', '认识服务'),
                 ('publications.html', '作品与版本'),
                 (self.reading_url('practice/README.html'), '实践记录'), ('directory.html', '目录 / 搜索')]
        return '<nav class="global-nav" aria-label="全站导航">' + ''.join(
            f'<a href="{escape(self.url(page, href))}">{label}</a>' for href, label in items) + '</nav>'

    def frame(self, page: str, title: str, body: str, css_class: str = '', *, extra_styles: tuple = (), extra_scripts: tuple = (), description: str | None = None, share_image: str | None = None) -> str:
        u = lambda target: escape(self.url(page, target))
        canonical = self.canonical(page)
        canonical_tag = f'<link rel="canonical" href="{escape(canonical)}">' if canonical else ''
        source_path = str(Path(page).with_suffix('.md'))
        noindex = not self.base_url or page == '404.html' or self.entries.get(source_path, {}).get('status') == 'withdrawn'
        robots_tag = '<meta name="robots" content="noindex">' if noindex else ''
        description = description or 'CF Fieldbook 是 Faye & Cove 的独立参考资料：从用途理解服务，比较路线，阅读可以检查的实践与来源。'
        share_image = share_image or 'assets/share/fieldbook.png'
        social = ''
        if self.base_url and page != '404.html':
            canonical_url = escape(canonical or (self.base_url + page))
            image_url = escape(self.base_url + share_image)
            social = (f'<meta property="og:type" content="article"><meta property="og:title" content="{escape(title)} · CF Fieldbook">'
                      f'<meta property="og:description" content="{escape(description)}">'
                      f'<meta property="og:url" content="{canonical_url}"><meta property="og:image" content="{image_url}">'
                      f'<meta property="og:site_name" content="CF Fieldbook">'
                      f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{escape(title)} · CF Fieldbook">'
                      f'<meta name="twitter:description" content="{escape(description)}"><meta name="twitter:image" content="{image_url}">')
        extras = ''.join(f'<link rel="stylesheet" href="{u(p)}">' for p in extra_styles)
        extras += ''.join(f'<script defer src="{u(p)}"></script>' for p in extra_scripts)
        legend = '<details class="link-legend"><summary>链接图例</summary><ul>' + ''.join(
            f'<li id="link-{kind}"><span class="link-symbol" data-link-kind="{kind}"></span>{label}</li>' for kind, label in LINK_LABELS.items()) + '</ul></details>'
        term_data = json.dumps(self.terms, ensure_ascii=False).replace('<', '\\u003c')
        dialog = f'''<dialog id="term-dialog" aria-labelledby="term-title"><div class="term-dialog-head"><p class="eyebrow">术语 / FIELD NOTES</p><button type="button" id="term-close" aria-label="关闭词义">关闭 ×</button></div><h2 id="term-title"></h2><p id="term-definition"></p><a id="term-full-link" href="{u('docs/glossary.html')}">在词表中继续阅读</a></dialog><script id="term-data" type="application/json">{term_data}</script>''' if self.terms else ''
        document = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · CF Fieldbook</title><meta name="author" content="Faye &amp; Cove">
<meta name="description" content="{escape(description)}">
{social}
<script>try{{if(localStorage.getItem('fieldbook-theme')==='warm')document.documentElement.dataset.theme='warm'}}catch(_){{}}</script>
{canonical_tag}{robots_tag}<link rel="icon" href="{u('assets/motifs/favicon.svg')}" type="image/svg+xml">
<link rel="stylesheet" href="{u('styles/site.css')}">{extras}<script defer src="{u('styles/site.js')}"></script></head>
<body class="{css_class}"><a class="skip-link" href="#main">跳到正文</a>
<header class="site-header"><a class="wordmark" href="{u('index.html')}"><strong>CF Fieldbook<span class="wordmark-dot">.</span></strong><span>用途 · 选择 · 实践</span></a><div class="header-side">{self.nav(page)}<button type="button" class="theme-toggle" aria-pressed="false" aria-label="切换到暖纸主题"><span class="theme-toggle-icon" aria-hidden="true">◐</span><span class="theme-toggle-label">暖阳</span></button></div></header>
{body}
{dialog}<footer class="site-footer"><img src="{u('assets/motifs/cat-sunrise.svg')}" width="96" height="64" alt="" aria-hidden="true"><div><p>独立参考 · 非 Cloudflare 官方出版物，未获 Cloudflare 背书。</p><p><a href="https://github.com/IndelibleVivi">GitHub · IndelibleVivi</a> · <a href="{u('LICENSE-STATUS.html')}">许可状态</a></p><p class="trademark">Cloudflare® 是 Cloudflare, Inc. 的注册商标。</p><p class="signature">made by Faye &amp; Cove</p><div class="reading-legend">{legend}</div></div><a class="back-top" href="#main">回到页首 ↑</a></footer></body></html>'''
        soup = BeautifulSoup(document, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link['href']
            if re.fullmatch(r'S\d{2,3}', link.get_text()):
                link['class'] = list(dict.fromkeys([*link.get('class', []), 'source-ref']))
            parsed = urlsplit(href)
            if link.get('download') is not None or (not parsed.scheme and parsed.path and Path(parsed.path).suffix not in {'.html', ''}):
                kind = 'attachment'
            elif href.startswith(REPOSITORY_URL) or href.startswith('https://github.com/IndelibleVivi/cf-fieldbook/'):
                kind = 'repository'
            elif parsed.scheme or parsed.netloc:
                kind = 'source'
            elif parsed.path.endswith('docs/glossary.html') and unquote(parsed.fragment) in self.terms:
                kind = 'term'
                link['data-term'] = unquote(parsed.fragment)
            else:
                kind = 'internal'
            link['data-link-kind'] = kind
            link['aria-describedby'] = 'link-' + kind
            if kind == 'attachment':
                link['data-attachment-action'] = 'download' if link.has_attr('download') else 'open'
        return str(soup)

    def rewrite(self, soup: BeautifulSoup, path: str, *, figures: bool = True) -> None:
        page = str(Path(path).with_suffix('.html'))
        for node in soup.find_all(['a', 'img']):
            key = 'href' if node.name == 'a' else 'src'
            value = node.get(key, '')
            # Links authored for the published reader also work offline and respect lifecycle.
            if node.name == 'a' and value.startswith(PUBLIC_SITE_URL):
                value = relative_url(path, value[len(PUBLIC_SITE_URL):] or 'index.html')
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc or value.startswith('#'):
                if node.name == 'img' and (parsed.scheme or parsed.netloc):
                    raise ValueError(f'Remote image assets are not supported: {path}: {value}')
                if node.name == 'a' and re.fullmatch(r'S\d{2,3}', node.get_text()) and self.entries.get(path, {}).get('track') != 'edition':
                    node[key] = self.url(page, 'sources.html') + '#' + node.get_text()
                    node['class'] = ['source-ref']
                continue
            target = (self.root / Path(path).parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(self.root):
                raise ValueError(f'Link escapes repository: {path}: {value}')
            rel = target.relative_to(self.root).as_posix()
            markdown_target = str(Path(rel).with_suffix('.md')) if rel.endswith('.html') else rel
            if rel in {'index.html', 'directory.html', 'products.html', 'publications.html', 'sources.html'} \
                    or re.fullmatch(r'publications-[\w-]+\.html', rel) \
                    or (rel == 'examples/job-state/demo.html' and self.demo_available()):
                node[key] = self.url(page, rel) + (f'#{parsed.fragment}' if parsed.fragment else '')
            elif markdown_target in self.paths:
                node[key] = self.url(page, str(Path(markdown_target).with_suffix('.html'))) + (f'#{parsed.fragment}' if parsed.fragment else '')
            elif rel in self.attachments or rel in SITE_ASSETS:
                node[key] = self.url(page, rel) + (f'#{parsed.fragment}' if parsed.fragment else '')
            elif node.name == 'a' and rel in PUBLIC_REPOSITORY_PATHS:
                node[key] = REPOSITORY_URL + quote(rel, safe='/') + (f'#{parsed.fragment}' if parsed.fragment else '')
            elif node.name == 'img':
                raise ValueError(f'Image is outside public allowlist: {path}: {value}')
            else:
                label = node.get_text()
                node.name = 'span'
                node.attrs = {'class': 'repository-ref', 'title': '未随阅读站分发的仓库文件：' + rel}
                node.string = label + '（仓库文件）'
        for table in list(soup.find_all('table')):
            wrapper = soup.new_tag('div', attrs={'class': 'table-scroll', 'tabindex': '0', 'aria-label': '可横向滚动的表格'})
            table.wrap(wrapper)
        if not figures:
            return
        for img in list(soup.find_all('img')):
            if img.parent.name == 'p' and len(img.parent.contents) == 1:
                img.parent.unwrap()
            figure = soup.new_tag('figure')
            scroll = soup.new_tag('div', attrs={'class': 'diagram-scroll', 'tabindex': '0', 'aria-label': '可横向滚动的图示'})
            img.wrap(scroll)
            scroll.wrap(figure)
            original = str(img['src'])
            basename = Path(urlsplit(original).path).stem
            mobile_path = f'assets/{basename}-mobile.svg'
            if basename in {'two-routes', 'task-state'} and mobile_path in self.attachments:
                picture = soup.new_tag('picture', attrs={'class': 'responsive-figure'})
                img.wrap(picture)
                source = soup.new_tag('source', attrs={'media': '(max-width: 1100px)', 'srcset': self.url(page, mobile_path)})
                picture.insert(0, source)
            if '/diagrams/' in str(img['src']):
                img['class'] = ['technical-diagram']
                # The generated viewBox sets a readable per-diagram display width.
                svgpath = (self.root / Path(path).parent / unquote(str(img['src']))).resolve()
                if svgpath.is_file():
                    match = re.search(r'viewBox="\s*[-.\d]+\s+[-.\d]+\s+([\d.]+)\s+([\d.]+)"', svgpath.read_text())
                    if match:
                        img['style'] = f'width:{min(float(match[1]), 1200):.0f}px'
            caption = soup.new_tag('figcaption')
            caption.append(img.get('alt', ''))
            caption.append(' · ')
            link = soup.new_tag('a', href=img['src'])
            link.string = '打开全尺寸 SVG'
            caption.append(link)
            if basename in {'two-routes', 'task-state'} and mobile_path in self.attachments:
                caption.append(' · ')
                mobile_link = soup.new_tag('a', href=self.url(page, mobile_path), attrs={'class': 'mobile-figure-link'})
                mobile_link.string = '打开纵版 SVG'
                caption.append(mobile_link)
            figure.append(caption)

    def render_content(self, path: str) -> tuple[str, list[tuple[str, str]], str]:
        chapter_ids = self.chapter_ids_for(path)
        meta, body = split_frontmatter(self.texts[path])
        # Source tokens may appear without link definitions in concise maintained pages.
        # The catalog supplies those missing definitions; existing edition definitions win.
        defined = set(re.findall(r'^\[(S\d{2,3})\]:', body, re.M))
        used = set(re.findall(r'\[(S\d{2,3})\]', body))
        source_by_id = {s['id']: s for s in self.sources}
        missing = used - defined
        unknown = missing - source_by_id.keys()
        if unknown:
            raise ValueError(f'Unknown source references in {path}: {sorted(unknown)}')
        for ident in sorted(missing):
            body += f'\n[{ident}]: {source_by_id[ident]["url"]}\n'
        soup = BeautifulSoup(self.md.render(body, {'source_path': path}), 'html.parser')
        # The GitHub masthead belongs to the repository; the website has its own header.
        if path == 'README.md':
            for banner in soup.select('p > a > img[src="assets/motifs/repository-banner.svg"]'):
                banner.find_parent('p').decompose()
        # Only the authored question/answer prefix pair is enhanced; arbitrary HTML stays disabled.
        for block in soup.find_all('blockquote'):
            paragraphs = block.find_all('p', recursive=False)
            if not paragraphs or not paragraphs[0].find('strong') or not paragraphs[0].strong.get_text().startswith('想一想：'):
                continue
            answer = next((p for p in paragraphs[1:] if p.find('strong') and p.strong.get_text().startswith('答案：')), None)
            if answer:
                block['class'] = ['understanding-question']
                details = soup.new_tag('details', attrs={'class': 'understanding-answer'})
                summary = soup.new_tag('summary')
                summary.string = '展开答案与解释'
                details.append(summary)
                answer_nodes = [answer, *list(answer.next_siblings)]
                for node in answer_nodes:
                    details.append(node.extract())
                block.append(details)
        h1 = soup.find('h1')
        if h1:
            h1.decompose()
        self.presentation[path] = {}
        # Move only an exact opening edition/subtitle pair into the article header.
        opening = soup.find('p')
        if opening and opening.strong and opening.br and meta.get('subtitle'):
            lines = [line.strip() for line in opening.get_text().splitlines() if line.strip()]
            if len(lines) == 2:
                subtitle = re.sub(r'\s*·\s*Faye\s*&\s*Cove\s*$', '', lines[1])
                if subtitle == meta['subtitle'] and str(meta.get('edition', '')).startswith(lines[0]):
                    self.presentation[path] = {'edition': lines[0], 'subtitle': subtitle}
                    opening.decompose()
        # Remove presentation signatures only; narrative and rights text remain authored.
        for p in list(soup.find_all('p')):
            if p.find(['code', 'pre']):
                continue
            lines = [line.strip() for line in p.get_text().splitlines() if line.strip()]
            signature_line = lambda line: bool(re.fullmatch(r'made by Faye\s*&\s*Cove', line, re.I))
            github_line = lambda line: bool(re.fullmatch(r'(?:GitHub\s*[·:：]?\s*)?(?:https://)?github\.com/IndelibleVivi/?', line))
            if lines and all(signature_line(line) or github_line(line) for line in lines):
                p.decompose()
        headings, seen = [], {}
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            label = heading.get_text()
            stem = heading_id(label)
            seen[stem] = seen.get(stem, 0) + 1
            ident = stem + (f'-{seen[stem] - 1}' if seen[stem] > 1 else '')
            if heading.name == 'h2':
                # A stable `<!-- chapter: ID -->` marker wins the ID; the display
                # slug stays behind as a legacy alias so old links keep working.
                marker = chapter_ids.get(label, {})
                stable = marker.get('id')
                legacy_ids = []
                if stable and stable != ident:
                    legacy_ids.append(ident)
                if marker.get('legacy') and marker['legacy'] not in legacy_ids and marker['legacy'] != stable:
                    legacy_ids.append(marker['legacy'])
                ident = stable or ident
                heading['id'] = ident
                headings.append((ident, label))
                if re.fullmatch(r'\d{2} / .+', label):
                    heading['class'] = [*heading.get('class', []), 'numbered-chapter']
                    heading.clear()
                    heading.append(BeautifulSoup(chapter_markup(label, 'chapter-number', 'chapter-title', 'chapter-separator'), 'html.parser'))
                for legacy in legacy_ids:
                    alias = soup.new_tag('span', attrs={'id': legacy, 'class': 'chapter-alias', 'aria-hidden': 'true'})
                    heading.insert(0, alias)
            else:
                heading['id'] = ident
            anchor = soup.new_tag('a', attrs={'href': '#' + ident, 'class': 'heading-link', 'aria-label': '链接到：' + label})
            anchor.string = '#'
            heading.append(anchor)
        self.rewrite(soup, path)
        if path == 'diagrams/README.md':
            for diagram in self.diagrams:
                title = diagram.get('title') or diagram['id']
                fragment = BeautifulSoup(self.md.render(f"## {title}\n\n![{title}](../{diagram['output']})\n\n[Mermaid 源码](../{diagram['source']})"), 'html.parser')
                self.rewrite(fragment, path)
                fragment.h2['id'] = 'diagram-' + diagram['id']
                headings.append((fragment.h2['id'], title))
                soup.append(fragment)
        return str(soup), headings, soup.get_text(' ', strip=True)

    def notice(self, path: str) -> str:
        entry = self.entries.get(path)
        if not entry:
            return ''
        review = entry.get('review', {})
        status = STATUS_LABELS[entry['status']]
        if entry.get('track') == 'edition':
            status = '历史报告 · ' + Path(path).stem + ' 资料快照'
        text = f"{status} · 查阅于 {review.get('checked_on', '未登记')}"
        scope = review.get('scope', '未登记核验范围')
        return f'<details class="evidence-note"><summary>{escape(text)} · 核验范围</summary><p>{escape(scope)}。来源记录的日期与范围适用于本文；来源核对不等于账户或云端实测。</p></details>'

    def reader(self, path: str) -> str:
        page = str(Path(path).with_suffix('.html'))
        content, headings, plain = self.render_content(path)
        entry = self.entries.get(path, {})
        kind = KIND_LABELS.get(entry.get('kind', 'doc'), '资料')
        toc = ''.join(f'<li><a href="#{escape(ident)}">{chapter_markup(label, "toc-number", "toc-label", "toc-separator")}</a></li>' for ident, label in headings)
        presentation = self.presentation[path]
        title = escape(self.titles[path])
        if title.startswith('Cloudflare '):
            title = '<span class="title-prefix">Cloudflare </span>' + title[len('Cloudflare '):]
        if entry.get('kind') == 'practice' and '：' in title:
            title, subtitle = title.split('：', 1)
            presentation = {**presentation, 'subtitle': html.unescape(subtitle)}
        deck = f'<p class="article-deck">{escape(presentation["subtitle"])}</p>' if presentation.get('subtitle') else ''
        edition = f'<p class="edition-line">{escape(presentation["edition"])}</p>' if presentation.get('edition') else ''
        download = '' if entry.get('status') == 'withdrawn' else f'<a download href="{escape(self.url(page, path))}">下载 Markdown ↓</a>'
        files = ''
        if entry.get('kind') == 'example' and entry.get('status') == 'current':
            root_dir = Path(path).parent
            related = sorted(p for p in self.attachments
                             if root_dir == Path(p).parent or root_dir in Path(p).parents)
            demo_link = '<p><a href="demo.html">逐步观察：任务恢复演示 →</a>（离线模型事件回放）</p>' if path == 'examples/job-state/README.md' and self.demo_available() else ''
            files = '<section class="example-downloads"><h2>例子附件</h2>' + demo_link + '<p>在自己的本地环境检查；本站不调用云端服务或部署例子。</p><ul>' + ''.join(
                f'<li><a download href="{escape(self.url(page, p))}">{escape(Path(p).relative_to(root_dir))} ↓</a></li>' for p in related) + '</ul></section>'
        status = entry.get('status', 'current')
        self.directory_items.append({'title': self.titles[path], 'url': page, 'kind': kind, 'status': status})
        self.index_content(BeautifulSoup(content, 'html.parser'), page, self.titles[path], kind, status)
        motif = READER_MOTIFS.get(entry.get('kind'), 'reading-pages')
        body = f'''<main id="main" class="reader-main"><header class="article-header"><div class="article-heading"><p class="eyebrow"><a href="{escape(self.url(page, 'index.html'))}">CF FIELDBOOK</a><span>/</span>{escape(kind)}</p><h1>{title}</h1>{deck}<div class="article-meta">{edition}{self.notice(path)}</div></div><img class="reader-mark" src="{escape(self.url(page, f'assets/motifs/{motif}.svg'))}" width="320" height="200" alt="" aria-hidden="true"></header>
<div class="reader-layout"><aside class="contents"><a class="contents-home" href="{escape(self.url(page, 'directory.html'))}">← 全部资料</a><details open><summary>本页目录</summary><ol>{toc}</ol></details><div class="reader-tools">{download}<a href="{escape(self.url(page, 'sources.html'))}">查阅来源索引 ↗</a></div></aside>
<article class="article"><div class="prose">{content}{files}</div><div class="reading-end"><img class="colophon-mark" src="{escape(self.url(page, 'assets/motifs/colophon.svg'))}" width="64" height="64" alt="" aria-hidden="true"><a href="{escape(self.url(page, 'practice/README.html') if entry.get('kind') == 'practice' else self.url(page, 'directory.html'))}">继续阅读：{'实践记录' if entry.get('kind') == 'practice' else '全部资料'} →</a></div></article></div></main>'''
        return self.frame(page, self.titles[path], body, 'reader-page',
                          description=self.page_description(path),
                          share_image=self.share_image(path))

    def product_links(self, *, compact: bool = False) -> str:
        if self.entries.get('guides/handbook.md', {}).get('status') != 'current':
            return ''
        rows = []
        for index, row in enumerate(self.publications.product_rows(self.publications.family('handbook')), 1):
            target = self.chapter_url('handbook', row['chapter'])
            if compact:
                rows.append(f'<li><a href="{escape(target)}"><span class="product-category">{escape(row["category"])}</span><span>{escape(row["names"])}</span><span class="product-arrow">↗</span></a></li>')
            else:
                supplement = ''
                if 'comparisons/clef-vs-jev.md' in self.paths and 'Clef' in row['names']:
                    supplement = '<a href="comparisons/clef-vs-jev.html">Clef / Jev 比较 →</a>'
                if 'use-cases/recoverable-jobs.md' in self.paths and row['chapter'] == 'jobs':
                    supplement = '<a href="use-cases/recoverable-jobs.html">任务恢复实践 →</a>'
                rows.append(f'<section class="product-reading"><div class="product-heading"><span class="product-index">{index:02d}</span><p>{escape(row["category"])}</p></div><div class="product-body"><h2><a href="{escape(target)}">{escape(row["names"])}</a></h2><p>{escape(row["description"])}</p><div class="product-actions"><a href="{escape(target)}">{escape(row["action"])} ↗</a>{supplement}</div></div></section>')
        return ''.join(rows)

    def home(self) -> str:
        home = self.publications.family('handbook')['home']
        practices = (
            ('private-reader', '01', 'Workers · D1 · R2 · Vectorize', '电脑关机以后，<br>读者仍能阅读。', '一次私有资料站的发布、检索与授权实践。看内容怎样完整交付，又怎样在中断后继续。'),
            ('access-pwa', '02', 'Access · PWA', '页面还在，<br>为什么连接已断？', '缓存外壳与登录会话有不同的寿命。从一次手机端故障，找到真正走网络的重连路径。'),
            ('protected-status', '03', 'Tunnel · Access · Monitoring', '门禁正常，<br>服务就正常了吗？', '把入口、源站与登录后的页面分开检查，读懂状态页给出的每一条线索。'),
        )
        practice_cards = ''.join(f'<a class="practice-card" href="practice/{slug}.html"><div class="practice-card-top"><span>{number}</span><span>实践记录 ↗</span></div><h3>{title}</h3><p>{description}</p><div class="practice-stack">{stack}</div></a>' for slug, number, stack, title, description in practices if f'practice/{slug}.md' in self.paths and self.entries[f'practice/{slug}.md']['status'] == 'current')
        works = self.work_entries()
        body = f'''<main id="main" class="home"><section class="home-cover"><div class="cover-copy"><p class="eyebrow">{escape(home["eyebrow"])}</p><h1>{escape(home["lead"])}<br><em>{escape(home["em"])}</em></h1><p class="cover-deck">{home["deck"]}</p><a class="cover-start" href="{escape(self.starting_path())}"><span>{escape(home["actions"][0]["label"])}</span><span aria-hidden="true">→</span></a><a class="cover-secondary" href="{escape(self.reading_url('practice/README.html'))}">{escape(home["actions"][1]["label"])}</a></div><figure class="cover-art"><img src="assets/motifs/cat-sunrise.svg" alt="青色猫坐在书页般的地平线上，望向橙色日出" width="600" height="400" fetchpriority="high"></figure></section>
<section class="entry-paths" aria-label="三份作品入口">{works}</section>
<section class="practice-section" aria-labelledby="practice-heading"><header class="section-heading"><div><p class="eyebrow">NOTES FROM THE FIELD</p><h2 id="practice-heading">真实问题，实际走过的路。</h2></div><a href="{escape(self.reading_url('practice/README.html'))}">全部实践记录 →</a></header><div class="practice-grid">{practice_cards}</div><p class="practice-caption">来自作者维护过的系统 · 匿名重构 · 各篇保留观察日期与验证范围</p></section>
<section class="product-spread" aria-labelledby="products-heading"><div class="section-intro"><p class="eyebrow">PRODUCTS / READING PATHS</p><h2 id="products-heading">一个服务，<br>放在什么位置？</h2><p>入口、运行、数据与恢复，各回答不同的问题。沿着一条路径读，不必一次组合所有服务。</p><img class="edge-detail" src="assets/motifs/edge-route.svg" width="360" height="220" alt="" aria-hidden="true"></div><div><ul class="product-links">{self.product_links(compact=True)}</ul><a class="all-products" href="products.html">打开服务阅读索引 →</a></div></section>
<section class="shelf"><div><p class="eyebrow">READ · INSPECT · TAKE AWAY</p><h2>沿着解释，找到依据。</h2><p>读懂一个做法，再看完整代码与来源。<br>也可以带走 Markdown 和离线例子。</p></div><ul><li><a href="directory.html">全部资料与内容搜索 <span>→</span></a></li><li><a href="examples/README.html">四个离线例子 <span>→</span></a></li><li><a href="{escape(self.reading_url('reference/implementation.html'))}">实施参考：代码与恢复语义 <span>→</span></a></li><li><a href="diagrams/README.html">六张图：架构与资料生命周期 <span>→</span></a></li><li><a href="sources.html">来源与核验范围 <span>→</span></a></li></ul></section>
<section class="edition-strip"><p class="eyebrow">DATES &amp; SOURCES</p><p>服务解释持续维护；报告保留各自日期。价格、开放条件和接口限制请结合正文的核验范围与来源阅读。</p><a href="sources.html">查阅来源索引 →</a></section></main>'''
        if self.demo_available():
            body = body.replace('<li><a href="examples/README.html">', '<li><a href="examples/job-state/demo.html">逐步观察任务恢复 <span>→</span></a></li><li><a href="examples/README.html">')
        return self.frame('index.html', '用途、选择与实践的持续参考', body, 'home-page')

    def products_page(self) -> str:
        readings = self.product_links()
        unavailable = '<p class="product-unavailable">服务阅读路径暂时不可用。请从<a href="directory.html">全部资料与搜索</a>查找其他内容。</p>'
        continuation = '<a href="guides/handbook.html">连续阅读：个人基础设施实践手册 →</a>' if readings else ''
        introduction = '<p>从入口到数据，从一次请求到可以恢复的任务。<br>这些阅读路径来自实践手册；选择与限制在相应章节展开。</p>' if readings else ''
        body = f'''<main id="main" class="products-page"><header class="page-title product-title"><div><p class="eyebrow">PRODUCT READING PATHS</p><h1>按问题，认识服务。</h1>{introduction}</div><img src="assets/motifs/edge-route.svg" width="360" height="220" alt="" aria-hidden="true"></header><div class="product-readings">{readings or unavailable}</div><div class="reading-end">{continuation}<a href="directory.html">全部资料与搜索 →</a></div></main>'''
        self.search.append({'title': '认识 Cloudflare 服务：产品阅读索引', 'url': 'products.html', 'kind': '服务',
                            'section': '', 'context': '',
                            'text': ' '.join(f"{row['category']} {row['names']} {row['description']}" for row in self.publications.product_rows(self.publications.family('handbook'))) if readings else '服务阅读路径暂时不可用。请查阅其他资料。',
                            'status': 'current'})
        self.directory_items.append({'title': '按问题认识服务', 'url': 'products.html', 'kind': '服务', 'status': 'current'})
        return self.frame('products.html', '按问题认识 Cloudflare 服务', body)

    def family_readings(self, fam: dict) -> dict:
        """The works page's per-family facts, kept off the home page."""
        path = self.publications.entry_path(pub.source_entry(fam))
        status = self.entries.get(path, {}).get('status', 'draft')
        if status in {'draft', 'withdrawn'}:
            return {'ident': {'title': fam['label'], 'date': ''}, 'cutoff': '未分发',
                    'page': self.reading_url(str(Path(path).with_suffix('.html'))), 'chapters': [], 'status': status}
        text = self.texts.get(path, '')
        ident = pub.report_identity(text, pub.source_entry(fam))
        cutoff = pub.frontmatter_scalar(text, 'source_cutoff') or ident['date']
        return {'ident': ident, 'cutoff': cutoff,
                'page': str(Path(path).with_suffix('.html')) if path else '',
                'chapters': self.publications.chapters(fam), 'status': status}

    def release_notes(self, fam: dict) -> str:
        """Show changes associated with this family; repository commits alone
        do not mean this book's content changed."""
        data = pub.releases(self.root)
        updates = [row for row in data.get('updates', []) if fam['id'] in row['families']]
        changes = ''.join(f'<li><b>{escape(row["date"])}</b> · {escape(row["summary"])}</li>' for row in updates)
        return ('<p>当前正文已收录下列与本册相关的修订；事实查阅日期与编辑修订日分开记录。</p>'
                f'<ul class="release-list">{changes}</ul>')

    def version_page(self, fam: dict) -> str:
        """A per-family version/update page listing the chapters this edition owns
        and the registered releases; safe even when the registry is empty."""
        info = self.family_readings(fam)
        rows = pub.released_for(pub.releases(self.root), fam['id'])
        chapter_list = ''.join(
            f'<li><a href="{escape(self.url(f"publications.html", info["page"]) + "#" + quote(c["id"], safe="-"))}">'
            f'{escape(c["title"])}</a></li>' for c in info['chapters'])
        if rows:
            releases = ''.join(
                f'<li><strong>{escape(r["edition"])}</strong> · {escape(r.get("date", ""))}'
                f'<p>{escape(r.get("summary", ""))}</p>'
                + ''.join(f'<a href="{escape(artifact["url"])}">{escape(fmt.upper())} ↓</a> ' for fmt, artifact in r['files'].items())
                + '</li>' for r in rows)
        else:
            releases = ('<li class="release-empty">尚未登记发布版本。当前为本地候选，'
                        '不宣称新 PDF 已分发。</li>')
        body = f'''<main id="main" class="publications-page"><header class="page-title illustrated-title"><div>
<p class="eyebrow">FIELD EDITIONS / {escape(fam['id'].upper())}</p><h1>{escape(fam['label'])}</h1>
<p>本册以 <strong>{escape(info['ident']['title'])}</strong> 编排，资料截至 {escape(info['cutoff'])}。
章节身份为稳定 ID；显示编号只表示顺序，旧网页锚点保留。</p></div>
<img src="{escape(self.url('publications.html', 'assets/motifs/reading-pages.svg'))}" width="320" height="200" alt="" aria-hidden="true"></header>
<section class="version-block"><h2>本册章节</h2><ol class="version-chapters">{chapter_list}</ol></section>
<section class="version-block"><h2>本册修订</h2>{self.release_notes(fam)}</section>
<section class="version-block"><h2>PDF 版本与分发</h2>{self.latest_download(fam)}<p class="release-note">只列出与<em>本册</em>直接相关、且已登记的版本；
不把任意仓库提交当作本册的过期依据。</p><ul class="release-list">{releases}</ul></section>
<section class="version-block"><h2>固定历史版</h2>{self.historical_links(fam)}</section>
<p class="version-back"><a href="{escape(self.url('publications.html', 'publications.html'))}">← 返回作品与版本入口</a></p></main>'''
        page = f'publications-{fam["id"]}.html'
        self.directory_items.append({'title': fam['label'] + ' · 版本页', 'url': page, 'kind': '资料维护', 'status': 'current'})
        return self.frame(page, fam['label'] + ' · 版本与更新', body, 'publications-page')

    def historical_links(self, fam: dict) -> str:
        records = pub.releases(self.root).get('historical', [])
        row = next((row for row in records if row['family'] == fam['id']), None)
        if not row:
            return '<p>没有登记历史下载。</p>'
        return ('<p>r3 · 资料截至 ' + escape(row['cutoff']) + '；固定保留，未按当前正文重建。</p><ul>'
                + ''.join(f'<li><a href="{escape(url)}">历史 {escape(fmt.upper())} ↗</a></li>' for fmt,url in row['files'].items()) + '</ul>')

    def latest_download(self, fam: dict) -> str:
        data = pub.releases(self.root)
        ident = data.get('latest', {}).get(fam['id'])
        if not ident:
            return '<p>尚无新版 latest 下载；当前候选没有自动发布。</p>'
        record = next(row for row in data['releases'] if row['id'] == ident)
        return '<p>最新已分发：' + escape(record['edition']) + ' · ' + ' · '.join(
            f'<a href="{escape(artifact["url"])}">{escape(fmt.upper())} ↓</a>' for fmt, artifact in record['files'].items()) + '</p>'

    def publications_page(self) -> str:
        cards = []
        for fam in self.publications.families():
            info = self.family_readings(fam)
            page = f'publications-{fam["id"]}.html'
            cards.append(
                f'<section class="family-card"><div class="family-head"><p class="eyebrow">{escape(fam["id"].upper())}</p>'
                f'<h2><a href="{escape(self.url("publications.html", info["page"]))}">{escape(fam["label"])}</a></h2></div>'
                f'<p class="family-meta">资料截至 {escape(info["cutoff"])} · {len(info["chapters"])} 章</p>'
                f'<div class="family-links"><a href="{escape(self.url("publications.html", info["page"]))}">阅读本册 →</a>'
                f'<a href="{escape(self.url("publications.html", page))}">版本与更新 →</a></div>'
                f'<div class="family-note">{self.release_notes(fam)}</div></section>')
        body = f'''<main id="main" class="publications-page"><header class="page-title illustrated-title"><div>
<p class="eyebrow">FIELD EDITIONS</p><h1>三部作品，与它们的版本。</h1>
<p>手册、Clef / Jev 专题与当期观察共源编排。每册有独立身份、稳定章节与版本页；本地候选不是已发布 Release。</p></div>
<img src="{escape(self.url('publications.html', 'assets/motifs/colophon.svg'))}" width="200" height="200" alt="" aria-hidden="true"></header>
<div class="family-grid">{''.join(cards)}</div>
<p class="publications-foot"><a href="{escape(self.url('publications.html', 'directory.html'))}">全部资料与搜索 →</a>
 · <a href="{escape(self.url('publications.html', 'sources.html'))}">来源与核验范围 →</a></p></main>'''
        self.directory_items.append({'title': '作品与版本', 'url': 'publications.html', 'kind': '资料维护', 'status': 'current'})
        return self.frame('publications.html', '作品与版本', body, 'publications-page')

    def recovery_demo(self) -> str:
        from recovery_demo import page_body
        page = 'examples/job-state/demo.html'
        soup = BeautifulSoup(page_body(self.root), 'html.parser')
        for heading in soup.find_all(['h2', 'h3']):
            heading['id'] = heading.get('id') or heading_id(heading.get_text())
        for main in soup.find_all('main'):
            main.unwrap()
        # The fragment contains authored relative links; apply the same public boundary.
        self.rewrite(soup, page, figures=False)
        searchable = soup.select_one('.recovery-page') or soup
        self.index_content(searchable, page, '任务恢复演示', '例子')
        self.directory_items.append({'title': '逐步观察：任务恢复演示', 'url': page, 'kind': '例子', 'status': 'current'})
        return self.frame(page, '逐步观察任务恢复', '<main id="main">' + str(soup) + '</main>',
                          'recovery-demo-page', extra_styles=('styles/recovery.css',), extra_scripts=('styles/recovery.js',))

    def not_found(self) -> str:
        u = lambda target: escape(self.url('404.html', target))
        body = f'''<main id="main" class="not-found"><p class="eyebrow">404 / PAGE NOT FOUND</p><div class="not-found-layout"><div><h1>这一页，没有找到。</h1><p>地址可能有误，或资料已经移动。<br>从阅读目录继续找，也可以回到首页重新翻开。</p><div class="not-found-actions"><a href="{u('directory.html')}">打开目录与搜索 →</a><a href="{u('index.html')}">回到首页 →</a></div></div><img src="{u('assets/motifs/cat-sunrise.svg')}" width="600" height="400" alt=""></div></main>'''
        return self.frame('404.html', '这一页没有找到', body, 'error-page')

    def directory(self) -> str:
        groups = []
        labels = ['实践', '用途', '手册', '服务', '比较', '实施参考', '例子', '带日期报告', '资料维护']
        for label in labels:
            items = [item for item in self.directory_items if item['kind'] == label]
            if items:
                groups.append(f'<section class="directory-group"><h2>{label}</h2><ul>' + ''.join(
                    f'<li class="directory-item"><a href="{escape(item["url"])}">{escape(item["title"])}</a><span>{escape(STATUS_LABELS[item["status"]])}</span></li>' for item in items) + '</ul></section>')
        data = json.dumps(self.search, ensure_ascii=False).replace('<', '\\u003c')
        body = f'''<main id="main" class="directory"><header class="page-title illustrated-title"><div><p class="eyebrow">THE READING INDEX</p><h1>全部资料</h1><p>从一个词继续找，或按下面的阅读目录翻开。搜索只在你的浏览器内处理。</p></div><img src="assets/motifs/field-notes.svg" width="320" height="200" alt="" aria-hidden="true"></header><section class="search-box"><label for="search-input">搜索正文与标题</label><input id="search-input" type="search" placeholder="例如：任务、费用、Clef、租约" disabled><p id="search-status" role="status">启用 JavaScript 后可搜索；完整目录始终可读。</p><ol id="search-results" hidden></ol></section><div id="reading-directory">{''.join(groups)}</div><script id="search-data" type="application/json">{data}</script></main>'''
        return self.frame('directory.html', '全部资料与搜索', body, extra_scripts=('styles/search.js',))

    def sources_page(self) -> str:
        rows = ''.join(f'<li id="{escape(s["id"])}"><span class="source-id">{escape(s["id"])}</span><div><a href="{escape(s["url"])}">{escape(s["title"])}</a><p>记录查阅日期 {escape(s.get("accessed", "未登记"))} · <code>{escape(s.get("verification_scope", "未登记"))}</code></p></div></li>' for s in self.sources)
        body = f'''<main id="main" class="sources-page"><header class="page-title illustrated-title"><div><p class="eyebrow">SOURCES &amp; SCOPE</p><h1>来源与核验范围</h1><p>来源编号对应正文引用。查阅日期与核验范围保留在各条记录中；来源核对不等于账户权限证明或云端实测。</p><p><a download href="catalog/sources.json">下载来源记录 JSON ↓</a></p></div><img src="assets/motifs/reading-pages.svg" width="320" height="200" alt="" aria-hidden="true"></header><ol class="sources-list">{rows}</ol></main>'''
        return self.frame('sources.html', '来源与核验范围', body)

    def download_markdown(self, path: str) -> str:
        """Keep public relative links portable and label undistributed repo references."""
        def link(match):
            prefix, label, value = match.groups()
            parsed = urlsplit(value)
            if value.startswith(PUBLIC_SITE_URL):
                rel = urlsplit(value[len(PUBLIC_SITE_URL):]).path
                if rel == 'examples/job-state/demo.html':
                    return f'{prefix}[{label}]({relative_url(path, rel)})' if self.demo_available() else f'{label}（演示已停止分发）'
            if parsed.scheme or value.startswith('#'):
                return match[0]
            target = (self.root / Path(path).parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(self.root):
                raise ValueError(f'Link escapes repository: {path}: {value}')
            rel = target.relative_to(self.root).as_posix()
            if rel == 'examples/job-state/demo.html' and self.demo_available():
                return match[0]
            if rel in self.paths:
                if self.entries.get(rel, {}).get('status') == 'withdrawn':
                    return f'{prefix}[{label}]({Path(parsed.path).with_suffix(".html")})'
                return match[0]
            if rel in self.attachments or rel in SITE_ASSETS:
                return match[0]
            if rel in PUBLIC_REPOSITORY_PATHS:
                return f'{prefix}[{label}]({REPOSITORY_URL}{quote(rel, safe="/")})'
            return f'{label}（仓库文件，未随阅读站分发）'
        return re.sub(r'(!?)\[([^\]]+)\]\(([^)]+)\)', link, self.texts[path])

    def write(self, path: str, text: str) -> None:
        target = self.output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')

    def write_discovery(self, pages: list[str]) -> None:
        namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
        ElementTree.register_namespace('', namespace)
        sitemap = ElementTree.Element(f'{{{namespace}}}urlset')
        if self.base_url:
            for page in pages:
                source = str(Path(page).with_suffix('.md'))
                if page == '404.html' or self.entries.get(source, {}).get('status') == 'withdrawn':
                    continue
                entry = ElementTree.SubElement(sitemap, f'{{{namespace}}}url')
                ElementTree.SubElement(entry, f'{{{namespace}}}loc').text = self.canonical(page)
        self.write('sitemap.xml', ElementTree.tostring(sitemap, encoding='unicode', xml_declaration=True) + '\n')
        robots = 'User-agent: *\nDisallow: ' + ('\n' if self.base_url else '/\n')
        if self.base_url:
            robots += f'Sitemap: {self.base_url}sitemap.xml\n'
        self.write('robots.txt', robots)

    def build(self) -> dict:
        # A clean generated output prevents withdrawn bytes surviving a rebuild.
        if self.output == self.root or not self.output.is_relative_to(self.root / '.build'):
            raise ValueError('Site output must be a child of repository .build/')
        if self.output.exists():
            shutil.rmtree(self.output)
        self.output.mkdir(parents=True)
        for path in self.paths:
            self.write(str(Path(path).with_suffix('.html')), self.reader(path))
            if self.entries.get(path, {}).get('status') != 'withdrawn':
                self.write(path, self.download_markdown(path))
        self.write('index.html', self.home())
        self.write('products.html', self.products_page())
        self.write('publications.html', self.publications_page())
        version_pages = []
        for fam in self.publications.families():
            page = f'publications-{fam["id"]}.html'
            self.write(page, self.version_page(fam))
            version_pages.append(page)
        demo_pages = []
        demo_assets = set()
        if self.demo_available():
            self.write('examples/job-state/demo.html', self.recovery_demo())
            demo_pages = ['examples/job-state/demo.html']
            demo_assets = {'styles/recovery.css', 'styles/recovery.js'}
        self.write('directory.html', self.directory())
        self.write('search-index.json', json.dumps(self.search, ensure_ascii=False, indent=2) + '\n')
        self.write('sources.html', self.sources_page())
        self.write('404.html', self.not_found())
        for path in sorted(self.attachments | demo_assets | SITE_ASSETS):
            target = self.output / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.root / path, target)
        html_pages = ([str(Path(path).with_suffix('.html')) for path in self.paths] + demo_pages
                      + ['index.html', 'products.html', 'publications.html', *version_pages,
                         'directory.html', 'sources.html', '404.html'])
        self.write_discovery(html_pages)
        manifest = {'schema': 'fieldbook.reading-site/1', 'state': 'static-build', 'base_url': self.base_url,
                    'pages': self.paths, 'html_pages': html_pages, 'attachments': sorted(self.attachments),
                    'notice': 'Read-only offline build; no new product fact verification or cloud execution.'}
        self.write('site-manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        return manifest


def build_site(root: Path = ROOT, output: Path | None = None, base_url: str | None = None) -> dict:
    return Site(root, output or root / '.build/site', base_url).build()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.build/site')
    parser.add_argument('--base-url', help='Public site directory URL, including a project subpath when applicable')
    args = parser.parse_args()
    result = build_site(ROOT, args.output, args.base_url)
    print(f'Built {len(result["html_pages"])} HTML reading pages at {args.output}')


if __name__ == '__main__':
    main()
