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
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup
from markdown_it import MarkdownIt
import yaml

from content import project_markdown

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = (
    'README.md', 'SPEC.md', 'CONTRIBUTING.md', 'LICENSE-STATUS.md', 'docs/architecture.md',
    'docs/lifecycle.md', 'docs/publication.md', 'docs/content-design.md',
    'docs/migration-r3.md', 'docs/current-state.md', 'docs/reading-site.md', 'examples/README.md',
    'diagrams/README.md', 'templates/practice-example.md', 'templates/release-card.md',
)
READER_PREFIXES = {'services', 'comparisons', 'use-cases', 'guides', 'reference', 'reports', 'examples'}
EXAMPLE_FILES = {
    'decision-routing': ('payloads.py', 'example.meta.json'),
    'health-worker': ('index.mjs', 'worker.test.mjs', 'wrangler.example.json', 'example.meta.json'),
    'job-state': ('model.py', 'demo.py', 'example.meta.json'),
}
KIND_LABELS = {'use-case': '用途', 'guide': '手册', 'service': '服务', 'comparison': '比较',
               'example': '例子', 'reference': '实施参考', 'report': '带日期报告', 'doc': '资料维护'}
STATUS_LABELS = {'current': '当前资料', 'superseded': '已有替代', 'archived': '历史归档',
                 'withdrawn': '已撤下', 'draft': '草稿'}
FIGCAP = {
    'workspace': '文件系统可以复用；进程与任务状态另行接续。示意一种工作方式，不是自动合并。',
    'runtime-cost': '同一任务数与配置，条长按每次运行分钟数绘制；详细假设与来源见邻近正文。',
    'two-routes': '两种常见路线，不要求同时采用。Tunnel 不替原设备运行程序。',
    'task-state': '接收、执行与完成分开记录。示意主线；完整状态与失败分支见邻近正文。',
}


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def relative_url(page: str, target: str) -> str:
    return Path(os.path.relpath(target, Path(page).parent)).as_posix()


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
    return heading[1] if heading else meta.get('title', Path(path).stem)


class Site:
    def __init__(self, root: Path, output: Path):
        self.root, self.output = root.resolve(), output.resolve()
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
        self.md = MarkdownIt('commonmark', {'html': False}).enable('table')

    def select_attachments(self) -> set[str]:
        selected = {'catalog/sources.json', 'catalog/launches.json', 'catalog/decision-routes.json',
                    'assets/diagrams/manifest.json'}
        for diagram in self.diagrams:
            selected.update((diagram['source'], diagram['output']))
        selected.update(f'assets/{key}.svg' for key in FIGCAP)
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
        return relative_url(page, target)

    def nav(self, page: str) -> str:
        items = [('guides/handbook.html', '从用途开始'), ('services/decision-models.html', '认识服务'),
                 ('reports/2026-10-02.html', '本期变化'), ('directory.html', '目录 / 搜索')]
        return '<nav class="global-nav" aria-label="全站导航">' + ''.join(
            f'<a href="{escape(self.url(page, href))}">{label}</a>' for href, label in items) + '</nav>'

    def frame(self, page: str, title: str, body: str, css_class: str = '') -> str:
        u = lambda target: escape(self.url(page, target))
        return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · CF Fieldbook</title><meta name="author" content="Faye &amp; Cove">
