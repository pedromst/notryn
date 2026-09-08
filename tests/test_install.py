import hashlib
import io
import json
import os
import stat
import ssl
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from notryn_install import Installation, Releases, safe_extract, version_key, https_context


class FixtureReleases:
    private = True

    def __init__(self, folder, version='0.2.0-alpha.3'):
        self.version = version
        self.archive = Path(folder) / ('package-' + version + '.tar.gz')
        root = 'Notryn-' + version
        with tarfile.open(self.archive, 'w:gz') as archive:
            for name, content in [('sidecar/notryn', b'#!/bin/sh\necho ' + version.encode() + b'\n'), ('Notryn.AppImage', b'app'), ('notryn.svg', b'<svg/>')]:
                member = tarfile.TarInfo(root + '/' + name);member.mode = 0o755;member.size = len(content)
                archive.addfile(member, io.BytesIO(content))

    def release(self, version=None, prerelease=False):
        return {'tag_name': 'v' + self.version}

    def download(self, release, name, directory):
        return self.archive


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.install = Installation(home=self.root / 'User with spaces', target=('linux', 'x86_64'), data=self.root / 'private data')
        self.install.data.mkdir()
        self.note = self.install.data / 'brains' / 'My Brain' / 'note.md'
        self.note.parent.mkdir(parents=True);self.note.write_text('# Keep this note')
        self.settings = self.install.data / 'brains.json';self.settings.write_text('{"private": true}')

    def tearDown(self):
        self.temp.cleanup()

    def assert_data_preserved(self):
        self.assertEqual(self.note.read_text(), '# Keep this note')
        self.assertEqual(self.settings.read_text(), '{"private": true}')

    def test_install_upgrade_rollback_uninstall_preserve_data_and_desktop_paths(self):
        with patch.object(self.install, 'verify_app'):
            self.install.install(FixtureReleases(self.root))
            self.install.install(FixtureReleases(self.root, '0.2.0-alpha.4'))
            self.assertEqual(self.install.manifest()['version'], '0.2.0-alpha.4')
            self.install.rollback()
        self.assertEqual(self.install.manifest()['version'], '0.2.0-alpha.3')
        self.assertIn("'", self.install.bin.read_text())
        desktop = (self.install.home / '.local/share/applications/com.notryn.Notryn.desktop').read_text()
        self.assertIn('Exec="', desktop)
        self.assertIn('" open', desktop)
        self.install.uninstall()
        self.assertFalse(self.install.app.exists());self.assertFalse(self.install.bin.exists())
        self.assertTrue(any(self.install.backups.iterdir()))
        self.assert_data_preserved()

    def test_failed_new_package_keeps_current_application(self):
        with patch.object(self.install, 'verify_app'):
            self.install.install(FixtureReleases(self.root))
        before = self.install.sidecar.read_bytes()
        with patch.object(self.install, 'verify_app', side_effect=RuntimeError('bad package')):
            with self.assertRaises(RuntimeError):
                self.install.install(FixtureReleases(self.root, '0.2.0-alpha.4'))
        self.assertEqual(self.install.sidecar.read_bytes(), before)
        self.assertEqual(self.install.manifest()['version'], '0.2.0-alpha.3')
        self.assert_data_preserved()

    def test_failed_activation_restores_previous_application(self):
        with patch.object(self.install, 'verify_app'):
            self.install.install(FixtureReleases(self.root))
            real_launchers = self.install.launchers
            calls = []
            def fail_once():
                calls.append(1)
                if len(calls) == 1:
                    raise OSError('simulated disk failure')
                real_launchers()
            with patch.object(self.install, 'launchers', side_effect=fail_once):
                with self.assertRaises(OSError):
                    self.install.install(FixtureReleases(self.root, '0.2.0-alpha.4'))
        self.assertIn('0.2.0-alpha.3', self.install.sidecar.read_text())
        self.assertEqual(self.install.manifest()['version'], '0.2.0-alpha.3')
        self.assert_data_preserved()

    def test_refuse_live_app_and_concurrent_installer(self):
        with patch.object(self.install, 'stopped', side_effect=RuntimeError('Quit Notryn first')):
            with self.assertRaises(RuntimeError):
                self.install.install(FixtureReleases(self.root))
        self.assertFalse(self.install.app.exists())
        (self.install.data / 'installation.lock').mkdir()
        with self.assertRaisesRegex(RuntimeError, 'Another installation'):
            self.install.install(FixtureReleases(self.root))
        self.assert_data_preserved()

    def test_unknown_destination_and_symlink_refused(self):
        self.install.app.mkdir(parents=True)
        (self.install.app / 'unrelated').write_text('keep')
        with patch.object(self.install, 'verify_app'), self.assertRaises(RuntimeError):
            self.install.install(FixtureReleases(self.root))
        self.assertEqual((self.install.app / 'unrelated').read_text(), 'keep')
        self.install.bin.parent.mkdir(parents=True, exist_ok=True)
        self.install.bin.symlink_to(self.note)
        with self.assertRaises(RuntimeError):
            self.install.install(FixtureReleases(self.root))
        self.assert_data_preserved()

    def test_optional_ci_metadata_token_is_not_required_by_public_installer(self):
        for token in (None, 'synthetic-ci-token'):
            response = io.BytesIO(b'[]')
            with patch('notryn_install.urlopen', return_value=response) as fetch:
                Releases(False, api_token=token).json('/releases')
                request = fetch.call_args.args[0]
                self.assertEqual(request.get_header('Authorization'), 'Bearer ' + token if token else None)
                self.assertEqual(request.full_url, 'https://api.github.com/repos/pedromst/notryn/releases')

    def test_https_context_requires_trusted_certificates_and_hostname(self):
        context = https_context()
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertGreater(len(context.get_ca_certs()), 0)

    def test_hash_mismatch_refuses_download(self):
        client = Releases(False)
        digest = hashlib.sha256(b'correct').hexdigest()
        release = {'tag_name':'v0.2.0-alpha.3','assets':[{'name':'package.zip','state':'uploaded','size':7,'digest':'sha256:'+digest}]}
        response = io.BytesIO(b'wrong!!');response.url='https://github.com/file'
        with patch('notryn_install.urlopen', return_value=response), self.assertRaisesRegex(RuntimeError,'checksum'):
            client.download(release, 'package.zip', self.root)

    def test_state_inside_application_is_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'outside the application'):
            Installation(self.root, ('linux', 'x86_64'), self.root / '.local/lib/notryn/brains')

    def test_no_downgrade_and_semver_order(self):
        self.assertGreater(version_key('0.2.0-alpha.10'),version_key('0.2.0-alpha.9'))
        self.assertGreater(version_key('0.2.0'),version_key('0.2.0-rc.2'))
        with self.assertRaises(RuntimeError):version_key('../../wrong')
        with patch.object(self.install, 'verify_app'):
            self.install.install(FixtureReleases(self.root,'0.2.0-alpha.4'))
            self.install.install(FixtureReleases(self.root,'0.2.0-alpha.3'))
        self.assertEqual(self.install.manifest()['version'],'0.2.0-alpha.4')

    def test_public_update_channel_follows_installed_version(self):
        for installed, expected in [('0.2.0-beta.1', True), ('0.2.0', False)]:
            with self.subTest(installed=installed):
                client = FixtureReleases(self.root, installed)
                client.private = False
                with patch.object(self.install, 'verify_app'):
                    self.install.install(client, installed)
                    with patch.object(client, 'release', wraps=client.release) as fetch:
                        self.install.install(client)
                        fetch.assert_called_once_with(None, prerelease=expected)
                self.install.uninstall()
        self.assert_data_preserved()

    def test_public_release_selection_filters_drafts_and_preview(self):
        client = Releases(False)
        releases = [
            {'tag_name': 'v0.2.0', 'prerelease': False},
            {'tag_name': 'v0.3.0-beta.1', 'prerelease': True},
            {'tag_name': 'v0.4.0', 'draft': True},
        ]
        with patch.object(client, 'json', return_value=releases):
            self.assertEqual(client.release()['tag_name'], 'v0.2.0')
            self.assertEqual(client.release(prerelease=True)['tag_name'], 'v0.3.0-beta.1')

    def test_archive_paths_links_special_files_and_duplicates(self):
        for name, target in [('../outside',None),('/outside',None),('Notryn/escape','../../outside'),('Notryn/device',None),('Notryn/file',None)]:
            with self.subTest(name=name):
                path=self.root/'unsafe.tar.gz'
                with tarfile.open(path,'w:gz') as archive:
                    member=tarfile.TarInfo(name)
                    if target:member.type=tarfile.SYMTYPE;member.linkname=target
                    elif name.endswith('device'):member.type=tarfile.FIFOTYPE
                    archive.addfile(member)
                    if name.endswith('file'):archive.addfile(member)
                with self.assertRaises(RuntimeError):safe_extract(path,self.root/'out','Notryn')
        self.assertFalse((self.root/'outside').exists())

    def test_zip_internal_framework_link_and_escaping_link(self):
        for target, valid in [('Versions/A', True),('../../outside',False)]:
            path=self.root/('valid.zip' if valid else 'invalid.zip')
            with zipfile.ZipFile(path,'w') as archive:
                archive.writestr('Notryn.app/Framework/Versions/A/binary','data')
                link=zipfile.ZipInfo('Notryn.app/Framework/Current');link.create_system=3;link.external_attr=(stat.S_IFLNK|0o777)<<16
                archive.writestr(link,target)
            if valid:
                root=safe_extract(path,self.root/'safe','Notryn.app')
                self.assertEqual((root/'Framework/Current/binary').read_text(),'data')
            else:
                with self.assertRaises(RuntimeError):safe_extract(path,self.root/'bad','Notryn.app')


if __name__ == '__main__': unittest.main()
