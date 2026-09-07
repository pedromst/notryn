import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop import reveal_note
from store import Store, Problem


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.folder = self.root / 'Brain with spaces'
        (self.folder / 'wiki' / 'projects').mkdir(parents=True)
        self.note = self.folder / 'wiki' / 'projects' / 'A note.md'
        self.note.write_text('# Original')
        self.store = Store(self.root / 'settings')
        self.brain = self.store.add('Read only', str(self.folder), False)
        self.store.get(self.brain['id'])['scope'] = 'wiki'

    def tearDown(self):
        self.temp.cleanup()

    def test_platform_dispatch_resolves_legacy_scope_without_writing(self):
        before = self.note.read_bytes()
        config = self.store.config.read_bytes()
        for platform in ['darwin', 'linux', 'win32']:
            with self.subTest(platform=platform), patch('desktop.sys.platform', platform), patch('desktop.shutil.which', return_value='/usr/bin/xdg-open'), patch('desktop.subprocess.run', return_value=Mock(returncode=0)) as run, patch('desktop.subprocess.Popen') as spawn:
                result = reveal_note(self.store, self.brain['id'], 'projects/A note.md')
                self.assertTrue(result['requested'])
                if platform == 'win32':
                    self.assertEqual(spawn.call_args.args[0], ['explorer.exe', '/select,', str(self.note)])
                    run.assert_not_called()
                else:
                    command = ['/usr/bin/open', '-R', str(self.note)] if platform == 'darwin' else ['/usr/bin/xdg-open', str(self.note.parent)]
                    self.assertEqual(run.call_args.args[0], command)
                    self.assertEqual(result['mode'], 'selected' if platform == 'darwin' else 'folder')
        self.assertEqual(self.note.read_bytes(), before)
        self.assertEqual(self.store.config.read_bytes(), config)

    def test_invalid_missing_and_removed_notes_never_launch(self):
        (self.folder / 'wiki' / 'link.md').symlink_to(self.note)
        with patch('desktop.subprocess.run') as run, patch('desktop.subprocess.Popen') as spawn:
            for relative in ['../outside.md', str(self.note), '.hidden.md', 'link.md', 'missing.md', None]:
                with self.subTest(path=relative), self.assertRaises(Problem):
                    reveal_note(self.store, self.brain['id'], relative)
            review = self.store.removal_preview(self.brain['id'], 'projects/A note.md', 'note')
            self.store.remove(review['id'])
            with self.assertRaises(Problem):
                reveal_note(self.store, self.brain['id'], 'projects/A note.md')
            run.assert_not_called()
            spawn.assert_not_called()
        self.assertEqual(self.note.read_text(), '# Original')

    def test_missing_desktop_and_failed_opener_report_errors(self):
        with patch('desktop.sys.platform', 'linux'), patch('desktop.shutil.which', return_value=None), self.assertRaises(Problem) as caught:
            reveal_note(self.store, self.brain['id'], 'projects/A note.md')
        self.assertEqual(caught.exception.status, 503)
        with patch('desktop.sys.platform', 'darwin'), patch('desktop.subprocess.run', return_value=Mock(returncode=1)), self.assertRaises(Problem) as caught:
            reveal_note(self.store, self.brain['id'], 'projects/A note.md')
        self.assertEqual(caught.exception.status, 503)


if __name__ == '__main__':
    unittest.main()
