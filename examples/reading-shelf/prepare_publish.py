#!/usr/bin/env python3
"""Prepare only the four public shelf files; never log in or deploy."""
from pathlib import Path
import shutil

from build import DOCUMENTS, build

ROOT = Path(__file__).resolve().parent
PUBLIC_FILES = ('index.html', *(f'materials/{name}.md' for name in DOCUMENTS))


def reject_symlinks(path: Path) -> None:
    """Keep both input and output on this example's ordinary local paths."""
    for part in (path, *path.relative_to(ROOT).parents):
        candidate = part if part.is_absolute() else ROOT / part
        if candidate.is_symlink():
            raise ValueError(f'symlink is not a publish input or output: {candidate.name}')


def prepare() -> Path:
    target = ROOT / 'public'
    reject_symlinks(target)
    for relative in PUBLIC_FILES:
        source = ROOT / relative
        reject_symlinks(source)
        if not source.is_file():
            raise ValueError(f'missing public input: {relative}')
    if target.exists():
        if not target.is_dir():
            raise ValueError('public must be a directory')
        for path in target.rglob('*'):
            reject_symlinks(path)
            relative = path.relative_to(target).as_posix()
            if not ((path.is_file() and relative in PUBLIC_FILES)
                    or (path.is_dir() and relative == 'materials')):
                raise ValueError(f'unexpected file in public; inspect it before continuing: {relative}')
    build()
    for relative in PUBLIC_FILES:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    return target


if __name__ == '__main__':
    print(prepare())
