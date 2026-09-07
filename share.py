#!/usr/bin/env python3
"""Temporary authenticated preview. The Brain server remains localhost-only."""
import argparse
import hmac
import http.client
import json
import os
import re
import secrets
import signal
import shutil
import subprocess
import tempfile
import threading
import time
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ENTRY = b'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NEURA | Private access</title><style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#071117;color:#c5ede2;font:16px system-ui}main{max-width:360px;padding:32px;text-align:center}h1{letter-spacing:7px}p{color:#97afb4;line-height:1.6}</style><main><h1>NEURA</h1><p id="message">Opening your private preview...</p></main><script src="/entry.js"></script></html>'''
ENTRY_JS = b'''(async()=>{const key=location.hash.slice(1);history.replaceState(null,'',location.pathname);const m=document.getElementById('message');if(!key){m.textContent='Open the complete link you received. This access is private and temporary.';return;}try{const r=await fetch('/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})});if(!r.ok)throw Error();location.replace('/');}catch{m.textContent='Access has expired or the link is incomplete. Request a new link.';}})();'''

def reader_payload(path, payload):
    """Describe the gateway's existing read-only policy to the interface."""
    if path == '/api/state':
        return {**payload, 'token': '', 'remotePreview': True,
                'brains': [{**b, 'readOnly': True} for b in payload['brains']]}
    if path == '/api/graph':
        return {**payload, 'brain': {**payload['brain'], 'readOnly': True}}
    if path == '/api/note':
        return {**payload, 'readOnly': True}
    return payload

class Gateway(BaseHTTPRequestHandler):
    access_key = ''
    session = ''
    deadline = 0
    origin_host = ''
    origin_port = 4783

    def log_message(self, *_):
        pass  # Do not record note paths, tokens, cookies or content.

    def authenticated(self):
        try:
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            value = cookies.get('__Host-neura')
            return bool(value and hmac.compare_digest(value.value, self.session))
        except CookieError:
            return False

    def send(self, code, body, mime='text/html; charset=utf-8', cookie=None):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
            mime = 'application/json; charset=utf-8'
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store, private')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Robots-Tag', 'noindex, nofollow, noarchive')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(body)

    def ready(self):
        if time.time() >= self.deadline:
            self.send(410, b'<h1>This temporary access has ended.</h1>')
            return False
        if not self.origin_host or self.headers.get('Host') != self.origin_host:
            self.send(403, {'error': 'Host rejected.'})
            return False
        return True

    def do_GET(self):
        if not self.ready():
            return
        path = urlparse(self.path).path
        if path == '/entry.js':
            return self.send(200, ENTRY_JS, 'application/javascript; charset=utf-8')
        if not self.authenticated():
            return self.send(200, ENTRY) if path == '/' else self.send(401, {'error': 'Private access.'})
        if path == '/api/voice':
            return self.send(200, {'available': False, 'local': False, 'remotePreview': True})
        connection = http.client.HTTPConnection('127.0.0.1', self.origin_port, timeout=15)
        try:
            connection.request('GET', self.path, headers={'Host': f'127.0.0.1:{self.origin_port}'})
            response = connection.getresponse()
            body = response.read()
            mime = response.getheader('Content-Type', 'application/octet-stream')
            if response.status == 200 and path in {'/api/state', '/api/graph', '/api/note'}:
                return self.send(200, reader_payload(path, json.loads(body)))
            self.send(response.status, body, mime)
        except (OSError, http.client.HTTPException):
            self.send(502, {'error': 'The local app is unavailable.'})
        finally:
            connection.close()

    def do_POST(self):
        if not self.ready():
            return
        if self.path != '/session':
            return self.send(405, {'error': 'Remote access is read-only.'})
        if self.headers.get('Origin') != 'https://' + self.origin_host:
            return self.send(403, {'error': 'Origin rejected.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 512:
                return self.send(400, {'error': 'Invalid request.'})
            payload = json.loads(self.rfile.read(length))
            key = payload.get('key') if isinstance(payload, dict) else None
            if not isinstance(key, str) or not hmac.compare_digest(key, self.access_key):
                return self.send(403, {'error': 'Invalid access.'})
            seconds = max(1, int(self.deadline - time.time()))
            self.send(200, {'ok': True}, cookie=f'__Host-neura={self.session}; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age={seconds}')
        except (ValueError, UnicodeError):
            self.send(400, {'error': 'Invalid request.'})

    def reject(self):
        self.send(405, {'error': 'Read-only.'})
    do_PUT = do_PATCH = do_DELETE = reject


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--minutes', type=int, default=120)
    args = parser.parse_args()
    if not 1 <= args.minutes <= 120:
        parser.error('Duration must be between 1 and 120 minutes.')
    tunnel_binary = shutil.which('cloudflared')
    if not tunnel_binary:
        parser.error('Install cloudflared and add it to PATH to open a shared preview.')
    Gateway.access_key = secrets.token_urlsafe(32)
    Gateway.session = secrets.token_urlsafe(32)
    Gateway.deadline = time.time() + args.minutes * 60
    server = ThreadingHTTPServer(('127.0.0.1', 4784), Gateway)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    process = subprocess.Popen([tunnel_binary, 'tunnel', '--no-autoupdate', '--url', 'http://127.0.0.1:4784'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    state_path = Path(tempfile.gettempdir()) / ('neura-share-' + str(os.getpid()) + '.json')
    def stop(*_):
        process.terminate()
        server.shutdown()
        server.server_close()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    timer = threading.Timer(args.minutes * 60, stop)
    timer.daemon = True
    timer.start()
    try:
        for line in process.stdout:
            match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', line)
            if match and not Gateway.origin_host:
                url = match.group(0)
                Gateway.origin_host = urlparse(url).netloc
                state = {'url': url, 'key': Gateway.access_key, 'expiresAt': Gateway.deadline, 'pid': os.getpid(), 'tunnelPid': process.pid}
                fd = os.open(state_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, 'w') as f:
                    json.dump(state, f)
                print('PRIVATE_PREVIEW=' + url + '/#' + Gateway.access_key, flush=True)
                print('EXPIRES_UNIX=' + str(int(Gateway.deadline)), flush=True)
            elif 'Registered tunnel connection' in line:
                print('TUNNEL_CONNECTED', flush=True)
            elif 'ERR' in line:
                print(line.strip(), flush=True)
        process.wait()
    finally:
        timer.cancel()
        server.shutdown()
        server.server_close()
        if process.poll() is None:
            process.terminate()
        if state_path.exists():
            state_path.unlink()

if __name__ == '__main__':
    main()
