#!/usr/bin/env python3
"""NEURA local application server. Standard library only, Python 3.9+."""
import argparse
import hmac
import json
import mimetypes
import secrets
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from store import Store, Problem
from themes import omarchy_theme
from desktop import reveal_note

HERE=Path(__file__).resolve().parent
WEB=HERE/'web'
SPEECH_LOCK=threading.Lock()
SPEECH_PROCESS=None

def has_voice():
    if not Path('/usr/bin/say').is_file():
        return False
    try:
        result=subprocess.run(['/usr/bin/say','-v','?'],capture_output=True,text=True,timeout=5)
        return any(line.startswith('Samantha ') and 'en_US' in line for line in result.stdout.splitlines())
    except (OSError,subprocess.TimeoutExpired):
        return False

class Handler(BaseHTTPRequestHandler):
    def log_message(self,format,*args):
        pass

    def send(self,status,data,mime='application/json; charset=utf-8'):
        body=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):
            pass

    def host_ok(self):
        return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}

    def do_GET(self):
        if not self.host_ok():
            return self.send(403,{'error':'Local access only.'})
        parsed=urlparse(self.path)
        params=parse_qs(parsed.query)
        def param(k,default=''):
            return params.get(k,[default])[0]
        try:
            if parsed.path=='/api/state':
                return self.send(200,{**self.server.store.state(),'token':self.server.token})
            if parsed.path=='/api/graph':
                default=next((b['id'] for b in self.server.store.brains if not b.get('removedAt')), '')
                return self.send(200,self.server.store.graph(param('brain',default)))
            if parsed.path=='/api/note':
                return self.send(200,self.server.store.read(param('brain'),param('path')))
            if parsed.path=='/api/voice':
                return self.send(200,{'available':self.server.voice,'name':'Samantha','language':'en-US','local':True})
            if parsed.path=='/api/theme':
                return self.send(200,omarchy_theme())
            target=(WEB/('index.html' if parsed.path=='/' else unquote(parsed.path).lstrip('/'))).resolve()
            if not target.is_relative_to(WEB.resolve()) or not target.is_file():
                return self.send(404,{'error':'Not found.'})
            return self.send(200,target.read_bytes(),mimetypes.guess_type(target)[0] or 'application/octet-stream')
        except Problem as exc:
            self.send(exc.status,{'error':exc.message})
        except (OSError,UnicodeError):
            self.send(500,{'error':'Could not read the local files.'})

    def body(self):
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=7*1024*1024:
                raise Problem('Request is too large.',413)
            result=json.loads(self.rfile.read(size))
            if not isinstance(result,dict):
                raise Problem('Invalid request.')
            return result
        except (ValueError,UnicodeError):
            raise Problem('Invalid request.')

    def do_POST(self):
        if not self.host_ok() or self.headers.get('Origin')!='http://'+self.headers.get('Host','') or not hmac.compare_digest(self.headers.get('X-Neura-Token',''),self.server.token):
            return self.send(403,{'error':'This action must be started in the local app.'})
        try:
            body=self.body()
            if self.path=='/api/notes/reveal':
                return self.send(200,reveal_note(self.server.store,body.get('brain'),body.get('path')))
            if self.path=='/api/removals/preview':
                return self.send(200,self.server.store.removal_preview(body.get('brain'),body.get('path'),body.get('kind')))
            if self.path=='/api/removals':
                return self.send(200,self.server.store.remove(body.get('preview'),body.get('device',False),body.get('confirmName','')))
            if self.path=='/api/removals/list':
                return self.send(200,self.server.store.removed_items())
            if self.path=='/api/removals/restore':
                return self.send(200,self.server.store.restore(body.get('id')))
            if self.path=='/api/removals/forget/preview':
                return self.send(200,self.server.store.forget_preview(body.get('id')))
            if self.path=='/api/removals/forget':
                return self.send(200,self.server.store.forget(body.get('id'),body.get('revision')))
            if self.path=='/api/folders/browse':
                return self.send(200,self.server.store.browse(body.get('path'),body.get('query',''),body.get('offset',0)))
            if self.path=='/api/brains':
                if body.get('action') not in {'create','connect','access'}:
                    raise Problem('Unknown action.')
                if body['action']=='access':
                    brain=self.server.store.set_access(body.get('brain'),body.get('writable'))
                    return self.send(200,{'brain':brain})
                if body['action']=='connect' and not body.get('path'):
                    raise Problem('Enter the Brain folder path on this computer.')
                brain=self.server.store.add(body.get('name',''),body.get('path') if body['action']=='connect' else None,body.get('writable') is True)
                return self.send(201,{'brain':brain})
            if self.path=='/api/notes':
                result=self.server.store.write(body.get('brain'),body.get('path'),body.get('content'),body.get('revision'))
                return self.send(200,result)
            if self.path=='/api/folders':
                return self.send(201,self.server.store.folder(body.get('brain'),body.get('path')))
            if self.path=='/api/move':
                return self.send(200,self.server.store.move(body.get('brain'),body.get('source'),body.get('destination'),body.get('kind'),body.get('guard')))
            if self.path=='/api/speech':
                return self.speech(body.get('text'))
            self.send(404,{'error':'Unknown action.'})
        except Problem as exc:
            self.send(exc.status,{'error':exc.message})
        except OSError:
            self.send(500,{'error':'Could not save. Your edit is still open.'})

    def speech(self,text):
        global SPEECH_PROCESS
        if not self.server.voice:
            return self.send(503,{'error':'No local English voice is available.'})
        if not isinstance(text,str) or len(text)>2000:
            raise Problem('Invalid text for speech.')
        with SPEECH_LOCK:
            if SPEECH_PROCESS and SPEECH_PROCESS.poll() is None:
                SPEECH_PROCESS.terminate()
            if not text:
                return self.send(200,{'status':'stopped'})
            process=subprocess.Popen(['/usr/bin/say','-v','Samantha'],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            SPEECH_PROCESS=process
        try:
            process.communicate(text.encode(),timeout=180)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
        return self.send(200 if process.returncode in (0,-15) else 503,{'status':'finished' if process.returncode==0 else 'stopped'})

    def reject(self):
        self.send(405,{'error':'Action unavailable. File deletion is not supported.'})
    do_PUT=do_PATCH=do_DELETE=reject

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=4783)
    parser.add_argument('--data-dir',help='Directory for settings, new Brains and backups')
    parser.add_argument('--open',action='store_true',help='Open NEURA in your default browser')
    args=parser.parse_args()
    app=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    app.store=Store(args.data_dir)
    app.token=secrets.token_urlsafe(32)
    app.voice=has_voice()
    if args.open:
        import webbrowser
        threading.Timer(.5,webbrowser.open,args=(f'http://127.0.0.1:{args.port}/',)).start()
    print(f'NEURA 0.2 · http://127.0.0.1:{args.port} · {len(app.store.brains)} Brain(s)',flush=True)
    try:
        app.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if SPEECH_PROCESS and SPEECH_PROCESS.poll() is None:
            SPEECH_PROCESS.terminate()
        app.server_close()
