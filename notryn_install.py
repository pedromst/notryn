"""Per-user release installation. No note data is moved or removed here."""
import argparse
import contextlib
import hashlib
import json
import os
import platform
import posixpath
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen

REPO = 'pedromst/notryn'
API = 'https://api.github.com/repos/' + REPO
VERSION_RE = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?$')
MAX_DOWNLOAD = 700 * 1024 * 1024
MAX_EXPANDED = 3 * 1024 * 1024 * 1024


def version_key(value):
    match = VERSION_RE.fullmatch(value or '')
    if not match:
        raise RuntimeError('Invalid release version.')
    major, minor, patch, stage, number = match.groups()
    return (int(major), int(minor), int(patch), {'alpha': 0, 'beta': 1, 'rc': 2, None: 3}[stage], int(number or 0))


def host_target():
    system = {'Linux': 'linux', 'Darwin': 'macos'}.get(platform.system())
    arch = {'AMD64': 'x86_64', 'x86_64': 'x86_64', 'arm64': 'arm64', 'aarch64': 'arm64'}.get(platform.machine())
    if not system or not arch or (system == 'linux' and arch != 'x86_64'):
        raise RuntimeError('This release supports Linux x86_64 and macOS Intel/Apple silicon. Windows is not available yet.')
    return system, arch


def run(args, **kwargs):
    result = subprocess.run([str(arg) for arg in args], capture_output=True, text=True, timeout=kwargs.pop('timeout', 120), **kwargs)
    if result.returncode:
        raise RuntimeError('Command failed: ' + Path(str(args[0])).name + '\n' + (result.stderr or result.stdout).strip()[-1200:])
    return result.stdout.strip()


class Releases:
    def __init__(self, private=False):
        self.private = private
        if private and not shutil.which('gh'):
            raise RuntimeError('Private testing needs GitHub CLI. Install it from cli.github.com, then run gh auth login.')

    def json(self, endpoint):
        if self.private:
            return json.loads(run(['gh', 'api', '--hostname', 'github.com', 'repos/' + REPO + endpoint]))
        request = Request(API + endpoint, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Notryn installer'})
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read(4 * 1024 * 1024))

    def release(self, version=None, prerelease=False):
        if version:
            version_key(version)
            release = self.json('/releases/tags/v' + version.removeprefix('v'))
        else:
            releases = self.json('/releases?per_page=100')
            candidates = [r for r in releases if not r.get('draft') and (prerelease or not r.get('prerelease')) and VERSION_RE.fullmatch(r.get('tag_name', ''))]
            if not candidates:
                raise RuntimeError('No published release is available for this channel.')
            release = max(candidates, key=lambda r: version_key(r['tag_name']))
        if release.get('draft'):
            raise RuntimeError('Draft releases cannot be installed.')
        version_key(release.get('tag_name'))
        return release

    def download(self, release, name, directory):
        assets = [a for a in release.get('assets', []) if a.get('name') == name and a.get('state') == 'uploaded']
        if len(assets) != 1:
            raise RuntimeError('This release has no verified package for your platform: ' + name)
        asset = assets[0]
        digest = asset.get('digest', '')
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest) or not 0 < asset.get('size', 0) <= MAX_DOWNLOAD:
            raise RuntimeError('Release checksum or size is missing. Nothing was installed.')
        target = Path(directory) / name
        if self.private:
            run(['gh', 'release', 'download', release['tag_name'], '--repo', 'github.com/' + REPO, '--pattern', name, '--dir', directory], timeout=600)
        else:
            # Construct the trusted GitHub URL; never execute URLs from a manifest.
            url = 'https://github.com/' + REPO + '/releases/download/' + release['tag_name'] + '/' + name
            with urlopen(Request(url, headers={'User-Agent': 'Notryn installer'}), timeout=60) as response, target.open('wb') as output:
                if not response.url.startswith('https://'):
                    raise RuntimeError('Insecure download redirect refused.')
                count = 0
                while chunk := response.read(1024 * 1024):
                    count += len(chunk)
                    if count > asset['size']:
                        raise RuntimeError('Download exceeded the expected size.')
                    output.write(chunk)
        if target.stat().st_size != asset['size'] or sha256(target) != digest[7:]:
            raise RuntimeError('Download checksum did not match GitHub. Nothing was installed.')
        return target


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(archive, destination, root_name):
    """Validate the entire archive, then extract regular files before internal links."""
    destination = Path(destination)
    with contextlib.ExitStack() as stack:
        is_zip = zipfile.is_zipfile(archive)
        reader = stack.enter_context(zipfile.ZipFile(archive) if is_zip else tarfile.open(archive, 'r:gz'))
        entries = reader.infolist() if is_zip else reader.getmembers()
        plans, names, links, size = [], set(), set(), 0
        for member in entries:
            name = member.filename if is_zip else member.name
            path = PurePosixPath(name)
            if '\\' in name or '\x00' in name or any(ord(c) < 32 for c in name) or path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != root_name:
                raise RuntimeError('Unsafe archive path refused.')
            name = str(path)
            if name in names:
                raise RuntimeError('Duplicate archive path refused.')
            names.add(name)
            mode = member.external_attr >> 16 if is_zip else member.mode
            directory = member.is_dir() if is_zip else member.isdir()
            link = stat.S_ISLNK(mode) if is_zip else member.issym()
            regular = (stat.S_IFMT(mode) in (0, stat.S_IFREG)) if is_zip else member.isfile()
            if not (directory or link or regular):
                raise RuntimeError('Special archive entry refused.')
            length = member.file_size if is_zip else member.size
            size += length
            if size > MAX_EXPANDED or len(names) > 60000:
                raise RuntimeError('Archive is too large.')
            target = None
            if link:
                if length > 4096:
                    raise RuntimeError('Oversized symbolic link refused.')
                target = reader.read(member).decode('utf-8') if is_zip else member.linkname
                resolved = posixpath.normpath(posixpath.join(str(path.parent), target))
                if '\\' in target or any(ord(c) < 32 for c in target) or target.startswith('/') or not resolved.startswith(root_name + '/'):
                    raise RuntimeError('Archive link escapes the application.')
                links.add(name)
            plans.append((member, path, mode, directory, target))
        # A link must never act as a parent directory during extraction.
        for _, path, _, _, _ in plans:
            if any(str(parent) in links for parent in path.parents):
                raise RuntimeError('Archive writes through a symbolic link.')
        for member, path, mode, directory, target in plans:
            out = destination.joinpath(*path.parts)
            if target is not None:
                continue
            if directory:
                out.mkdir(parents=True, exist_ok=True)
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                with (reader.open(member) if is_zip else reader.extractfile(member)) as source, out.open('xb') as output:
                    shutil.copyfileobj(source, output)
                out.chmod(0o755 if mode & 0o111 else 0o644)
        for _, path, _, _, target in plans:
            if target is not None:
                out = destination.joinpath(*path.parts)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.symlink_to(target)
        root = (destination / root_name).resolve()
        for name in links:
            if not (destination / name).resolve().is_relative_to(root):
                raise RuntimeError('Chained archive link escapes the application.')
    return destination / root_name


