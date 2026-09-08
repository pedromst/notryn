import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from notryn_cli import copy_state, data_home, parser, process_command


class CliTests(unittest.TestCase):
    def test_random_instance_starting_with_hyphen_reaches_server_unchanged(self):
        for frozen in (False, True):
            with self.subTest(frozen=frozen), patch('sys.frozen', frozen, create=True):
                command = process_command('serve', Path('/tmp/test state'), 4783, '-random-token')
                parsed = parser().parse_args(command[1 if frozen else 2:])
                self.assertEqual(parsed.instance, '-random-token')
                self.assertEqual(parsed.data_dir, '/tmp/test state')
                self.assertEqual(parsed.command, 'serve')

    def test_platform_data_directories_and_override(self):
        root = Path('/tmp/notryn-test-home')
        root = root.resolve()
        self.assertEqual(data_home('darwin', {}, root), root / 'Library' / 'Application Support' / 'Notryn')
        self.assertEqual(data_home('linux', {}, root), root / '.local' / 'share' / 'notryn')
        self.assertEqual(data_home('linux', {'XDG_DATA_HOME': '/tmp/data'}, root), Path('/tmp/data/notryn'))
        self.assertEqual(data_home('win32', {'LOCALAPPDATA': '/tmp/local'}, root), Path('/tmp/local/Notryn'))
        self.assertEqual(data_home('linux', {'NOTRYN_HOME': '/tmp/private-notryn'}, root), Path('/tmp/private-notryn').resolve())

    def test_state_migration_copies_and_rewrites_without_touching_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / '.neura'
            destination = root / 'notryn'
            source.mkdir()
            brain = source / 'brains' / 'brain-id'
            brain.mkdir(parents=True)
            (source / 'brains.json').write_text(json.dumps({'root': str(brain)}))
            before = (source / 'brains.json').read_bytes()
            self.assertTrue(copy_state(source, destination))
            self.assertEqual((source / 'brains.json').read_bytes(), before)
            migrated = json.loads((destination / 'brains.json').read_text())
            self.assertEqual(migrated['root'], str(destination.resolve() / 'brains' / 'brain-id'))
            self.assertFalse(copy_state(source, destination))

    def test_state_migration_refuses_symbolic_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / '.neura'; source.mkdir()
            (source / 'brains.json').write_text('{}')
            (source / 'unsafe').symlink_to(root)
            with self.assertRaises(RuntimeError):
                copy_state(source, root / 'notryn')


if __name__ == '__main__':
    unittest.main()
