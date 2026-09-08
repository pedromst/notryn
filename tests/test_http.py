import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Handler
from store import Store

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.http.store=Store(Path(self.temp.name)/'state');self.http.token='test-only-session-token';self.http.instance_id='test-instance'
        self.origin='http://127.0.0.1:'+str(self.http.server_port)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();self.temp.cleanup()
    def request(self,path,payload=None,headers=None):
        body=json.dumps(payload).encode() if payload is not None else None
        req=urllib.request.Request(self.origin+path,data=body,headers=headers or {})
        try:
            with urllib.request.urlopen(req) as r:return r.status,json.loads(r.read())
        except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
    def test_write_requires_origin_and_session_token(self):
        body={'action':'create','name':'Test'}
        self.assertEqual(self.request('/api/brains',body)[0],403)
        self.assertEqual(self.request('/api/brains',body,{'Origin':'https://other.example','X-Notryn-Token':self.http.token})[0],403)
        self.assertEqual(self.request('/api/brains',body,{'Origin':self.origin,'X-Notryn-Token':'wrong'})[0],403)
        code,data=self.request('/api/brains',body,{'Origin':self.origin,'X-Notryn-Token':self.http.token});self.assertEqual(code,201)
        self.assertEqual(data['brain']['name'],'Test')
    def test_readonly_source_rejects_browser_writes(self):
        folder=Path(self.temp.name)/'existing';folder.mkdir();(folder/'one.md').write_text('original')
        brain=self.http.store.add('Existing',str(folder),False)
        code,_=self.request('/api/notes',{'brain':brain['id'],'path':'one.md','content':'overwrite','revision':None},{'Origin':self.origin,'X-Notryn-Token':self.http.token})
        self.assertEqual(code,403);self.assertEqual((folder/'one.md').read_text(),'original')
    def test_unknown_host_cannot_read_state(self):
        self.assertEqual(self.request('/api/state',headers={'Host':'external.example'})[0],403)
    def test_runtime_identifies_only_this_local_instance(self):
        code,data=self.request('/api/runtime')
        self.assertEqual(code,200);self.assertEqual(data['app'],'notryn')
        self.assertEqual(data['instance'],'test-instance');self.assertTrue(data['version'])
    def test_removal_preview_execution_list_and_restore_require_local_session(self):
        brain=self.http.store.add('Removal test');bid=brain['id'];self.http.store.write(bid,'A.md','original',None)
        paths=['/api/removals/preview','/api/removals','/api/removals/list','/api/removals/restore']
        for path in paths:
            for headers in [{},{'Origin':'https://elsewhere.example','X-Notryn-Token':self.http.token},{'Origin':self.origin,'X-Notryn-Token':'wrong'}]:
                self.assertEqual(self.request(path,{},headers)[0],403)
            self.assertEqual(self.request(path)[0],404)
        headers={'Origin':self.origin,'X-Notryn-Token':self.http.token}
        code,preview=self.request(paths[0],{'brain':bid,'path':'A.md','kind':'note'},headers);self.assertEqual(code,200)
        code,result=self.request(paths[1],{'preview':preview['id']},headers);self.assertEqual(code,200);self.assertEqual(result['mode'],'hidden')
        self.assertEqual((Path(brain['root'])/'A.md').read_text(),'original')
        self.assertEqual(self.request('/api/note?brain='+bid+'&path=A.md')[0],404)
        self.assertEqual(len(self.request(paths[2],{},headers)[1]['items']),1)
        self.assertEqual(self.request(paths[3],{'id':result['entry']},headers)[0],200)
        self.assertEqual(self.http.store.read(bid,'A.md')['content'],'original')
    def test_move_requires_local_origin_token_and_write_access(self):
        brain=self.http.store.add('Moves');bid=brain['id']
        self.http.store.write(bid,'One.md','# One',None);self.http.store.folder(bid,'Ideas')
        body={'brain':bid,'source':'One.md','destination':'Ideas','kind':'note'}
        for headers in [{},{'Origin':'https://other.example','X-Notryn-Token':self.http.token},{'Origin':self.origin,'X-Notryn-Token':'wrong'}]:
            self.assertEqual(self.request('/api/move',body,headers)[0],403)
        code,result=self.request('/api/move',body,{'Origin':self.origin,'X-Notryn-Token':self.http.token})
        self.assertEqual(code,200);self.assertEqual(result['path'],'Ideas/One.md')
        self.assertEqual(self.http.store.read(bid,'Ideas/One.md')['content'],'# One')
        self.http.store.brains[0]['readOnly']=True
        body.update(source='Ideas/One.md',destination='')
        self.assertEqual(self.request('/api/move',body,{'Origin':self.origin,'X-Notryn-Token':self.http.token})[0],403)

    def test_rename_requires_local_origin_token_and_write_access(self):
        brain=self.http.store.add('Renames');bid=brain['id']
        self.http.store.write(bid,'Old.md','# Old',None)
        body={'brain':bid,'source':'Old.md','name':'New','kind':'note'}
        for headers in [{},{'Origin':'https://other.example','X-Notryn-Token':self.http.token},{'Origin':self.origin,'X-Notryn-Token':'wrong'}]:
            self.assertEqual(self.request('/api/rename',body,headers)[0],403)
        headers={'Origin':self.origin,'X-Notryn-Token':self.http.token}
        code,result=self.request('/api/rename',body,headers)
        self.assertEqual(code,200);self.assertEqual(result['path'],'New.md')
        self.assertEqual(self.http.store.read(bid,'New.md')['content'],'# Old')
        self.http.store.brains[-1]['readOnly']=True
        body.update(source='New.md',name='Again')
        self.assertEqual(self.request('/api/rename',body,headers)[0],403)
    def test_folder_browsing_requires_local_origin_and_token(self):
        folder=Path(self.temp.name)/'Browse here';folder.mkdir();(folder/'Child').mkdir()
        body={'path':str(folder)}
        for headers in [{},{'Origin':'https://other.example','X-Notryn-Token':self.http.token},{'Origin':self.origin,'X-Notryn-Token':'wrong'}]:
            code,data=self.request('/api/folders/browse',body,headers)
            self.assertEqual(code,403);self.assertNotIn('folders',data)
        self.assertEqual(self.request('/api/folders/browse')[0],404)
        before=self.http.store.config.read_bytes()
        code,data=self.request('/api/folders/browse',body,{'Origin':self.origin,'X-Notryn-Token':self.http.token})
        self.assertEqual(code,200);self.assertEqual([f['name'] for f in data['folders']],['Child'])
        self.assertEqual(self.http.store.config.read_bytes(),before)
    def test_quoted_folder_connects_through_http(self):
        folder=Path(self.temp.name)/'Brain with spaces';folder.mkdir();(folder/'Projects').mkdir();(folder/'Projects'/'First.md').write_text('# First')
        code,data=self.request('/api/brains',{'action':'connect','name':'Tester','path':"'"+str(folder)+"'"},{'Origin':self.origin,'X-Notryn-Token':self.http.token})
        self.assertEqual(code,201);self.assertEqual(data['brain']['root'],str(folder.resolve()));self.assertTrue(data['brain']['readOnly'])
        self.assertEqual(data['graph']['brain']['id'],data['brain']['id'])
        self.assertEqual(data['graph']['folders'],['Projects'])
        self.assertEqual([node['path'] for node in data['graph']['nodes']],['Projects/First.md'])
    def test_brain_access_changes_only_through_the_local_authenticated_api(self):
        folder=Path(self.temp.name)/'Access';folder.mkdir();brain=self.http.store.add('Access',str(folder),False)
        payload={'action':'access','brain':brain['id'],'writable':True};headers={'Origin':self.origin,'X-Notryn-Token':self.http.token}
        self.assertEqual(self.request('/api/brains',payload)[0],403)
        code,data=self.request('/api/brains',payload,headers);self.assertEqual(code,200);self.assertFalse(data['brain']['readOnly'])
        self.assertEqual(self.request('/api/brains',{**payload,'writable':'yes'},headers)[0],400)
    def test_state_has_no_personal_defaults(self):
        code,data=self.request('/api/state');self.assertEqual(code,200);self.assertEqual(data['brains'],[]);self.assertNotIn('agent',data)

    def test_reveal_requires_local_session_before_native_dispatch(self):
        body={'brain':'fixture','path':'projects/A note.md'}
        headers={'Origin':self.origin,'X-Notryn-Token':self.http.token}
        with patch('server.reveal_note',return_value={'requested':True,'mode':'selected'}) as reveal:
            for bad in [{},{**headers,'Origin':'https://external.example'},{**headers,'X-Notryn-Token':'wrong'}]:
                self.assertEqual(self.request('/api/notes/reveal',body,bad)[0],403)
            self.assertEqual(self.request('/api/notes/reveal')[0],404)
            reveal.assert_not_called()
            self.assertEqual(self.request('/api/notes/reveal',body,headers)[0],200)
            reveal.assert_called_once_with(self.http.store,'fixture','projects/A note.md')

    def test_forget_requires_local_authentication_and_review(self):
        brain=self.http.store.add('Forget test')
        preview=self.http.store.removal_preview(brain['id'],'','brain')
        removed=self.http.store.remove(preview['id']);payload={'id':removed['entry']}
        headers={'Origin':self.origin,'X-Notryn-Token':self.http.token}
        for endpoint in ['/api/removals/forget/preview','/api/removals/forget']:
            for bad in [{},{**headers,'Origin':'https://external.example'},{**headers,'X-Notryn-Token':'bad'}]:
                self.assertEqual(self.request(endpoint,payload,bad)[0],403)
        code,review=self.request('/api/removals/forget/preview',payload,headers);self.assertEqual(code,200)
        self.assertEqual(self.request('/api/removals/forget',payload,headers)[0],409)
        code,result=self.request('/api/removals/forget',{**payload,'revision':review['revision']},headers)
        self.assertEqual(code,200);self.assertTrue(result['forgotten']);self.assertTrue(Path(brain['root']).is_dir())
    def test_theme_is_readonly_and_host_restricted(self):
        palette={'available':True,'name':'Test','palette':{'background':'#111111','foreground':'#eeeeee','accent':'#aaffcc'}}
        before=self.http.store.config.read_bytes()
        with patch('server.omarchy_theme',return_value=palette):
            self.assertEqual(self.request('/api/theme'),(200,palette))
            self.assertEqual(self.request('/api/theme',headers={'Host':'external.example'})[0],403)
        self.assertEqual(self.http.store.config.read_bytes(),before)
if __name__=='__main__':unittest.main()
