#!/usr/bin/env python3
"""Freeze, build and verify local publication candidates; never publish them.

One family per edition. `--publication <family>` selects it (defaults to
`default_family` in catalog/publications.json); `--all` freezes/builds every
family as separate candidate IDs in one command, preserving the old
"three books at once" convenience. Each candidate records the readings it
actually needs, so freezing one family does not read or package unrelated
manuscripts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import publications as pub

ROOT = Path(__file__).resolve().parents[1]
# Explicit input owners; not .env, private state, old output, dependencies or git metadata.
INPUT_DIRS = ('reports', 'guides', 'comparisons', 'services', 'use-cases', 'reference',
              'catalog', 'examples', 'assets', 'styles', 'tools', 'diagrams', 'practice')
READER_DEPENDENCIES = ('docs/glossary.md', 'templates/job-recovery-task.md')
# The fact-block projector always imports this example's cost function.
CONTENT_DEPENDENCIES = ('examples/decision-routing/payloads.py',)
# Fixed presentation assets every family's cover/colophon renders.
MOTIF_DEPENDENCIES = ('assets/motifs/cat-sunrise.svg',)
SUFFIXES = {'.md', '.json', '.mjs', '.js', '.py', '.svg', '.css', '.mmd', '.html'}
FORMATS = {'md', 'html', 'pdf'}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def location(root: Path, ident: str) -> Path:
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,79}', ident) or '..' in ident:
        raise ValueError('edition ID must be a short lowercase name, not a path')
    target = root / '.build' / 'editions' / ident
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('edition path escapes repository')
    return target


def _add_dir(files: list[Path], root: Path, name: str) -> list[Path]:
    """Allow only regular repository files under one inferred distribution directory."""
    for path in sorted((root / name).rglob('*')):
        if path.is_file() and path.suffix in SUFFIXES and '__pycache__' not in path.parts:
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                raise ValueError(f'input must be a regular repository file: {path.relative_to(root)}')
            files.append(path)
    return files


def included(root: Path, fam: dict) -> list[Path]:
    """Close the freeze over the family's actual manuscript, figures, glossary,
    sources and needed tools, and cover the directories those references reach.
    Unrelated prose and the whole maintenance-doc tree are not packaged."""
    files = [root / name for name in ('package.json', 'package-lock.json', 'requirements-render.txt',
                                      pub.PUBLICATIONS_PATH, *READER_DEPENDENCIES,
                                      *CONTENT_DEPENDENCIES, *MOTIF_DEPENDENCIES)]
    allowed = set(INPUT_DIRS)
    for relative in pub.readings_for(root, fam):
        top = Path(relative).parts[0]
        if top not in allowed:
            raise ValueError(f'{fam["id"]}: reading {relative} is outside the input allowlist')
        path = root / relative
        if path.suffix in SUFFIXES:
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                raise ValueError(f'input must be a regular repository file: {relative}')
            files.append(path)
        else:
            _add_dir(files, root, top)
    # The shared tools (including publications.py) always travel with the renderer.
    _add_dir(files, root, 'tools')
    # The catalog holds the exact cross-page data the renderer resolves entry
    # paths and source metadata from; it is small and always required.
    _add_dir(files, root, 'catalog')
    # Report/HTML presentation styles and the figure motifs the renderer embeds.
    _add_dir(files, root, 'styles')
    seen, unique = set(), []
    for path in files:
        if path.is_file() and path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def freeze(root: Path, ident: str, family_key: str | None = None) -> Path:
    data = pub.load(root)
    fam = pub.Collection(root, data).family(family_key or data.get('default_family'))
    from content import PAGES, project_markdown
    readings = pub.readings_for(root, fam)
    changed = [path for path in readings if path in PAGES
               and (root / path).read_text() != project_markdown(root, path)]
    if changed:
        raise ValueError('fact blocks have drifted: ' + ', '.join(changed))
    target = location(root, ident)
    files = included(root, fam)
    # mkdir deliberately refuses an existing edition, even one that did not finish building.
    target.mkdir(parents=True, exist_ok=False)
    snapshot = target / 'inputs'
    records = {}
    for path in files:
        relative = path.relative_to(root).as_posix()
        dest = snapshot / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
        records[relative] = digest(dest)
    revision = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    manifest = {
        'schema': 'fieldbook.edition/1', 'id': ident, 'state': 'local-candidate',
        'family': fam['id'], 'label': fam['label'],
        'source_entry': pub.source_entry(fam),
        'as_of': pub.frontmatter_scalar((root / pub.entry_path(root, pub.source_entry(fam))).read_text(), 'source_cutoff'),
        'readings': pub.readings_for(root, fam),
        'frozen_at': datetime.now(timezone.utc).isoformat(),
        'source_commit': revision.stdout.strip() if revision.returncode == 0 else None,
        'source_identity': 'input_digests are authoritative, including uncommitted edits',
        'evidence_scope': 'Inherited source dates; freezing is not factual review or release approval.',
        'input_digests': records,
    }
    (target / 'edition.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return target


def verify_inputs(target: Path) -> dict:
    manifest = json.loads((target / 'edition.json').read_text())
    snapshot = (target / 'inputs').resolve()
    expected = manifest['input_digests']
    actual = {p.relative_to(snapshot).as_posix() for p in snapshot.rglob('*')
              if p.is_file()}
    if actual != set(expected):
        raise ValueError('frozen input inventory changed')
    for relative, value in expected.items():
        path = snapshot / relative
        if path.is_symlink() or not path.resolve().is_relative_to(snapshot) or digest(path) != value:
            raise ValueError(f'frozen input changed: {relative}')
    return manifest


def build(root: Path, ident: str, formats: list[str]) -> Path:
    if not formats or not set(formats) <= FORMATS:
        raise ValueError('formats must be md, html and/or pdf')
    target = location(root, ident)
    manifest = verify_inputs(target)
    outputs = target / 'outputs'
    if outputs.exists():
        raise ValueError('edition outputs already exist; use a new edition ID for a changed build')
    snapshot = target / 'inputs'
    subprocess.run([sys.executable, '-B', str(snapshot / 'tools/render.py'),
                    '--snapshot', str(snapshot), '--output', str(outputs),
                    '--edition', ident, '--family', manifest['family'],
                    '--formats', *formats], check=True)
    verify_inputs(target)
    manifest['outputs'] = {p.relative_to(outputs).as_posix(): digest(p)
                           for p in sorted(outputs.rglob('*')) if p.is_file()}
    manifest['formats'] = formats
    manifest['build_python'] = sys.version.split()[0]
    manifest['build_packages'] = {name: version(name) for name in
                                  ('markdown-it-py', 'beautifulsoup4', 'PyYAML',
                                   'weasyprint', 'fonttools', 'pydyf')}
    manifest['font_policy'] = ('System fonts; PDF embeds identity CID CFF as CIDFontType0C; '
                               'no standalone font files distributed; layout may vary across systems.')
    manifest['build_state'] = 'built-local-candidate'
    (target / 'edition.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return outputs


def check(root: Path, ident: str) -> dict:
    target = location(root, ident)
    manifest = verify_inputs(target)
    if 'outputs' in manifest:
        outputs = target / 'outputs'
        actual = {p.relative_to(outputs).as_posix() for p in outputs.rglob('*') if p.is_file()}
        if actual != set(manifest['outputs']):
            raise ValueError('edition output inventory changed')
        for relative, value in manifest['outputs'].items():
            path = outputs / relative
            if path.is_symlink() or not path.resolve().is_relative_to(outputs.resolve()) or digest(path) != value:
                raise ValueError(f'edition output changed: {relative}')
    return manifest


def _family_keys(root: Path, args) -> list[str]:
    data = pub.load(root)
    if getattr(args, 'all', False):
        return [fam['id'] for fam in pub.families(data)]
    if args.publication:
        pub.family(data, args.publication)  # validate early
        return [args.publication]
    return [data.get('default_family') or pub.families(data)[0]['id']]


def _label(key: str) -> str:
    return f'-{key}' if key else ''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('freeze', 'build', 'check'):
        child = sub.add_parser(name)
        child.add_argument('id')
        if name == 'freeze':
            child.add_argument('--publication', default=None,
                               help='publication family to freeze (default: publications.json default_family)')
        if name != 'check':
            child.add_argument('--all', action='store_true',
                               help='freeze/build every family as separate candidate IDs')
        if name == 'build':
            child.add_argument('--formats', nargs='+', choices=sorted(FORMATS), default=['md', 'html', 'pdf'])
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == 'check':
        result = check(root, args.id)
        print(f"PASS: {result['id']} input/output identity; {result.get('build_state', 'frozen-only')}")
        return 0
    if args.command == 'build':
        if args.all:
            group = json.loads((location(root, args.id) / 'edition-set.json').read_text())
            identifiers = group['editions']
        else:
            identifiers = [args.id]
        for ident in identifiers:
            print(build(root, ident, args.formats))
    else:
        keys = _family_keys(root, args)
        if len(keys) > 1:
            group_path = location(root, args.id)
            group_path.mkdir(parents=True, exist_ok=False)
        identifiers = []
        for key in keys:
            ident = args.id + _label(key if len(keys) > 1 else '')
            print(freeze(root, ident, key))
            identifiers.append(ident)
        if len(keys) > 1:
            (group_path / 'edition-set.json').write_text(json.dumps(
                {'schema': 'fieldbook.edition-set/1', 'id': args.id, 'editions': identifiers}, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