class Installation:
    def __init__(self, home=None, target=None, data=None):
        self.home = Path(home or Path.home()).resolve()
        self.system, self.arch = target or host_target()
        self.app = self.home / ('.local/lib/notryn' if self.system == 'linux' else 'Applications/Notryn.app')
        self.backups = self.app.parent / '.notryn-backups'
        self.data = Path(data or os.environ.get('NOTRYN_HOME') or (self.home / 'Library/Application Support/Notryn' if self.system == 'macos' else Path(os.environ.get('XDG_DATA_HOME', self.home / '.local/share')) / 'notryn')).expanduser().resolve()
        if self.data.is_relative_to(self.app.resolve()) or self.data.is_relative_to(self.backups.resolve()):
            raise RuntimeError('Notes and settings must be outside the application and application-backup folders.')
        self.bin = self.home / '.local/bin/notryn'

    @property
    def sidecar(self):
        return self.sidecar_in(self.app)

    def sidecar_in(self, app):
        return Path(app) / ('sidecar/notryn' if self.system == 'linux' else 'Contents/Resources/notryn/notryn')

    def manifest_path(self, app=None):
        # Keep management metadata outside signed macOS bundles.
        return self.data / 'installation.json' if app is None else Path(str(app) + '.json')

    def write_manifest(self, value, app=None):
        path = self.manifest_path(app)
        temporary = path.with_name(path.name + '.tmp-' + secrets.token_hex(4))
        temporary.write_text(json.dumps(value, indent=2) + '\n')
        temporary.chmod(0o600)
        os.replace(temporary, path)

    def manifest(self, app=None):
        try:
            value = json.loads(self.manifest_path(app).read_text())
            version_key(value['version'])
            if value['platform'] != self.system or value['arch'] != self.arch:
                raise ValueError()
            return value
        except (OSError, ValueError, KeyError):
            raise RuntimeError('No managed installation found. Run the new installer first.')

    def stopped(self):
        try:
            record = json.loads((self.data / 'runtime.json').read_text())
            port, instance = record['port'], record['instance']
            if not isinstance(port, int) or not 1 <= port <= 65535 or not isinstance(instance, str):
                return
            with urlopen(f'http://127.0.0.1:{port}/api/runtime', timeout=.5) as response:
                live = json.loads(response.read(65536))
            if live.get('app') == 'notryn' and live.get('instance') == instance:
                raise RuntimeError('Save your notes and quit Notryn before installing, updating or uninstalling. If using the local server, run notryn stop.')
        except (OSError, ValueError, KeyError):
            pass

    @contextlib.contextmanager
    def locked(self):
        self.data.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = self.data / 'installation.lock'
        try:
            lock.mkdir(mode=0o700)
        except FileExistsError:
            raise RuntimeError('Another installation is in progress. If it was interrupted, check that no installer is running before removing ' + str(lock))
        try:
            self.stopped()
            # Never follow application/launcher destinations supplied through links.
            for target in (self.app, self.backups, self.bin, self.home / '.local/share/applications/com.notryn.Notryn.desktop', self.home / '.local/share/icons/hicolor/scalable/apps/notryn.svg'):
                if any(parent.is_symlink() for parent in (target, *target.parents) if parent != self.home.parent):
                    raise RuntimeError('A symbolic link in the installation destination was refused.')
            yield
        finally:
            lock.rmdir()

    def verify_app(self, root, version, smoke=True):
        binary = self.sidecar_in(root)
        if not binary.is_file():
            raise RuntimeError('The local server is missing from the package.')
        shell = root / ('Notryn.AppImage' if self.system == 'linux' else 'Contents/MacOS/Notryn')
        if not shell.is_file():
            raise RuntimeError('The desktop application is missing from the package.')
        if self.system == 'macos':
            run(['/usr/bin/codesign', '--verify', '--deep', '--strict', root])
        if run([binary, 'version']) != version:
            raise RuntimeError('The package version did not match the release.')
        if smoke:
            with tempfile.TemporaryDirectory(prefix='notryn-check-') as temporary:
                with socket.socket() as sock:
                    sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
                try:
                    run([binary, 'start', '--data-dir', temporary, '--port', str(port)], timeout=30)
                    run([binary, 'status', '--data-dir', temporary])
                finally:
                    run([binary, 'stop', '--data-dir', temporary])

    def launchers(self):
        import shlex
        self.bin.parent.mkdir(parents=True, exist_ok=True)
        script = '#!/bin/sh\nexec ' + shlex.quote(str(self.sidecar)) + ' "$@"\n'
        self.bin.write_text(script); self.bin.chmod(0o755)
        if self.system == 'linux':
            folder = self.home / '.local/share/applications'; folder.mkdir(parents=True, exist_ok=True)
            icon_dir = self.home / '.local/share/icons/hicolor/scalable/apps'; icon_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.app / 'notryn.svg', icon_dir / 'notryn.svg')
            # Desktop Exec has its own quoting rules (not shell interpolation).
            executable = str(self.bin).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
            (folder / 'com.notryn.Notryn.desktop').write_text('[Desktop Entry]\nType=Application\nVersion=1.0\nName=Notryn\nComment=Local Markdown notes\nExec="' + executable + '" open\nIcon=notryn\nTerminal=false\nCategories=Office;Utility;\nStartupNotify=true\n')

    def install(self, client, version=None):
        with self.locked():
            existing = self.manifest() if self.app.exists() and self.manifest_path().is_file() else None
            # Beta installations follow preview releases; stable installations stay stable.
            preview = client.private or bool(existing and '-' in existing['version'])
            release = client.release(version, prerelease=preview)
            version = release['tag_name'].removeprefix('v')
            if existing:
                if version_key(version) <= version_key(existing['version']):
                    print('Already installed: ' + existing['version'] + '. Use notryn rollback to return to a saved version.')
                    return existing['version']
            extension = 'tar.gz' if self.system == 'linux' else 'zip'
            name = f'Notryn-{version}-{self.system}-{self.arch}.{extension}'
            with tempfile.TemporaryDirectory(prefix='notryn-download-') as temporary:
                print('Downloading Notryn ' + version + ' for ' + self.system + ' ' + self.arch + '…', flush=True)
                archive = client.download(release, name, temporary)
                root = safe_extract(archive, Path(temporary) / 'unpacked', 'Notryn-' + version if self.system == 'linux' else 'Notryn.app')
                self.verify_app(root, version)
                self.app.parent.mkdir(parents=True, exist_ok=True)
                stage = Path(tempfile.mkdtemp(prefix='.notryn-new-', dir=self.app.parent))
                backup = None
                try:
                    shutil.copytree(root, stage, dirs_exist_ok=True, symlinks=True)
                    if self.app.exists():
                        # Only migrate the recognizable prior private alpha layout.
                        if not self.sidecar.is_file():
                            raise RuntimeError('Installation location contains an unrelated application. Nothing was replaced.')
                        self.backups.mkdir(parents=True, exist_ok=True)
                        backup = self.backups / ('notryn-' + (existing or {}).get('version', 'legacy') + '-' + secrets.token_hex(6))
                    metadata = {'version': version, 'platform': self.system, 'arch': self.arch, 'private': client.private, 'previous': backup.name if backup else None, 'sha256': sha256(archive)}
                    if backup:
                        if existing:
                            self.write_manifest(existing, backup)
                        self.app.rename(backup)
                    try:
                        stage.rename(self.app)
                        self.launchers()
                        self.write_manifest(metadata)
                    except Exception:
                        if self.app.exists():
                            shutil.rmtree(self.app)
                        if backup:
                            backup.rename(self.app)
                            self.launchers()
                        raise
                finally:
                    if stage.exists():
                        shutil.rmtree(stage)
            print('Installed Notryn ' + version + '. Your notes and settings were kept.\nOpen from your app menu or run: ' + str(self.bin))
            return version

    def update(self, version=None):
        metadata = self.manifest()
        return self.install(Releases(metadata['private']), version)

    def rollback(self):
        with self.locked():
            metadata = self.manifest()
            name = metadata.get('previous')
            if not name or Path(name).name != name:
                raise RuntimeError('No previous application version is available.')
            previous = self.backups / name
            if previous.is_symlink() or not previous.is_dir():
                raise RuntimeError('The previous application backup is unavailable.')
            old = self.manifest(previous) if self.manifest_path(previous).is_file() else {'version': run([self.sidecar_in(previous), 'version']), 'platform': self.system, 'arch': self.arch, 'private': metadata['private']}
            self.verify_app(previous, old['version'])
            saved = self.backups / ('notryn-' + metadata['version'] + '-' + secrets.token_hex(6))
            self.write_manifest(metadata, saved)
            self.app.rename(saved)
            try:
                previous.rename(self.app)
                old['previous'] = saved.name
                self.launchers()
                self.write_manifest(old)
            except Exception:
                if self.app.exists():
                    self.app.rename(previous)
                saved.rename(self.app)
                self.launchers()
                raise
            print('Restored Notryn ' + old['version'] + '. Notes and settings were not rolled back.')

    def uninstall(self):
        with self.locked():
            self.manifest()
            self.backups.mkdir(parents=True, exist_ok=True)
            target = self.backups / ('uninstalled-' + secrets.token_hex(6))
            self.write_manifest(self.manifest(), target)
            self.app.rename(target)
            self.manifest_path().unlink()
            self.bin.unlink(missing_ok=True)
            if self.system == 'linux':
                for path in ['applications/com.notryn.Notryn.desktop', 'icons/hicolor/scalable/apps/notryn.svg']:
                    (self.home / '.local/share' / path).unlink(missing_ok=True)
            print('Notryn uninstalled. Notes and settings were kept at ' + str(self.data) + '.\nApplication backups were kept at ' + str(self.backups) + '.')

    def open(self):
        if not self.app.exists():
            raise RuntimeError('Install the desktop application first.')
        if self.system == 'macos':
            subprocess.Popen(['/usr/bin/open', str(self.app)])
        else:
            environment = os.environ.copy(); environment['APPIMAGE_EXTRACT_AND_RUN'] = '1'
            subprocess.Popen([str(self.app / 'Notryn.AppImage')], env=environment, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description='Install the Notryn desktop app for this user.')
    parser.add_argument('--private', action='store_true', help='Use GitHub CLI authentication for the private alpha')
    parser.add_argument('--version')
    parser.add_argument('--no-open', action='store_true')
    args = parser.parse_args()
    try:
        if hasattr(os, 'geteuid') and os.geteuid() == 0:
            raise RuntimeError('Run as your normal user, without sudo.')
        installation = Installation()
        installation.install(Releases(args.private), args.version)
        if not args.no_open:
            installation.open()
        return 0
    except Exception as error:
        print('Installation stopped: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
