#!/usr/bin/env python3
"""Shared structure for the published families: one source of truth.

`catalog/publications.json` owns the editorial arrangement of the three
publication families (report / handbook / comparison): which entries they read,
their cover copy, their semantic chapter configuration and the stable product
reading targets. This module reads that file plus the Markdown `<!-- chapter: -->`
markers, so the reading site and the frozen editions cannot drift into two
different inventories.

Markdown remains the only body authority. Nothing here copies long prose or
forces the sources to be split paragraph by paragraph: chapters carry a stable
ID marker, while their visible number is display order only.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLICATIONS_PATH = 'catalog/publications.json'
RELEASES_PATH = 'catalog/publication-releases.json'

# Injected by tools/render.py (which sets its own module-global ROOT to the
# frozen snapshot) so the same reader works on the live tree and inside a
# frozen edition's inputs/.
CHAPTER_MARKER = re.compile(r'^\s*<!--\s*chapter:\s*([\w.-]+)\s*-->\s*$')
NUMBERED = re.compile(r'^(\d{2})\s*/\s*(.+)$')


def slug(text: str) -> str:
    """The legacy heading slug, preserved as the stable in-page anchor."""
    return re.sub(r'[^\w\s-]', '', text.lower()).replace(' ', '-')


def load(root: Path | None = None) -> dict:
    base = (root or ROOT).resolve()
    path = base / PUBLICATIONS_PATH
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema') != 'fieldbook.publications/1':
        raise ValueError('unsupported publications schema')
    return data


def families(data: dict) -> list[dict]:
    return list(data['families'])


def family(data: dict, key: str) -> dict:
    for item in data['families']:
        if item['id'] == key:
            return item
    raise ValueError(f'unknown publication family: {key}')


def default_family(data: dict) -> dict:
    key = data.get('default_family')
    if key:
        return family(data, key)
    return data['families'][0]


def source_entry(fam: dict) -> str:
    return fam['source_entry']


def chapter_config(fam: dict) -> dict:
    return fam.get('chapters', {})


def product_rows(fam: dict) -> list[dict]:
    return list(fam.get('product_reading', []))


def releases(root: Path | None = None) -> dict:
    """The explicit release registry. An empty registry means nothing is released;
    a local candidate is never claimed as a distributed edition."""
    base = (root or ROOT).resolve()
    path = base / RELEASES_PATH
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema') != 'fieldbook.publication-releases/1':
        raise ValueError('unsupported publication-releases schema')
    for record in data.get('releases', []):
        if record.get('state') != 'released' or not record.get('files'):
            raise ValueError('release registry requires reviewed, distributed files')
        for artifact in record['files'].values():
            if not artifact['url'].startswith('https://') or not re.fullmatch(r'[a-f0-9]{64}', artifact['sha256']):
                raise ValueError('release artifact needs a public URL and checked output identity')
    for family_id, release_id in data.get('latest', {}).items():
        if not any(record.get('id') == release_id and record.get('family') == family_id for record in data.get('releases', [])):
            raise ValueError('latest must point to a registered release of this family')
    return data


def released_for(data: dict, family_id: str) -> list[dict]:
    return [r for r in data.get('releases', []) if r.get('family') == family_id]


def entry_map(root: Path | None = None) -> dict:
    base = (root or ROOT).resolve()
    catalog = json.loads((base / 'catalog/entries.json').read_text(encoding='utf-8'))
    return {item['id']: item for item in catalog['entries']}


def entry_path(root: Path, entry_id: str) -> str | None:
    return entry_map(root).get(entry_id, {}).get('path')


def frontmatter_scalar(text: str, key: str) -> str | None:
    """Read one scalar from YAML frontmatter without importing a YAML library."""
    match = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if not match:
        return None
    for line in match[1].splitlines():
        field = re.match(rf'^{re.escape(key)}:\s*(.+?)\s*$', line)
        if field:
            return field[1].strip().strip('"\'')
    return None


def report_identity(text: str, entry_id: str) -> dict:
    """Report title/date/token come from the manuscript identity, never a hardcoded
    date and never the private author signature."""
    body = re.split(r'^---\n.*?\n---\n', text, maxsplit=1, flags=re.S)
    body = body[1] if len(body) > 1 else text
    match = re.search(r'^#\s+(.+)$', body, re.M)
    title = match[1].strip() if match else entry_id
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', title)
    date = date_match[1] if date_match else (frontmatter_scalar(text, 'source_cutoff') or entry_id)
    token = slug(re.sub(r'\s*·.*$', '', re.sub(r'[（(].*$', '', title)))[:40] or entry_id
    return {'title': title, 'date': date, 'token': token}


def parse_chapters(text: str, config: dict) -> list[dict]:
    """Every meaningful `##` heading becomes a chapter.

    A preceding `<!-- chapter: ID -->` supplies the stable ID; its absence
    yields a default anchor from the heading slug and an empty type. Nothing is
    ever indexed positionally into a `types[index]` array.
    """
    chapters: list[dict] = []
    pending: str | None = None
    order = 0
    for line in text.splitlines():
        marker = CHAPTER_MARKER.match(line)
        if marker:
            pending = marker[1]
            continue
        if not line.startswith('## '):
            continue
        raw = re.sub(r'^\d+\s*/\s*', '', line[3:].strip())
        if raw in {'来源索引', '关于这一版', '术语小词表'}:
            pending = None
            continue
        order += 1
        numbered = NUMBERED.match(line[3:].strip())
        ident = pending or slug(raw)
        pending = None
        chapters.append({
            'id': ident,
            'order': order,
            'number': numbered[1] if numbered else '',
            'title': raw,
            'anchor': slug(raw),          # legacy in-page anchor
            'type': config.get(ident, ''),
        })
    return chapters


def figures(text: str) -> list[str]:
    """`assets/<name>.svg` figures referenced by controlled `figure:` comments."""
    names = dict.fromkeys(re.findall(r'<!--\s*figure:\s*([\w-]+)\s*-->', text))
    return [f'assets/{name}.svg' for name in names]


def local_links(text: str, manuscript_path: str) -> list[str]:
    """Repository-relative Markdown links, resolved against the manuscript's directory."""
    base = Path(manuscript_path).parent
    out = []
    for target in re.findall(r'\]\(([^)\s]+)\)', text):
        if target.startswith(('http://', 'https://', '#', 'mailto:')):
            continue
        resolved = os.path.normpath(str(base / target.split('#')[0])).replace(os.sep, '/')
        if '..' not in Path(resolved).parts and resolved not in out:
            out.append(resolved)
    return out


