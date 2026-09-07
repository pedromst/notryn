"""Reveal saved notes through the local computer's file manager."""
import shutil
import subprocess
import sys

from store import Problem


def reveal_note(store, brain_id, relative):
    with store.lock:
        brain = store.get(brain_id)
        path = store.safe_path(brain, relative)
        if not path.is_file():
            raise Problem('This note is not on disk. Save it first, or refresh the library.', 404)
    mode = 'selected'
    try:
        if sys.platform == 'darwin':
            command = ['/usr/bin/open', '-R', str(path)]
        elif sys.platform == 'win32':
            # Explorer delegates to an existing desktop process; its exit code is not reliable.
            subprocess.Popen(['explorer.exe', '/select,', str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {'requested':True, 'mode':mode}
        elif sys.platform.startswith('linux'):
            opener = shutil.which('xdg-open')
            if not opener:
                raise Problem('No desktop folder opener is available. Install xdg-utils and a file manager.', 503)
            command = [opener, str(path.parent)]
            mode = 'folder'
        else:
            raise Problem('Opening folders is not available on this system.', 503)
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
        if result.returncode:
            raise Problem('The file manager could not open this folder. Check your desktop session.', 503)
    except (OSError, subprocess.TimeoutExpired):
        raise Problem('The file manager did not respond. Check your desktop session and try again.', 503)
    return {'requested':True, 'mode':mode}
