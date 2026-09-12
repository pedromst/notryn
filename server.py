#!/usr/bin/env python3
"""NOTRYN local application server. Standard library only, Python 3.9+."""
import argparse
import hmac
import json
import mimetypes
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from store import Store, Problem
from themes import omarchy_theme
from desktop import reveal_note
from notryn_version import VERSION

HERE=Path(__file__).resolve().parent
RESOURCE_ROOT=Path(getattr(sys,'_MEIPASS',HERE))
WEB=RESOURCE_ROOT/'web'
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
            if parsed.path=='/api/runtime':
                return self.send(200,{'app':'notryn','version':VERSION,'instance':self.server.instance_id})
            if parsed.path=='/api/graph':
                default=next((b['id'] for b in self.server.store.brains if not b.get('removedAt')), '')
                return self.send(200,self.server.store.graph(param('brain',default)))
            if parsed.path=='/api/graph/revision':
                default=next((b['id'] for b in self.server.store.brains if not b.get('removedAt')), '')
                return self.send(200,self.server.store.graph_revision(param('brain',default)))
            if parsed.path=='/api/note':
                return self.send(200,self.server.store.read(param('brain'),param('path')))
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
        if not self.host_ok() or self.headers.get('Origin')!='http://'+self.headers.get('Host','') or not hmac.compare_digest(self.headers.get('X-Notryn-Token',''),self.server.token):
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
                if body['action'] in {'create','connect'} and not body.get('path'):
                    raise Problem('Choose where to create the Brain.' if body['action']=='create' else 'Enter the Brain folder path on this computer.')
                brain=self.server.store.add(
                    body.get('name',''),
                    existing=body.get('path') if body['action']=='connect' else None,
                    writable=body.get('writable') is True,
                    create_in=body.get('path') if body['action']=='create' else None,
                )
                # Return the first inventory with the successful connection. This
                # makes a newly connected Brain usable immediately, without a
                # second state request racing the first graph load in the shell.
                return self.send(201,{'brain':brain,'graph':self.server.store.graph(brain['id'])})
            if self.path=='/api/notes':
                result=self.server.store.write(body.get('brain'),body.get('path'),body.get('content'),body.get('revision'))
                return self.send(200,result)
            if self.path=='/api/folders':
                return self.send(201,self.server.store.folder(body.get('brain'),body.get('path')))
            if self.path=='/api/move':
                return self.send(200,self.server.store.move(body.get('brain'),body.get('source'),body.get('destination'),body.get('kind'),body.get('guard')))
            if self.path=='/api/rename':
                return self.send(200,self.server.store.rename(body.get('brain'),body.get('source'),body.get('name'),body.get('kind'),body.get('guard')))
            self.send(404,{'error':'Unknown action.'})
        except Problem as exc:
            self.send(exc.status,{'error':exc.message})
        except OSError:
            self.send(500,{'error':'Could not save. Your edit is still open.'})

    def reject(self):
        self.send(405,{'error':'Action unavailable. File deletion is not supported.'})
    do_PUT=do_PATCH=do_DELETE=reject

def serve(port=4783,data_dir=None,open_browser=False,instance_id=None):
    global SPEECH_PROCESS
    app=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    app.store=Store(data_dir)
    app.token=secrets.token_urlsafe(32)
    app.instance_id=instance_id or secrets.token_urlsafe(24)
    if open_browser:
        import webbrowser
        threading.Timer(.5,webbrowser.open,args=(f'http://127.0.0.1:{port}/',)).start()
    print(f'NOTRYN {VERSION} · http://127.0.0.1:{port} · {len(app.store.brains)} Brain(s)',flush=True)
    try:
        app.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.server_close()
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=4783)
    parser.add_argument('--data-dir',help='Directory for settings, new Brains and backups')
    parser.add_argument('--open',action='store_true',help='Open NOTRYN in your default browser')
    args=parser.parse_args()
    raise SystemExit(serve(args.port,args.data_dir,args.open))
