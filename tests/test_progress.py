import contextlib
import hashlib
import io
import os
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from notryn_install import Releases
from notryn_progress import Progress


class Terminal(io.StringIO):
    encoding = 'utf-8'

    def isatty(self):
        return True


class ProgressTests(unittest.TestCase):
    def test_download_reports_measured_bytes_and_keeps_stdout_clean(self):
        data = b'x' * (1024 * 1024)
        release = {'tag_name': 'v0.2.0-beta.5', 'assets': [{
            'name': 'package.zip', 'state': 'uploaded', 'size': len(data),
            'digest': 'sha256:' + hashlib.sha256(data).hexdigest()}]}
        response = io.BytesIO(data)
        response.url = 'https://github.com/file'
        output, messages = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(output), contextlib.redirect_stderr(messages):
            with patch('notryn_install.urlopen', return_value=response):
                path = Releases().download(release, 'package.zip', folder)
            self.assertEqual(path.read_bytes(), data)
        self.assertEqual(output.getvalue(), '')
        text = messages.getvalue()
        for percent in [0, 25, 50, 75, 100]:
            self.assertIn(f'Downloading app: {percent}%', text)
        self.assertIn('Verifying download: done', text)
        self.assertNotIn('\r', text)
        self.assertNotIn('\x1b', text)

    def test_short_or_oversized_download_stops_without_claiming_completion(self):
        for data in [b'half', b'far too much data']:
            with self.subTest(data=data), tempfile.TemporaryDirectory() as folder:
                response = io.BytesIO(data)
                response.url = 'https://github.com/file'
                release = {'tag_name': 'v0.2.0-beta.5', 'assets': [{
                    'name': 'package.zip', 'state': 'uploaded', 'size': 8, 'digest': 'sha256:' + '0' * 64}]}
                messages = io.StringIO()
                with contextlib.redirect_stderr(messages), patch('notryn_install.urlopen', return_value=response):
                    with self.assertRaises(RuntimeError):
                        Releases().download(release, 'package.zip', folder)
                self.assertIn('Downloading app: stopped', messages.getvalue())
                self.assertNotIn('100%', messages.getvalue())
                self.assertNotIn('Verifying download: done', messages.getvalue())

    def test_checksum_failure_is_distinct_from_a_completed_transfer(self):
        response = io.BytesIO(b'bad hash')
        response.url = 'https://github.com/file'
        release = {'tag_name': 'v0.2.0-beta.5', 'assets': [{
            'name': 'package.zip', 'state': 'uploaded', 'size': 8, 'digest': 'sha256:' + '0' * 64}]}
        messages = io.StringIO()
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stderr(messages):
            with patch('notryn_install.urlopen', return_value=response), self.assertRaisesRegex(RuntimeError, 'checksum'):
                Releases().download(release, 'package.zip', folder)
        self.assertIn('Downloading app: 100%', messages.getvalue())
        self.assertIn('Verifying download: stopped', messages.getvalue())
        self.assertNotIn('Verifying download: done', messages.getvalue())

    def test_indicator_moves_while_a_stage_blocks_and_stops_after_cancellation(self):
        terminal = Terminal()
        with patch.dict(os.environ, {'TERM': 'xterm-256color', 'NO_COLOR': '1'}):
            with self.assertRaises(KeyboardInterrupt):
                with Progress('Checking app', stream=terminal):
                    time.sleep(.3)
                    self.assertGreater(len(terminal.getvalue().split('\r')), 2)
                    raise KeyboardInterrupt()
        text = terminal.getvalue()
        self.assertIn('stopped', text)
        self.assertNotIn('✓', text)
        self.assertNotIn('\x1b', text)
        time.sleep(.2)
        self.assertEqual(terminal.getvalue(), text)

    def test_narrow_resized_terminal_does_not_wrap_or_invent_percentage(self):
        terminal = Terminal()
        with patch.dict(os.environ, {'TERM': 'xterm', 'NO_COLOR': '1'}):
            with patch('notryn_progress.os.get_terminal_size', return_value=os.terminal_size((80, 24))):
                with Progress('Downloading app', 1024, terminal) as progress:
                    progress.update(512)
                    terminal.seek(0); terminal.truncate()
                    with patch('notryn_progress.os.get_terminal_size', return_value=os.terminal_size((32, 24))):
                        progress._render()
                        self.assertLessEqual(len(terminal.getvalue().strip('\r\n')), 31)
                        self.assertIn('50%', terminal.getvalue())
        self.assertIn('stopped', terminal.getvalue())
        self.assertNotIn('100%', terminal.getvalue())

    def test_dumb_terminal_and_ascii_encoding_remain_readable(self):
        for term, encoding in [('dumb', 'utf-8'), ('xterm', 'ascii')]:
            with self.subTest(term=term), patch.dict(os.environ, {'TERM': term, 'NO_COLOR': '1'}):
                terminal = Terminal()
                terminal.encoding = encoding
                with Progress('Unpacking app', stream=terminal):
                    pass
                text = terminal.getvalue()
                text.encode(encoding)
                self.assertIn('Unpacking app', text)
                self.assertNotIn('\x1b', text)
                if term == 'dumb':
                    self.assertNotIn('\r', text)

    def test_private_download_shows_activity_without_a_fake_percentage(self):
        data = b'private sample'
        release = {'tag_name': 'v0.2.0-beta.5', 'assets': [{
            'name': 'package.zip', 'state': 'uploaded', 'size': len(data),
            'digest': 'sha256:' + hashlib.sha256(data).hexdigest()}]}
        messages = io.StringIO()
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stderr(messages):
            def download(*args, **kwargs):
                Path(folder, 'package.zip').write_bytes(data)
            with patch('notryn_install.shutil.which', return_value='/synthetic/gh'), patch('notryn_install.run', side_effect=download):
                Releases(private=True).download(release, 'package.zip', folder)
        self.assertIn('Downloading app (private release): done', messages.getvalue())
        self.assertNotIn('%', messages.getvalue())


if __name__ == '__main__':
    unittest.main()
