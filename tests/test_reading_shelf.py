"""The publication directory contains only current, explicitly public shelf files."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHELF = ROOT / 'examples/reading-shelf'
PUBLIC_FILES = {'index.html', 'materials/welcome.md', 'materials/notes.md', 'materials/checklist.md'}


class ShelfPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in (*PUBLIC_FILES, 'build.py', 'prepare_publish.py'):
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SHELF / relative, destination)

    def prepare(self):
        return subprocess.run([sys.executable, str(self.root / 'prepare_publish.py')],
                              capture_output=True, text=True)

    def test_publish_only_explicit_public_files_and_refresh_after_edit(self):
        (self.root / '.env').write_text('PRIVATE_SENTINEL')
        (self.root / 'private.txt').write_text('PRIVATE_SENTINEL')
        self.assertEqual(self.prepare().returncode, 0)
        public = self.root / 'public'
        self.assertEqual({p.relative_to(public).as_posix() for p in public.rglob('*') if p.is_file()}, PUBLIC_FILES)
        for relative in PUBLIC_FILES:
            self.assertEqual((public / relative).read_bytes(), (self.root / relative).read_bytes())
        note = self.root / 'materials/notes.md'
        old = note.read_text()
        note.write_text(old.replace('旧引用可以保留版本身份', '新句：旧引用须标日期'))
        self.assertNotIn('新句', (public / 'index.html').read_text())
        self.assertNotIn('新句', (public / 'materials/notes.md').read_text())
        self.assertEqual(self.prepare().returncode, 0)
        self.assertIn('新句', (public / 'index.html').read_text())
        self.assertEqual((public / 'materials/notes.md').read_bytes(), note.read_bytes())

    def test_unknown_public_file_is_rejected_and_preserved(self):
        public = self.root / 'public'
        public.mkdir()
        unexpected = public / 'private.txt'
        unexpected.write_text('do not remove')
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unexpected file', result.stderr)
        self.assertEqual(unexpected.read_text(), 'do not remove')
        self.assertFalse((public / 'index.html').exists())

    def test_symlink_input_and_output_are_rejected(self):
        for relative in ('materials/notes.md', 'public'):
            with self.subTest(relative=relative):
                path = self.root / relative
                original = path.read_bytes() if path.exists() else None
                if path.exists():
                    path.unlink()
                path.symlink_to(self.root / 'build.py')
                result = self.prepare()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('symlink', result.stderr)
                path.unlink()
                if original is not None:
                    path.write_bytes(original)

    def test_optional_toolchain_is_pinned_to_real_lock_and_static_directory(self):
        package = json.loads((SHELF / 'package.json').read_text())
        lock = json.loads((SHELF / 'package-lock.json').read_text())
        self.assertEqual(package['devDependencies']['wrangler'], lock['packages']['node_modules/wrangler']['version'])
        config = '\n'.join(line for line in (SHELF / 'wrangler.publish.example.jsonc').read_text().splitlines()
                           if not line.lstrip().startswith('//'))
        config = json.loads(config)
        self.assertEqual(config['assets']['directory'], './public')
        self.assertEqual(config['assets']['not_found_handling'], 'none')
        self.assertNotIn('main', config)
        self.assertNotIn('binding', config['assets'])
