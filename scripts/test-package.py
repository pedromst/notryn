"""Exercise the built package with disposable state, never personal Brains."""
import hashlib
import socket
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notryn_install import Installation, host_target, run, safe_extract
from notryn_version import VERSION

archive = Path(sys.argv[1]).resolve()
system, arch = host_target()
class BuiltRelease:
    private = True
    def release(self, *args, **kwargs): return {'tag_name': 'v' + VERSION}
    def download(self, *args, **kwargs):
        checksum = Path(str(archive) + '.sha256').read_text().split()[0]
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == checksum
        return archive

with tempfile.TemporaryDirectory(prefix='notryn-lifecycle-') as temporary:
    home = Path(temporary) / 'Home with spaces'
    data = Path(temporary) / 'private state'
    installation = Installation(home, (system, arch), data)
    note = data / 'brains' / 'Test Brain' / 'note.md'
    note.parent.mkdir(parents=True);note.write_text('# Keep me\n')
    (data / 'brains.json').write_text('{"brains": []}')
    # Existing alpha layout exercises migration plus real backup/rollback.
    installation.app.parent.mkdir(parents=True)
    legacy = safe_extract(archive, Path(temporary) / 'legacy', 'Notryn-' + VERSION if system == 'linux' else 'Notryn.app')
    legacy.rename(installation.app)
    installation.install(BuiltRelease())
    assert run([installation.bin, 'version']) == VERSION
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0));port = sock.getsockname()[1]
    try:
        run([installation.bin, 'start', '--data-dir', data, '--port', str(port)])
        run([installation.bin, 'status', '--data-dir', data])
        try:
            installation.install(BuiltRelease())
            raise AssertionError('Live installation must be refused')
        except RuntimeError as exc:
            assert 'quit Notryn' in str(exc)
    finally:
        run([installation.bin, 'stop', '--data-dir', data])
    installation.rollback()
    assert run([installation.bin, 'version']) == VERSION
    installation.rollback()
    installation.uninstall()
    assert not installation.app.exists()
    assert note.read_text() == '# Keep me\n'
    assert (data / 'brains.json').read_text() == '{"brains": []}'
    print('PASS: package, version, isolated start/status/stop, live-app refusal, rollback twice, uninstall and note preservation.')
