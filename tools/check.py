#!/usr/bin/env python3
"""Offline editorial checks. Does not probe URLs or inspect a cloud account."""
from __future__ import annotations
from datetime import date
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'blog.cloudflare.com', 'developers.cloudflare.com', 'www.cloudflare.com', 'docs.typesafe.ai', 'openrouter.ai', 'vercel.com', 'huggingface.co', 'developer.mozilla.org', 'modelcontextprotocol.io'}


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    sources = json.loads((root / 'catalog/sources.json').read_text())
    ids = {s['id'] for s in sources}
    if len(ids) != len(sources):
        errors.append('duplicate source ID')
    for source in sources:
        if not re.fullmatch(r'S\d{2,3}', source['id']):
            errors.append(f"bad source ID: {source['id']}")
        uri = urlparse(source['url'])
        if uri.scheme != 'https' or uri.hostname not in ALLOWED:
            errors.append(f"unapproved source URL: {source['id']}")
        try:
            date.fromisoformat(source['accessed'])
        except ValueError:
            errors.append(f"bad checked date: {source['id']}")
    for name in ['reports/2026-10-02.md', 'guides/handbook.md', 'reference/implementation.md', 'comparisons/clef-vs-jev.md']:
        text = (root / name).read_text()
        refs = set(re.findall(r'\[(S\d{2,3})\]', text))
        if refs - ids:
            errors.append(f'{name}: missing source IDs {sorted(refs - ids)}')
        if 'source_cutoff: 2026-10-02' not in text:
            errors.append(f'{name}: source cutoff missing')
        if '<!-- SOURCES -->' not in text:
            errors.append(f'{name}: source boundary missing')
        if any(marker in text for marker in ['', '~~~~~~~~~~~~~~~~', 'TODO', 'TBD']):
            errors.append(f'{name}: unresolved publishing marker')
        # All known relative file hyperlinks must resolve. Hash-only links are local anchors.
        for url in re.findall(r'\]\(([^)]+)\)', text):
            if not url.startswith(('https://', 'http://', '#')):
                if not ((root / name).parent / url.split('#')[0]).exists():
                    errors.append(f'{name}: broken file link {url}')
    launches = json.loads((root / 'catalog/launches.json').read_text())
    if len({x['id'] for x in launches}) != len(launches):
        errors.append('duplicate launch ID')
    for item in launches:
        if not set(item['sources']) <= ids:
            errors.append(f"launch {item['id']}: unknown source")
        verified = date.fromisoformat(item['verified_on'])
        if item['announced_on'] and date.fromisoformat(item['announced_on']) > verified:
            errors.append(f"launch {item['id']}: announcement after verification")
        for event in item['effective_events']:
            if event.get('date'):
                date.fromisoformat(event['date'])
    worker = (root / 'examples/health-worker/index.mjs').read_text().strip()
    implementation = (root / 'reference/implementation.md').read_text()
    if worker not in implementation:
        errors.append('health Worker source and implementation reference have drifted')
    for name in ['reports/2026-10-02.md', 'guides/handbook.md']:
        reader = (root / name).read_text()
        if 'author: Faye & Cove' not in reader or 'made by Faye & Cove' not in reader:
            errors.append(f'{name}: author credit missing')
        for figure in re.findall(r'<!-- figure: ([\w-]+) -->', reader):
            if not (root / 'assets' / f'{figure}.svg').is_file():
                errors.append(f'{name}: missing figure {figure}')
    if any(p.suffix.lower() in {'.ttf', '.otf', '.ttc', '.woff', '.woff2'} for p in root.rglob('*')
           if not set(p.relative_to(root).parts) & {'.venv', 'node_modules', '.build', '.git'}):
        errors.append('font files must not be distributed')
    config = json.loads((root / 'examples/health-worker/wrangler.example.json').read_text())
    if config.get('workers_dev') or config.get('routes'):
        errors.append('example unexpectedly exposes a public route')
    return errors


if __name__ == '__main__':
    problems = validate()
    if problems:
        print('\n'.join(problems), file=sys.stderr)
        sys.exit(1)
    print('PASS: source IDs, dates, local links, publication markers, example consistency.')
    print('Scope: offline only; not URL reachability, full secret scanning, or cloud acceptance.')
