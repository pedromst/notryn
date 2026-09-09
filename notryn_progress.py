"""Small terminal progress displays; no dependencies and no output on import."""
import os
import shutil
import sys
import threading
import time


class Progress:
    """A measured download bar or an activity indicator for an unmeasured stage."""

    def __init__(self, label, total=None, stream=None):
        if total is not None and total <= 0:
            raise ValueError('Progress needs a positive download size.')
        self.label = label
        self.total = total
        self.stream = stream if stream is not None else sys.stderr
        self.interactive = self.stream.isatty() and os.environ.get('TERM') != 'dumb'
        self.color = self.interactive and 'NO_COLOR' not in os.environ
        try:
            '⠋✓━'.encode(self.stream.encoding or 'utf-8')
            self.unicode = True
        except (UnicodeError, AttributeError):
            self.unicode = False
        self.count = 0
        self.started = 0
        self.frame = 0
        self.last_width = 0
        self.bucket = 0
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.thread = None

    def _write(self, text):
        try:
            if not self.unicode:
                text = text.replace('·', '/')
            self.stream.write(text)
            self.stream.flush()
        except (OSError, ValueError):
            # Closing a progress-output pipe must not interrupt a file operation.
            pass

    def _width(self):
        try:
            return os.get_terminal_size(self.stream.fileno()).columns
        except (OSError, ValueError, AttributeError):
            return shutil.get_terminal_size(fallback=(80, 24)).columns

    def _line(self, finished=None):
        elapsed = max(0, time.monotonic() - self.started)
        if finished is not None:
            mark = ('✓' if self.unicode else 'OK') if finished else '!'
            suffix = f'  {elapsed:.0f}s' if finished else '  stopped'
            if self.total and finished:
                suffix = f'  100% · {self.count / 1048576:.1f} MB · {elapsed:.0f}s'
            return f'  {mark} {self.label}{suffix}'
        frames = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏' if self.unicode else '|/-\\'
        mark = frames[self.frame % len(frames)]
        if not self.total:
            return f'  {mark} {self.label}  {elapsed:.0f}s'
        percent = min(100, self.count * 100 // self.total)
        size = f'{self.count / 1048576:.1f}/{self.total / 1048576:.1f} MB'
        speed = f' · {self.count / 1048576 / elapsed:.1f} MB/s' if self.count and elapsed >= 1 else ''
        width = self._width()
        if width < 64:
            return f'  {mark} {self.label}  {percent:3d}% · {size}'
        length = min(22, max(8, width - len(self.label) - len(size) - len(speed) - 21))
        filled = length * self.count // self.total
        bar = ('━' if self.unicode else '=') * filled + ('─' if self.unicode else '-') * (length - filled)
        return f'  {mark} {self.label}  {bar} {percent:3d}% · {size}{speed}'

    def _render(self, finished=None):
        text = self._line(finished)
        if self.interactive:
            # Leave the last terminal column free so the line cannot wrap.
            width = max(1, self._width() - 1)
            text = text[:width]
            padding = ' ' * max(0, min(self.last_width, width) - len(text))
            styled = ('\033[36m' + text + '\033[0m') if self.color else text
            self._write('\r' + styled + padding + ('\n' if finished is not None else ''))
            self.last_width = len(text)
        else:
            # Logs and redirected output remain plain, without control sequences.
            if finished is not None:
                state = 'done' if finished else 'stopped'
                self._write(f'  {self.label}: {state} ({time.monotonic() - self.started:.0f}s).\n')
            elif self.total:
                self._write(f'  {self.label}: {self.count * 100 // self.total}% ({self.count / 1048576:.1f}/{self.total / 1048576:.1f} MB).\n')
            else:
                self._write(f'  {self.label}...\n')

    def _animate(self):
        while not self.stop.wait(.12):
            with self.lock:
                self.frame += 1
                self._render()

    def __enter__(self):
        self.started = time.monotonic()
        self._render()
        if self.interactive:
            self.thread = threading.Thread(target=self._animate, daemon=True)
            self.thread.start()
        return self

    def update(self, count):
        with self.lock:
            self.count = max(self.count, min(count, self.total))
            bucket = self.count * 4 // self.total
            if not self.interactive and bucket > self.bucket:
                self.bucket = bucket
                self._render()

    def __exit__(self, kind, error, traceback):
        self.stop.set()
        if self.thread:
            self.thread.join()
        with self.lock:
            self._render(finished=kind is None and (self.total is None or self.count == self.total))
        return False


def heading(action, version, system, arch):
    stream = sys.stderr
    color = stream.isatty() and os.environ.get('TERM') != 'dumb' and 'NO_COLOR' not in os.environ
    brand = '\033[1;36mnotryn\033[0m' if color else 'notryn'
    print(f'\n  {brand}  {action} {version}\n  {system} / {arch}\n', file=stream, flush=True)
