"""Explicit public example files shared by site downloads and frozen readings.

A local install, publish output or private file must never become a public input
merely because it sits next to an example's source.
"""
from pathlib import Path

EXAMPLE_FILES = {
    'api-operations': ('model.py', 'demo.py', 'example.meta.json'),
    'decision-routing': ('payloads.py', 'example.meta.json'),
    'health-worker': ('index.mjs', 'worker.test.mjs', 'wrangler.example.json', 'example.meta.json'),
    'job-state': ('model.py', 'demo.py', 'example.meta.json'),
    'reading-shelf': ('build.py', 'index.html', 'materials/welcome.md', 'materials/notes.md',
                      'materials/checklist.md', 'example.meta.json', 'prepare_publish.py',
                      'wrangler.publish.example.jsonc', 'package.json', 'package-lock.json'),
}


def example_paths(root: Path, name: str, *, include_readme: bool = False) -> tuple[str, ...]:
    """Return the declared, existing regular files, rejecting unsafe/missing inputs."""
    if name not in EXAMPLE_FILES:
        raise ValueError(f'example has no public file allowlist: {name}')
    paths = tuple(f'examples/{name}/{filename}' for filename in
                  (('README.md',) if include_readme else ()) + EXAMPLE_FILES[name])
    base = root.resolve()
    for relative in paths:
        path = base / relative
        if any(parent.is_symlink() for parent in (path, *path.parents) if parent != base and parent.is_relative_to(base)):
            raise ValueError(f'public example input must be a regular repository file: {relative}')
        if not path.is_file():
            raise ValueError(f'missing public example input: {relative}')
    return paths
