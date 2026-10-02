import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from github_sync import Git, SecretStore, SyncService, parse_repo, explain, GitError
from notryn_license import Entitlements
from server import Handler
from store import Problem, Store

TOKEN = 'github_pat_' + 'A1b2C3d4' * 8


def fake_api(private=True):
    def api(token, path):
        if token != TOKEN:
            raise Problem('GitHub did not accept this token.', 401)
        if path == '/user':
            return {'login': 'ana', 'id': 42}
        return {'private': private, 'default_branch': 'main'}
    return api


class LocalSync(SyncService):
    """Uses a bare repository on disk instead of github.com."""
    remote = None

    def remote_url(self, repo):
        return str(self.remote)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.remote = self.base / 'remote.git'
        subprocess.run(['git', 'init', '-q', '--bare', str(self.remote)], check=True)

    def tearDown(self):
        self.temp.cleanup()

    def device(self, name, private=True):
        store = Store(self.base / name / 'state')
        service = LocalSync(store, SecretStore(store.home, backend='file'), Entitlements(store.home, enabled=False), fake_api(private))
        service.remote = self.remote
        service.connect_account(TOKEN)
        brain = store.add('Notes', create_in=str(self.make(self.base / name)))
        return store, service, brain

    @staticmethod
    def make(path):
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_token_is_private_and_never_described(self):
        store, service, _ = self.device('one')
        description = json.dumps(service.describe())
        self.assertNotIn(TOKEN, description)
        self.assertEqual(service.describe()['account']['login'], 'ana')
        secret = store.home / 'secrets' / 'github.json'
        self.assertEqual(secret.stat().st_mode & 0o777, 0o600)
        self.assertEqual(secret.parent.stat().st_mode & 0o777, 0o700)
        self.assertNotIn(TOKEN, (store.home / 'sync.json').read_text())
        self.assertNotIn(TOKEN, store.config.read_text())
        service.disconnect_account()
        self.assertFalse(secret.exists())
        with self.assertRaises(Problem):
            service.connect_account('not-a-token')

    def test_token_is_not_stored_in_git_config(self):
        store, service, brain = self.device('one')
        store.write(brain['id'], 'A.md', '# A', None)
        service.configure(brain['id'], 'ana/notes')
        root = Path(brain['root'])
        self.assertNotIn(TOKEN, (root / '.git' / 'config').read_text())
        self.assertIn('.notryn-*', (root / '.git' / 'info' / 'exclude').read_text())

    def test_two_computers_share_a_brain(self):
        store_a, sync_a, brain_a = self.device('laptop')
        store_a.write(brain_a['id'], 'Ideas.md', '# Ideas\n[[Plans]]', None)
        store_a.folder(brain_a['id'], 'Projects')
        store_a.write(brain_a['id'], 'Projects/Plans.md', '# Plans', None)
        first = sync_a.configure(brain_a['id'], 'ana/notes', interval=5)
        self.assertTrue(first['pushed'])

        store_b, sync_b, brain_b = self.device('desktop')
        second = sync_b.configure(brain_b['id'], 'https://github.com/ana/notes.git')
        self.assertEqual(second['pulled'], 2)
        self.assertEqual((Path(brain_b['root']) / 'Projects' / 'Plans.md').read_text(), '# Plans')
        self.assertEqual(len(store_b.graph(brain_b['id'])['nodes']), 2)

        note = store_b.read(brain_b['id'], 'Ideas.md')
        store_b.write(brain_b['id'], 'Ideas.md', '# Ideas\nFrom the desktop', note['revision'])
        self.assertTrue(sync_b.sync(brain_b['id'])['pushed'])
        result = sync_a.sync(brain_a['id'])
        self.assertEqual(result['pulled'], 1)
        self.assertIn('From the desktop', (Path(brain_a['root']) / 'Ideas.md').read_text())
        self.assertFalse(sync_a.sync(brain_a['id'])['pushed'])

    def test_conflicting_edits_keep_both_versions(self):
        store_a, sync_a, brain_a = self.device('laptop')
        store_a.write(brain_a['id'], 'Shared.md', 'base', None)
        sync_a.configure(brain_a['id'], 'ana/notes')
        store_b, sync_b, brain_b = self.device('desktop')
        sync_b.configure(brain_b['id'], 'ana/notes')

        store_a.write(brain_a['id'], 'Shared.md', 'laptop version', store_a.read(brain_a['id'], 'Shared.md')['revision'])
        sync_a.sync(brain_a['id'])
        store_b.write(brain_b['id'], 'Shared.md', 'desktop version', store_b.read(brain_b['id'], 'Shared.md')['revision'])
        result = sync_b.sync(brain_b['id'])

        root = Path(brain_b['root'])
        self.assertEqual((root / 'Shared.md').read_text(), 'desktop version')
        self.assertEqual(len(result['conflicts']), 1)
        self.assertEqual((root / result['conflicts'][0]).read_text(), 'laptop version')
        self.assertNotIn('<<<<<<<', (root / 'Shared.md').read_text())
        # The laptop receives both versions too.
        sync_a.sync(brain_a['id'])
        self.assertTrue((Path(brain_a['root']) / result['conflicts'][0]).exists())

    def test_interrupted_merge_is_recovered_without_conflict_markers(self):
        store_a, sync_a, brain_a = self.device('laptop')
        store_a.write(brain_a['id'], 'Shared.md', 'base', None)
        sync_a.configure(brain_a['id'], 'ana/notes')
        store_b, sync_b, brain_b = self.device('desktop')
        sync_b.configure(brain_b['id'], 'ana/notes')
        store_a.write(brain_a['id'], 'Shared.md', 'laptop', store_a.read(brain_a['id'], 'Shared.md')['revision'])
        sync_a.sync(brain_a['id'])
        store_b.write(brain_b['id'], 'Shared.md', 'desktop', store_b.read(brain_b['id'], 'Shared.md')['revision'])
        git = Git(brain_b['root'], identity={'name': 'Test', 'email': 'test@example.com'})
        git.run('add', '-A')
        git.run('commit', '-q', '-m', 'local')
        git.run('fetch', '-q', 'notryn', '+refs/heads/main:refs/remotes/notryn/main')
        git.run('merge', 'notryn/main', check=False)  # Simulates a crash during a conflicted merge.
        result = sync_b.sync(brain_b['id'])
        self.assertEqual((Path(brain_b['root']) / 'Shared.md').read_text(), 'desktop')
        self.assertEqual(len(result['conflicts']), 1)

    def test_existing_folders_on_both_sides_are_merged(self):
        store_a, sync_a, brain_a = self.device('laptop')
        store_a.write(brain_a['id'], 'Laptop.md', 'one', None)
        sync_a.configure(brain_a['id'], 'ana/notes')
        store_b, sync_b, brain_b = self.device('desktop')
        store_b.write(brain_b['id'], 'Desktop.md', 'two', None)
        sync_b.configure(brain_b['id'], 'ana/notes')
        sync_a.sync(brain_a['id'])
        for brain in (brain_a, brain_b):
            self.assertEqual(sorted(p.name for p in Path(brain['root']).glob('*.md')), ['Desktop.md', 'Laptop.md'])

    def test_public_repository_requires_confirmation(self):
        store, service, brain = self.device('one', private=False)
        with self.assertRaises(Problem) as context:
            service.configure(brain['id'], 'ana/notes')
        self.assertEqual(context.exception.status, 428)
        self.assertNotIn('sync', store.get(brain['id']))
        service.configure(brain['id'], 'ana/notes', confirm_public=True)
        self.assertFalse(store.get(brain['id'])['sync']['private'])

    def test_repository_that_becomes_public_pauses_sync(self):
        store, service, brain = self.device('one')
        store.write(brain['id'], 'A.md', 'a', None)
        service.configure(brain['id'], 'ana/notes')
        service.api = fake_api(private=False)
        store.write(brain['id'], 'B.md', 'secret', None)
        with self.assertRaises(Problem) as context:
            service.sync(brain['id'])
        self.assertEqual(context.exception.status, 428)
        self.assertNotIn('B.md', Git(self.remote).out('ls-tree', '-r', '--name-only', 'main'))
        service.configure(brain['id'], 'ana/notes', confirm_public=True)
        self.assertIn('B.md', Git(self.remote).out('ls-tree', '-r', '--name-only', 'main'))

    def test_folder_on_another_branch_is_not_pushed(self):
        store, service, brain = self.device('one')
        git = Git(Path(brain['root']), identity={'name': 'Test', 'email': 'test@example.com'})
        git.run('init', '-q')
        git.run('checkout', '-q', '-b', 'drafts')
        store.write(brain['id'], 'Draft.md', 'not for main', None)
        git.run('add', '-A')
        git.run('commit', '-q', '-m', 'draft')
        with self.assertRaises(Problem) as context:
            service.configure(brain['id'], 'ana/notes')
        self.assertEqual(context.exception.status, 409)
        self.assertIn('drafts', context.exception.message)
        self.assertEqual(Git(self.remote).run('rev-parse', '--verify', '-q', 'main', check=False).returncode, 1)
        git.run('checkout', '-q', '-b', 'main')
        self.assertTrue(service.sync(brain['id'])['pushed'])

    def test_empty_repository_on_another_branch_name_is_adopted(self):
        store, service, brain = self.device('one')
        Git(Path(brain['root'])).run('init', '-q', '-b', 'master')
        store.write(brain['id'], 'A.md', 'a', None)
        self.assertTrue(service.configure(brain['id'], 'ana/notes')['pushed'])
        self.assertIn('A.md', Git(self.remote).out('ls-tree', '-r', '--name-only', 'main'))

    def test_orphan_branch_in_a_repository_with_history_is_refused(self):
        store, service, brain = self.device('one')
        git = Git(Path(brain['root']), identity={'name': 'Test', 'email': 'test@example.com'})
        git.run('init', '-q', '-b', 'main')
        store.write(brain['id'], 'Keep.md', 'main notes', None)
        git.run('add', '-A')
        git.run('commit', '-q', '-m', 'main')
        git.run('switch', '-q', '--orphan', 'drafts')
        with self.assertRaises(Problem) as context:
            service.configure(brain['id'], 'ana/notes')
        self.assertEqual(context.exception.status, 409)
        self.assertEqual(Git(self.remote).run('rev-parse', '--verify', '-q', 'main', check=False).returncode, 1)

    def test_existing_remote_with_the_same_name_is_left_alone(self):
        store, service, brain = self.device('one')
        root = Path(brain['root'])
        git = Git(root)
        git.run('init', '-q')
        git.run('remote', 'add', 'notryn', 'https://example.com/mine.git')
        with self.assertRaises(Problem) as context:
            service.configure(brain['id'], 'ana/notes')
        self.assertEqual(context.exception.status, 409)
        service.stop(brain['id'])
        self.assertEqual(git.out('remote', 'get-url', 'notryn'), 'https://example.com/mine.git')

    def test_scheduler_survives_unexpected_failures(self):
        store, service, brain = self.device('one')
        store.write(brain['id'], 'A.md', 'a', None)
        service.configure(brain['id'], 'ana/notes', interval=5)
        exclude = Path(brain['root']) / '.git' / 'info' / 'exclude'
        exclude.write_bytes(b'\xff\xfe not utf-8')
        service.status[brain['id']]['at'] = '2000-01-01T00:00:00+00:00'
        service.tick()
        self.assertEqual(service.status[brain['id']]['state'], 'error')

    def test_private_preview_hides_sync_details(self):
        from share import reader_payload
        brain = {'id': 'b', 'name': 'Notes', 'sync': {'repo': 'ana/notes'}}
        self.assertNotIn('sync', reader_payload('/api/graph', {'brain': brain, 'nodes': []})['brain'])
        self.assertNotIn('sync', reader_payload('/api/state', {'brains': [brain]})['brains'][0])

    def test_read_only_brain_cannot_sync(self):
        store = Store(self.base / 'ro' / 'state')
        service = LocalSync(store, SecretStore(store.home, backend='file'), Entitlements(store.home, enabled=False), fake_api())
        service.connect_account(TOKEN)
        folder = self.make(self.base / 'ro' / 'Existing')
        brain = store.add('Existing', existing=str(folder), writable=False)
        with self.assertRaises(Problem) as context:
            service.configure(brain['id'], 'ana/notes')
        self.assertEqual(context.exception.status, 403)

    def test_paywall_blocks_sync_until_unlocked(self):
        store = Store(self.base / 'paid' / 'state')
        locked = Entitlements(store.home, enabled=True, public_hex='00' * 32)
        service = LocalSync(store, SecretStore(store.home, backend='file'), locked, fake_api())
        with self.assertRaises(Problem) as context:
            service.connect_account(TOKEN)
        self.assertEqual(context.exception.status, 402)
        self.assertFalse(service.describe()['license']['allowed'])

    def test_stop_keeps_files_and_history(self):
        store, service, brain = self.device('one')
        store.write(brain['id'], 'A.md', 'a', None)
        service.configure(brain['id'], 'ana/notes')
        service.stop(brain['id'])
        root = Path(brain['root'])
        self.assertTrue((root / 'A.md').exists())
        self.assertTrue((root / '.git').is_dir())
        self.assertNotIn('sync', store.get(brain['id']))
        self.assertNotIn('notryn', Git(root).out('remote'))

    def test_schedule_runs_due_brains(self):
        store, service, brain = self.device('one')
        store.write(brain['id'], 'A.md', 'a', None)
        service.configure(brain['id'], 'ana/notes', interval=0, on_open=True)
        self.assertFalse(service.due(brain['id'], store.get(brain['id'])['sync'], startup=False))
        self.assertTrue(service.due(brain['id'], store.get(brain['id'])['sync'], startup=True))
        service.update_schedule(brain['id'], 5, False)
        config = store.get(brain['id'])['sync']
        self.assertFalse(service.due(brain['id'], config, startup=False))
        service.status[brain['id']]['at'] = '2000-01-01T00:00:00+00:00'
        self.assertTrue(service.due(brain['id'], config, startup=False))
        with self.assertRaises(Problem):
            service.update_schedule(brain['id'], 7, False)

    def test_repository_names(self):
        for value in ('ana/notes', 'https://github.com/ana/notes', 'https://github.com/ana/notes.git', 'git@github.com:ana/notes.git', ' github.com/ana/notes/ '):
            self.assertEqual(parse_repo(value), 'ana/notes')
        for value in ('', 'ana', 'https://gitlab.com/ana/notes', 'ana/../x', 'ana/notes; rm -rf /', '-x/notes'):
            with self.assertRaises(Problem):
                parse_repo(value)

    def test_errors_are_explained_without_secrets(self):
        git = Git('.', TOKEN)
        self.assertNotIn(TOKEN, git.scrub('fatal: ' + TOKEN))
        self.assertIn('Contents: Read and write', explain(GitError('remote: Permission to ana/notes.git denied. 403', 128)))
        self.assertIn('not found', explain(GitError('remote: Repository not found.', 128)))


class SyncHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.http.store = Store(Path(self.temp.name) / 'state')
        self.http.sync = SyncService(self.http.store, SecretStore(self.http.store.home, backend='file'), Entitlements(self.http.store.home, enabled=False), fake_api())
        self.http.token = 'test-only-session-token'
        self.origin = 'http://127.0.0.1:' + str(self.http.server_port)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, payload=None, headers=None):
        body = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(self.origin + path, data=body, headers=headers or {})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_account_connection_requires_local_session_and_hides_token(self):
        payload = {'action': 'connect', 'token': TOKEN}
        self.assertEqual(self.request('/api/sync/account', payload)[0], 403)
        code, data = self.request('/api/sync/account', payload, {'Origin': self.origin, 'X-Notryn-Token': self.http.token})
        self.assertEqual(code, 200)
        self.assertEqual(data['account']['login'], 'ana')
        code, data = self.request('/api/sync')
        self.assertEqual(code, 200)
        self.assertNotIn(TOKEN, json.dumps(data))
        self.assertEqual(self.request('/api/sync', headers={'Host': 'external.example'})[0], 403)

    def test_license_activation_rejects_invalid_keys(self):
        code, data = self.request('/api/license', {'action': 'activate', 'key': 'nope'}, {'Origin': self.origin, 'X-Notryn-Token': self.http.token})
        self.assertEqual(code, 400)
        self.assertIn('license', data['error'].lower())


if __name__ == '__main__':
    unittest.main()
