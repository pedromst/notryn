#!/usr/bin/env python3
"""Start a packaged Windows server, write a note, and read the Brain back."""
import argparse
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


def find_programs(root):
    exes = list(Path(root).rglob('notryn.exe'))
    sidecar = next((path for path in exes if path.parent.name.lower() == 'notryn' and path.parent.parent.name.lower() == 'resources'), None)
    gui = next((path for path in exes if path.resolve() != (sidecar.resolve() if sidecar else None)), None)
    if sidecar is None or gui is None:
        names = ', '.join(str(path) for path in exes) or 'none'
        raise SystemExit('Package is missing Notryn.exe or resources/notryn/notryn.exe. Found: ' + names)
    return gui, sidecar


def request(port, path, token=None, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {}
    if payload is not None:
        headers['Origin'] = f'http://127.0.0.1:{port}'
        headers['X-Notryn-Token'] = token
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        body = error.read().decode(errors='replace')
        raise SystemExit(f'{path} returned {error.code}: {body}') from error


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--zip')
    source.add_argument('--exe')
    source.add_argument('--port', type=int)
    parser.add_argument('--brains')
    args = parser.parse_args()
    temporary = tempfile.TemporaryDirectory(prefix='notryn-windows-smoke-')
    try:
        if args.port:
            brains = Path(args.brains or (Path(temporary.name) / 'Brains'))
            brains.mkdir(parents=True, exist_ok=True)
            exercise(args.port, brains)
            return
        if args.zip:
            destination = Path(temporary.name) / 'package'
            with zipfile.ZipFile(args.zip) as archive:
                for info in archive.infolist():
                    name = info.filename.replace('\\', '/')
                    if name.startswith('/') or reparse(name):
                        raise SystemExit('Archive path refused: ' + name)
                archive.extractall(destination)
            gui, sidecar = find_programs(destination)
        else:
            sidecar = Path(args.exe).resolve()
            if sidecar.parent.name.lower() != 'notryn' or sidecar.parent.parent.name.lower() != 'resources':
                raise SystemExit('Pass resources/notryn/notryn.exe from an installed or unpacked package.')
            gui, sidecar = find_programs(sidecar.parent.parent.parent)
        print('GUI:', gui)
        print('Server:', sidecar)
        data = Path(temporary.name) / 'state'
        brains = Path(temporary.name) / 'Brains'
        data.mkdir()
        brains.mkdir()
        port = free_port()
        log = data / 'manual.log'
        started = subprocess.list2cmdline([str(sidecar), 'start', '--port', str(port), '--data-dir', str(data)])
        print(started)
        completed = subprocess.run([str(sidecar), 'start', '--port', str(port), '--data-dir', str(data)], capture_output=True, text=True, timeout=90)
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        if completed.returncode != 0:
            server_log = data / 'logs' / 'server.log'
            if server_log.is_file():
                print(server_log.read_text(encoding='utf-8', errors='replace'), file=sys.stderr)
            raise SystemExit(completed.returncode)
        try:
            exercise(port, brains)
        finally:
            subprocess.run([str(sidecar), 'stop', '--data-dir', str(data)], check=False, timeout=30)
            time.sleep(0.2)
    finally:
        temporary.cleanup()


def exercise(port, brains):
    status, state = request(port, '/api/state')
    if status != 200 or not state.get('token'):
        raise SystemExit('Brain state endpoint did not return a session.')
    token = state['token']
    _, created = request(port, '/api/brains', token, {'action': 'create', 'name': 'Smoke', 'path': str(brains)})
    brain = created['brain']['id']
    _, saved = request(port, '/api/notes', token, {'brain': brain, 'path': 'Hello.md', 'content': '# Hello from Windows\n', 'revision': None})
    if saved.get('path') != 'Hello.md':
        raise SystemExit('Saving the note did not return Hello.md.')
    _, note = request(port, '/api/note?' + urllib.parse.urlencode({'brain': brain, 'path': 'Hello.md'}))
    if note.get('content') != '# Hello from Windows\n':
        raise SystemExit('Read-back content did not match: ' + json.dumps(note))
    _, graph = request(port, '/api/graph?' + urllib.parse.urlencode({'brain': brain}))
    paths = [node.get('path') for node in graph.get('nodes', [])]
    if paths != ['Hello.md']:
        raise SystemExit('Brain graph did not list the note: ' + json.dumps(paths))
    on_disk = (Path(brains) / 'Smoke' / 'Hello.md').read_text(encoding='utf-8')
    if on_disk != '# Hello from Windows\n':
        raise SystemExit('Note file on disk did not match.')
    print('Smoke test passed.')


def reparse(name):
    parts = [part for part in name.split('/') if part not in ('', '.')]
    return any(part == '..' for part in parts)


def free_port():
    import socket
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


if __name__ == '__main__':
    try:
        main()
    except subprocess.TimeoutExpired as exc:
        raise SystemExit('The packaged server timed out.') from exc
