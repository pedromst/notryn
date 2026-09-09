const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};

function saveHarness(){
 const disk=deferred(),graph=deferred(),messages=[];
 const elements={'#editor':{value:'# Updated'},'#document-error':{},'#toast':{}};
 const state={brain:'test',note:{path:'Note.md',content:'# Original',revision:'old'},editing:true,dirty:true};
 let refreshes=0;
 const context={state,$:s=>elements[s],writable:()=>true,updateSaveState:()=>{},clearTimeout:()=>{},
  updateEditor:()=>{state.dirty=elements['#editor'].value!==state.note.content;},
  finishEditing:()=>{state.editing=false;},toast:message=>messages.push(message),api:()=>disk.promise,
  loadGraph:()=>{refreshes++;return graph.promise;}};
 vm.createContext(context);
 vm.runInContext(source.slice(source.indexOf('async function saveNote('),source.indexOf("$('#save-note').onclick")),context);
 return {context,state,elements,disk,graph,messages,refreshes:()=>refreshes};
}
test('save waits for disk confirmation but never waits for slow graph indexing',async()=>{
 const h=saveHarness(),save=h.context.saveNote({finish:true});
 assert.equal(h.state.saving,true);assert.equal(h.messages.length,0);assert.equal(h.refreshes(),0);
 h.disk.resolve({revision:'new'});await save;
 assert.equal(h.state.saving,false);assert.equal(h.state.editing,false);assert.equal(h.state.note.revision,'new');
 assert.equal(h.refreshes(),1);assert.match(h.messages[0],/Saved to disk/);
 h.graph.resolve();
});
test('edits typed during saving stay open and unsaved',async()=>{
 const h=saveHarness(),save=h.context.saveNote({finish:true});h.elements['#editor'].value='# Newer typing';
 h.disk.resolve({revision:'new'});await save;
 assert.equal(h.state.note.content,'# Updated');assert.equal(h.state.dirty,true);assert.equal(h.state.editing,true);
 assert.match(h.messages[0],/Newer edits/);h.graph.resolve();
});
test('failed disk write never reports success or refreshes the graph',async()=>{
 const h=saveHarness(),save=h.context.saveNote({finish:true});h.disk.reject(Error('Conflict'));await save;
 assert.equal(h.state.note.revision,'old');assert.equal(h.state.dirty,true);assert.equal(h.state.editing,true);
 assert.equal(h.messages.length,0);assert.equal(h.refreshes(),0);assert.equal(h.elements['#document-error'].textContent,'Conflict');
});
test('desktop shell permits half, third and quarter tiles to reach the responsive layout',()=>{
 const main=fs.readFileSync(path.join(__dirname,'../desktop/main.cjs'),'utf8');let options;
 class BrowserWindow{constructor(value){options=value;this.webContents={session:{setPermissionRequestHandler(){}},setWindowOpenHandler(){},on(){}};}loadURL(){}on(){}}
 const context={BrowserWindow,process:{platform:'linux'},PORT:4783};vm.createContext(context);
 vm.runInContext(main.slice(main.indexOf('function createWindow()'),main.indexOf('if (!app.requestSingleInstanceLock()'))+';createWindow();',context);
 for(const [width,height] of [[960,540],[640,360],[480,360],[320,320]]){
  assert.ok(options.minWidth<=width);assert.ok(options.minHeight<=height);
 }
 assert.equal(options.width,1500);assert.equal(options.height,940);
 assert.equal(options.webPreferences.sandbox,true);assert.equal(options.webPreferences.nodeIntegration,false);
});
test('desktop top bar moves the macOS window without swallowing its controls',()=>{
 const styles=fs.readFileSync(path.join(__dirname,'../web/style.css'),'utf8');
 assert.match(styles,/\.topbar\s*\{[^}]*-webkit-app-region:drag/);
 assert.match(styles,/\.topbar :is\(button,input,textarea,select,a\)\s*\{[^}]*-webkit-app-region:no-drag/);
});