def readings_for(root: Path, fam: dict) -> list[str]:
    """The explicit source entries this family reads, plus the figures and linked
    example directories its own manuscripts reference. Every returned path sits
    under the freeze input allowlist; shared dependencies (glossary, catalog,
    styles, motifs) are copied separately."""
    entries = [source_entry(fam), *fam.get('readings', []), *fam.get('practice', [])]
    index = entry_map(root)
    paths: list[str] = []
    for ident in entries:
        path = index.get(ident, {}).get('path')
        if not path:
            raise ValueError(f'{fam["id"]}: unknown catalog entry {ident}')
        if path not in paths:
            paths.append(path)
    extra: list[str] = []
    for path in paths:
        if path.endswith('.md'):
            text = (root / path).read_text(encoding='utf-8')
            extra += figures(text)
            for link in local_links(text, path):
                top = Path(link).parts[0]
                if top == 'examples' and link.endswith('README.md'):
                    directory = Path(link).parent
                    for candidate in sorted((root / directory).rglob('*')):
                        if candidate.is_file():
                            extra.append(candidate.relative_to(root).as_posix())
                elif top in {'assets', 'practice', 'use-cases', 'comparisons', 'services', 'guides',
                             'reference', 'reports', 'examples'}:
                    extra.append(link)
    for relative in extra:
        if (root / relative).is_file() and relative not in paths:
            paths.append(relative)
    return paths


class Collection:
    """Chapter and product structure read from the live tree or a frozen snapshot."""

    def __init__(self, root: Path, data: dict):
        self.root = root.resolve()
        self.data = data
        self._chapters: dict[str, list[dict]] = {}
        self._paths: dict[str, str | None] = {}

    def families(self) -> list[dict]:
        return families(self.data)

    def family(self, key: str) -> dict:
        return family(self.data, key)

    def default_family(self) -> dict:
        return default_family(self.data)

    def entry_path(self, entry_id: str) -> str | None:
        if entry_id not in self._paths:
            self._paths[entry_id] = entry_path(self.root, entry_id)
        return self._paths[entry_id]

    def text(self, entry_id: str) -> str:
        path = self.entry_path(entry_id)
        if not path:
            raise ValueError(f'unknown catalog entry: {entry_id}')
        return (self.root / path).read_text(encoding='utf-8')

    def chapters(self, fam: dict) -> list[dict]:
        key = source_entry(fam)
        if key not in self._chapters:
            self._chapters[key] = parse_chapters(self.text(key), chapter_config(fam))
        return self._chapters[key]

    def chapter(self, fam: dict, ident: str) -> dict:
        for item in self.chapters(fam):
            if item['id'] == ident:
                return item
        raise ValueError(f'{fam["id"]}: unknown chapter ID {ident!r}')

    def product_rows(self, fam: dict) -> list[dict]:
        return product_rows(fam)