<meta name="description" content="Cloudflare 用途、选择与实践的持续参考。Faye &amp; Cove 的独立 Fieldbook。">
<link rel="stylesheet" href="{u('styles/site.css')}"><script defer src="{u('styles/site.js')}"></script></head>
<body class="{css_class}"><a class="skip-link" href="#main">跳到正文</a>
<header class="site-header"><a class="wordmark" href="{u('index.html')}"><strong>CF Fieldbook<span class="wordmark-dot">.</span></strong><span>用途 · 选择 · 实践</span></a>{self.nav(page)}</header>
{body}
<footer class="site-footer"><img src="{u('assets/motifs/cat-sunrise.svg')}" width="96" height="64" alt="" aria-hidden="true"><div><p>Faye &amp; Cove 的独立参考 · 本地阅读候选</p><p><a href="https://github.com/IndelibleVivi">https://github.com/IndelibleVivi</a> · <a href="{u('LICENSE-STATUS.html')}">许可状态</a></p><p class="signature">made by Faye &amp; Cove</p></div><a class="back-top" href="#main">回到页首 ↑</a></footer></body></html>'''

    def rewrite(self, soup: BeautifulSoup, path: str) -> None:
        page = str(Path(path).with_suffix('.html'))
        for node in soup.find_all(['a', 'img']):
            key = 'href' if node.name == 'a' else 'src'
            value = node.get(key, '')
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
            if rel in self.paths:
                node[key] = self.url(page, str(Path(rel).with_suffix('.html'))) + (f'#{parsed.fragment}' if parsed.fragment else '')
            elif rel in self.attachments:
                node[key] = self.url(page, rel) + (f'#{parsed.fragment}' if parsed.fragment else '')
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
        for img in list(soup.find_all('img')):
            if img.parent.name == 'p' and len(img.parent.contents) == 1:
                img.parent.unwrap()
            figure = soup.new_tag('figure')
            scroll = soup.new_tag('div', attrs={'class': 'diagram-scroll', 'tabindex': '0', 'aria-label': '可横向滚动的图示'})
            img.wrap(scroll)
            scroll.wrap(figure)
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
            figure.append(caption)

    def render_content(self, path: str) -> tuple[str, list[tuple[str, str]], str]:
        meta, body = split_frontmatter(self.texts[path])
        body = re.sub(r'<!--\s*figure:\s*([\w-]+)\s*-->', lambda m:
                      f"\n![{FIGCAP[m[1]]}](../assets/{m[1]}.svg)\n" if m[1] in FIGCAP else '', body)
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
        soup = BeautifulSoup(self.md.render(body), 'html.parser')
        h1 = soup.find('h1')
        if h1:
            h1.decompose()
        # The shared footer owns the one author signature.
        for p in list(soup.find_all('p')):
            if 'made by Faye & Cove' in p.get_text() and 'GitHub' in p.get_text():
                p.decompose()
        headings, seen = [], {}
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            label = heading.get_text()
            stem = re.sub(r'[^\w\s-]', '', label.lower()).replace(' ', '-')
            seen[stem] = seen.get(stem, 0) + 1
            ident = stem + (f'-{seen[stem] - 1}' if seen[stem] > 1 else '')
            heading['id'] = ident
            if heading.name == 'h2':
                headings.append((ident, label))
            anchor = soup.new_tag('a', attrs={'href': '#' + ident, 'class': 'heading-link', 'aria-label': '链接到：' + label})
            anchor.string = '#'
            heading.append(anchor)
        self.rewrite(soup, path)
        if path == 'diagrams/README.md':
            for diagram in self.diagrams:
                fragment = BeautifulSoup(self.md.render(f"## {diagram['title']}\n\n![{diagram['title']}](../{diagram['output']})\n\n[Mermaid 源码](../{diagram['source']})"), 'html.parser')
                self.rewrite(fragment, path)
                fragment.h2['id'] = 'diagram-' + diagram['id']
                headings.append((fragment.h2['id'], diagram['title']))
                soup.append(fragment)
        return str(soup), headings, soup.get_text(' ', strip=True)

    def notice(self, path: str) -> str:
        entry = self.entries.get(path)
        if not entry:
            return '<p class="page-note">资料维护说明 · 设计目标与当前实现请按文中的状态说明区分。</p>'
        review = entry.get('review', {})
        status = STATUS_LABELS[entry['status']]
        if entry.get('track') == 'edition':
            status = '历史报告 · ' + Path(path).stem + ' 资料快照'
        text = f"{status} · 记录核验日期 {review.get('checked_on', '未登记')}"
        scope = review.get('scope', '未登记核验范围')
        return f'<aside class="evidence-note"><strong>{escape(text)}</strong><p>{escape(scope)}。网站构建没有重新核验 Cloudflare 事实；本地测试与来源核对、云端实测分别记录。</p></aside>'

    def reader(self, path: str) -> str:
        page = str(Path(path).with_suffix('.html'))
        content, headings, plain = self.render_content(path)
        entry = self.entries.get(path, {})
        kind = KIND_LABELS.get(entry.get('kind', 'doc'), '资料')
        toc = ''.join(f'<li><a href="#{escape(ident)}">{escape(label)}</a></li>' for ident, label in headings)
        download = '' if entry.get('status') == 'withdrawn' else f'<a download href="{escape(self.url(page, path))}">下载 Markdown ↓</a>'
        files = ''
        if entry.get('kind') == 'example' and entry.get('status') == 'current':
            related = sorted(p for p in self.attachments if Path(p).parent == Path(path).parent)
            files = '<section class="example-downloads"><h2>例子附件</h2><p>在自己的本地环境检查；本站没有运行或部署入口。</p><ul>' + ''.join(
                f'<li><a download href="{escape(self.url(page, p))}">{escape(Path(p).name)} ↓</a></li>' for p in related) + '</ul></section>'
        self.search.append({'title': self.titles[path], 'url': page, 'kind': kind,
                            'text': plain, 'status': entry.get('status', 'current')})
        body = f'''<main id="main" class="reader-layout"><aside class="contents"><a class="contents-home" href="{escape(self.url(page, 'directory.html'))}">← 全部资料</a><details open><summary>本页目录</summary><ol>{toc}</ol></details><div class="reader-tools">{download}<a href="{escape(self.url(page, 'sources.html'))}">查阅来源索引 ↗</a></div></aside>
<article class="article"><header class="article-header"><p class="eyebrow">CF FIELDBOOK / {escape(kind)}</p><h1>{escape(self.titles[path])}</h1>{self.notice(path)}</header><div class="prose">{content}{files}</div><div class="reading-end"><a href="{escape(self.url(page, 'directory.html'))}">继续阅读：全部资料 →</a></div></article></main>'''
        return self.frame(page, self.titles[path], body, 'reader-page')

    def home(self) -> str:
        body = '''<main id="main" class="home"><section class="home-cover"><div class="cover-copy"><p class="eyebrow">AN INDEPENDENT CLOUDFLARE FIELDBOOK</p><h1>从手边的问题，<br>读到可检查的实践。</h1><p class="cover-deck">Cloudflare 用途、选择与实践的持续参考。<br>认识一项服务，也理解它应当放在哪里。</p><p class="cover-credit">Faye &amp; Cove <span>／</span> 2026.10</p></div><figure class="cover-art"><img src="assets/motifs/cat-sunrise.svg" alt="青色猫坐在书页般的地平线上，望向橙色日出" width="600" height="400"><figcaption>先看清问题，再决定下一步。</figcaption></figure></section>
<section class="entry-paths" aria-labelledby="entry-heading"><div class="section-intro"><p class="eyebrow">THREE WAYS IN</p><h2 id="entry-heading">从这里翻开</h2><p>不必先读完所有服务。<br>选一个与你现在有关的入口。</p></div><div class="path-list">
<a class="path" href="guides/handbook.html"><span class="path-number">01</span><div><h3>从用途开始 <span>→</span></h3><p>发布网页、安全访问、保存内容、恢复任务。<br>从一件正在做的事情认识基础设施。</p></div></a>
<a class="path" href="services/decision-models.html"><span class="path-number">02</span><div><h3>认识服务 <span>→</span></h3><p>先分清模型与接入路径，再比较限制与成本。<br>从 Clef / Jev 读一项具体选择。</p></div></a>
<a class="path" href="reports/2026-10-02.html"><span class="path-number">03</span><div><h3>本期变化 <span>→</span></h3><p>2026-10-02 新发布观察。<br>保留当时的开放状态、时间与来源。</p></div></a></div></section>
<section class="shelf"><div><p class="eyebrow">READ · INSPECT · TAKE AWAY</p><h2>沿着解释，找到依据。</h2><p>正文、精确记录和离线例子各有归属。<br>可以读，也可以带走 Markdown 与公开附件。</p></div><ul><li><a href="directory.html">全部资料与内容搜索 <span>→</span></a></li><li><a href="examples/README.html">三个离线例子 <span>→</span></a></li><li><a href="reference/implementation.html">实施参考：代码与恢复语义 <span>→</span></a></li><li><a href="diagrams/README.html">五张图：架构与资料生命周期 <span>→</span></a></li><li><a href="sources.html">来源与核验范围 <span>→</span></a></li></ul></section>
<section class="edition-strip"><p class="eyebrow">A NOTE ON THIS READING</p><p>本地阅读候选，继承阅读版 r3 的正文与来源记录。本轮建站没有重新核验服务事实，没有调用模型或部署云端服务。历史报告是有日期的资料快照。</p><a href="docs/reading-site.html">阅读与构建说明 →</a></section></main>'''
        return self.frame('index.html', '用途、选择与实践的持续参考', body, 'home-page')

    def directory(self) -> str:
        groups = []
        labels = ['用途', '手册', '服务', '比较', '实施参考', '例子', '带日期报告', '资料维护']
        for label in labels:
            items = [item for item in self.search if item['kind'] == label]
            if items:
                groups.append(f'<section class="directory-group"><h2>{label}</h2><ul>' + ''.join(
                    f'<li class="directory-item"><a href="{escape(item["url"])}">{escape(item["title"])}</a><span>{escape(STATUS_LABELS[item["status"]])}</span></li>' for item in items) + '</ul></section>')
        data = json.dumps(self.search, ensure_ascii=False).replace('<', '\\u003c')
        body = f'''<main id="main" class="directory"><header class="page-title"><p class="eyebrow">THE READING INDEX</p><h1>全部资料</h1><p>从一个词继续找，或按下面的阅读目录翻开。搜索只在你的浏览器内处理。</p></header><section class="search-box"><label for="search-input">搜索正文与标题</label><input id="search-input" type="search" placeholder="例如：任务、费用、Clef、租约" disabled><p id="search-status" role="status">启用 JavaScript 后可搜索；完整目录始终可读。</p><ol id="search-results" hidden></ol></section><div id="reading-directory">{''.join(groups)}</div><script id="search-data" type="application/json">{data}</script></main>'''
        return self.frame('directory.html', '全部资料与搜索', body)

    def sources_page(self) -> str:
        rows = ''.join(f'<li id="{escape(s["id"])}"><span class="source-id">{escape(s["id"])}</span><div><a href="{escape(s["url"])}">{escape(s["title"])}</a><p>记录查阅日期 {escape(s.get("accessed", "未登记"))} · <code>{escape(s.get("verification_scope", "未登记"))}</code></p></div></li>' for s in self.sources)
        body = f'''<main id="main" class="sources-page"><header class="page-title"><p class="eyebrow">SOURCES &amp; SCOPE</p><h1>来源与核验范围</h1><p>来源编号对应原记录。继承 r3 的 public document 核对，不构成本站的新事实核验、账户权限证明或云端实测。</p><p><a download href="catalog/sources.json">下载来源记录 JSON ↓</a></p></header><ol class="sources-list">{rows}</ol></main>'''
        return self.frame('sources.html', '来源与核验范围', body)

    def download_markdown(self, path: str) -> str:
        """Keep public relative links portable and label undistributed repo references."""
        def link(match):
            prefix, label, value = match.groups()
            parsed = urlsplit(value)
            if parsed.scheme or value.startswith('#'):
                return match[0]
            target = (self.root / Path(path).parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(self.root):
                raise ValueError(f'Link escapes repository: {path}: {value}')
            rel = target.relative_to(self.root).as_posix()
            if rel in self.paths:
                if self.entries.get(rel, {}).get('status') == 'withdrawn':
                    return f'{prefix}[{label}]({Path(parsed.path).with_suffix(".html")})'
                return match[0]
            if rel in self.attachments:
                return match[0]
            return f'{label}（仓库文件，未随阅读站分发）'
        return re.sub(r'(!?)\[([^\]]+)\]\(([^)]+)\)', link, self.texts[path])

    def write(self, path: str, text: str) -> None:
        target = self.output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')

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
        self.write('directory.html', self.directory())
        self.write('sources.html', self.sources_page())
        for path in sorted(self.attachments | {'styles/site.css', 'styles/site.js', 'assets/motifs/cat-sunrise.svg'}):
            target = self.output / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.root / path, target)
        manifest = {'schema': 'fieldbook.reading-site/1', 'state': 'local-candidate',
                    'pages': self.paths, 'attachments': sorted(self.attachments),
                    'notice': 'Read-only offline build; no new product fact verification or cloud execution.'}
        self.write('site-manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        return manifest


def build_site(root: Path = ROOT, output: Path | None = None) -> dict:
    return Site(root, output or root / '.build/site').build()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.build/site')
    args = parser.parse_args()
    result = build_site(ROOT, args.output)
    print(f'Built {len(result["pages"]) + 3} HTML reading pages at {args.output}')


if __name__ == '__main__':
    main()
