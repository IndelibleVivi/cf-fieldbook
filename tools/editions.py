#!/usr/bin/env python3
"""Freeze, build and verify local publication candidates; never publish them."""
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

ROOT = Path(__file__).resolve().parents[1]
# Explicit input owners; not .env, private state, old output, dependencies or git metadata.
INPUT_DIRS = ('reports', 'guides', 'comparisons', 'services', 'use-cases', 'reference',
              'catalog', 'examples', 'assets', 'styles', 'tools', 'diagrams')
READER_DEPENDENCIES = ('docs/glossary.md', 'templates/job-recovery-task.md')
SUFFIXES = {'.md', '.json', '.mjs', '.js', '.py', '.svg', '.css', '.mmd'}
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


def included(root: Path) -> list[Path]:
    files = [root / name for name in ('package.json', 'package-lock.json', 'requirements-render.txt',
                                     *READER_DEPENDENCIES)]
    for name in INPUT_DIRS:
        for path in sorted((root / name).rglob('*')):
            if path.is_file() and path.suffix in SUFFIXES and '__pycache__' not in path.parts:
                if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                    raise ValueError(f'input must be a regular repository file: {path.relative_to(root)}')
                files.append(path)
    return files


def freeze(root: Path, ident: str) -> Path:
    from content import sync
    if sync(root, check=True):
        raise ValueError('fact blocks have drifted; run tools/content.py sync and review first')
    target = location(root, ident)
    files = included(root)
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
                    '--edition', ident, '--formats', *formats], check=True)
    verify_inputs(target)
    manifest['outputs'] = {p.relative_to(outputs).as_posix(): digest(p)
                           for p in sorted(outputs.rglob('*')) if p.is_file()}
    manifest['formats'] = formats
    manifest['build_python'] = sys.version.split()[0]
    manifest['build_packages'] = {name: version(name) for name in ('markdown-it-py', 'beautifulsoup4', 'PyYAML', 'weasyprint')}
    manifest['font_policy'] = 'System fonts; no font files distributed; layout may vary across systems.'
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('freeze', 'build', 'check'):
        child = sub.add_parser(name)
        child.add_argument('id')
        if name == 'build':
            child.add_argument('--formats', nargs='+', choices=sorted(FORMATS), default=['md', 'html', 'pdf'])
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == 'freeze':
        print(freeze(root, args.id))
    elif args.command == 'build':
        print(build(root, args.id, args.formats))
    else:
        result = check(root, args.id)
        print(f"PASS: {result['id']} input/output identity; {result.get('build_state', 'frozen-only')}")
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
