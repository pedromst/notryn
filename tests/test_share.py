import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Handler
from share import Gateway
from store import Store


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.local = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.local.store = Store(Path(self.temp.name) / 'state')
        self.local.token = 'local-only-test-token'
        self.brain = self.local.store.add('Demo')
        self.local.store.write(self.brain['id'], 'One.md', '# One', None)
        self.handler = type('TestGateway', (Gateway,), {
            'origin_host': 'preview.example', 'origin_port': self.local.server_port,
            'deadline': time.time() + 60, 'session': 'preview-test-session'})
        self.gateway = ThreadingHTTPServer(('127.0.0.1', 0), self.handler)
        self.threads = []
        for server in (self.local, self.gateway):
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.threads.append(thread)

    def tearDown(self):
        for server in (self.gateway, self.local):
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join()
        self.temp.cleanup()

    def request(self, path, data=None, authenticated=True):
        headers = {'Host': 'preview.example'}
        if authenticated:
            headers['Cookie'] = '__Host-neura=preview-test-session'
        req = urllib.request.Request(
            f'http://127.0.0.1:{self.gateway.server_port}{path}',
            data=json.dumps(data).encode() if data is not None else None, headers=headers)
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            body = error.read()
            return error.code, json.loads(body) if body.startswith(b'{') else body

    def test_remote_reader_does_not_receive_write_permissions_or_local_token(self):
        status, state = self.request('/api/state')
        self.assertEqual(status, 200)
        self.assertTrue(state['remotePreview'])
        self.assertEqual(state['token'], '')
        self.assertTrue(state['brains'][0]['readOnly'])
        _, graph = self.request('/api/graph?brain=' + self.brain['id'])
        self.assertTrue(graph['brain']['readOnly'])
        _, note = self.request('/api/note?brain=' + self.brain['id'] + '&path=One.md')
        self.assertTrue(note['readOnly'])
        self.assertEqual(note['content'], '# One')
        self.assertEqual(self.request('/api/notes', {'content': 'overwrite'})[0], 405)
        self.assertEqual(self.request('/api/move', {'source': 'One.md', 'destination': 'Folder', 'kind': 'note'})[0], 405)
        for path in ['/api/removals/preview','/api/removals','/api/removals/list','/api/removals/restore']:
            self.assertEqual(self.request(path, {})[0], 405)
        self.assertEqual(self.local.store.read(self.brain['id'], 'One.md')['content'], '# One')

    def test_remote_reader_requires_authentication_and_unexpired_access(self):
        self.assertEqual(self.request('/api/state', authenticated=False)[0], 401)
        self.handler.deadline = time.time() - 1
        self.assertEqual(self.request('/api/state')[0], 410)


if __name__ == '__main__':
    unittest.main()
