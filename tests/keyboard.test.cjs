const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const web=path.join(__dirname,'../web');
const context={window:{},interfaceHints:true,clean:s=>String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase()};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(web,'keyboard.js'),'utf8'),context);
const policy=context.window.NotrynKeyboard;
const app=fs.readFileSync(path.join(web,'app.js'),'utf8');
const catalogSource=app.slice(app.indexOf('const actionItems=()=>['),app.indexOf('function openShortcuts(){'));
for(const match of catalogSource.matchAll(/run:([a-zA-Z]\w*)[,}]/g))context[match[1]]=()=>{};
vm.runInContext(catalogSource+';globalThis.actions=actionItems();',context);
const actions=context.actions;
const event=(key,extra={})=>({key,...extra});
const match=(key,extra={},scope={})=>policy.match(actions,event(key,extra),scope)?.title||null;

test('all actual bindings leave every system modifier combination alone',()=>{
 for(const action of actions)for(const key of (Array.isArray(action.plain)?action.plain:[action.plain]).filter(Boolean)){
  for(let mask=1;mask<8;mask++)for(const shiftKey of [false,true]){
   assert.equal(match(key,{ctrlKey:!!(mask&1),metaKey:!!(mask&2),altKey:!!(mask&4),shiftKey},{graph:true}),null,action.title);
  }
 }
});
test('browser help, toolbar, refresh and developer keys are not bound',()=>{
 for(let i=1;i<=12;i++)for(const shiftKey of [false,true])assert.equal(match('F'+i,{shiftKey}),null);
 assert.equal(match('Escape',{shiftKey:true}),null,'Shift Esc belongs to the browser');
 for(const key of ['/',"'"])assert.equal(match(key),null,'Firefox quick find stays native');
});
test('typing, text selections, IME, AltGraph and consumed events are respected',()=>{
 for(const key of ['t','p','n','s','a','?','/','ArrowDown']){
  assert.equal(match(key,{}, {typing:true,graph:true}),null);
  assert.equal(match(key,{}, {selected:true,graph:true}),null);
  for(const extra of [{isComposing:true},{keyCode:229},{defaultPrevented:true},{getModifierState:key=>key==='AltGraph'}])assert.equal(match(key,extra,{graph:true}),null);
 }
});
test('new keyboard routes are unambiguous and retain deliberate Shift variants',()=>{
 for(const [key,title] of Object.entries({h:'Show / hide brain',q:'Filter notes',p:'Notes and commands',t:'Choose theme',a:'Toggle Iris',n:'New note',b:'Switch Brain',l:'Toggle library',s:'Save note',e:'Edit or finish editing',v:'Preview note',f:'Focus note / exit focus',w:'Switch pane','?':'Commands and shortcuts'}))assert.equal(match(key),title);
 assert.equal(match('H',{shiftKey:true}),'Show full Brain');
 assert.equal(match('N',{shiftKey:true}),'New folder');
 assert.equal(match('B',{shiftKey:true}),'Create a Brain');
 assert.equal(match('L',{shiftKey:true}),'Swap note and brain');
 assert.equal(match('W',{shiftKey:true}),'Switch pane');
 assert.equal(match('?',{shiftKey:true}),'Commands and shortcuts');
 for(const [key,title] of Object.entries({t:'Hide interface hints',r:'Recent notes',q:'Show Brain root',e:'Switch Write / Markdown',f:'Format text',d:'Removed items',m:'Note or folder actions',o:'Show note in folder',s:'Save and finish editing',a:'Toggle voice'}))assert.equal(match(key,{shiftKey:true}),title);
 assert.equal(match('c'),'Choose a folder');assert.equal(match('u'),'Back one folder');
 const seen=new Set();
 for(const action of actions)for(const key of (Array.isArray(action.plain)?action.plain:[action.plain]).filter(Boolean)){
  const signature=[key,!!action.plainShift,action.context||'global'].join(':');
  assert.ok(!seen.has(signature),'Duplicate binding '+signature);seen.add(signature);
  assert.equal(action.combo,undefined);
 }
});
test('brain controls are local to the canvas and keep shifted scrolling native',()=>{
 for(const key of ['ArrowDown','ArrowUp','j','k','PageDown','PageUp','+','-','0',' ']){
  assert.equal(match(key),null);
  assert.ok(match(key,{}, {graph:true}));
 }
 assert.equal(match(' ',{shiftKey:true},{graph:true}),null);
 assert.equal(match('ArrowDown',{shiftKey:true},{graph:true}),null);
 assert.equal(match('+',{shiftKey:true},{graph:true}),'Zoom in');
});
test('turning off character shortcuts retains standard navigation keys',()=>{
 for(const key of ['p','t','a','s','?','/','j','+','0'])assert.equal(match(key,{}, {enabled:false,graph:true}),null);
 assert.equal(match('Escape',{}, {enabled:false}),'Close panel / leave focus');
 assert.equal(match('ArrowDown',{}, {enabled:false,graph:true}),'Rotate brain');
});
test('command search finds topics and aliases in the real catalog',()=>{
 const find=q=>Array.from(actions.filter(a=>context.matchesCommand(a,q)),a=>a.title);
 for(const q of ['theme','tema','TEMAS','appearance colors','omarchy'])assert.deepEqual(find(q),['Choose theme']);
 assert.deepEqual(find('assistente'),['Toggle Iris']);
 for(const q of ['back','voltar','pasta anterior','u'])assert.deepEqual(find(q),['Back one folder']);
 assert.ok(find('Brain view').includes('Rotate brain'));
 assert.deepEqual(find('nonexistent-command-xyz'),[]);
 assert.deepEqual(find('advanced'),['Hide interface hints']);
});
test('key searches distinguish exact letters and Shift variants',()=>{
 const find=q=>Array.from(actions.filter(a=>context.matchesCommand(a,q)),a=>a.title);
 assert.deepEqual(find('T'),['Choose theme']);
 assert.deepEqual(find('Shift+H'),['Show full Brain']);
 assert.deepEqual(find('Shift H'),['Show full Brain']);
 assert.deepEqual(find('Shift S'),['Save and finish editing']);
 assert.deepEqual(find('Shift T'),['Hide interface hints']);
 assert.deepEqual(find('+'),['Zoom in']);
 assert.deepEqual(find('−'),['Zoom out']);
 assert.deepEqual(find('ArrowUp'),['Rotate brain']);
});
test('less frequent and visual actions are available by searchable command name',()=>{
 for(const title of ['Manage Brain access','Remove this Brain from Notryn','Expand all folders','Collapse all folders','Show note in folder','Configure keyboard shortcuts','Heading 1','Heading 2','Heading 3','Bullet list','Numbered list','Blockquote','Code block','Inline code','Insert or edit link','Undo','Redo']){
  const action=actions.find(a=>a.title===title);assert.ok(action,title);assert.equal(typeof action.run,'function');assert.ok(context.matchesCommand(action,title),title);
 }
});
test('editor commands use Ctrl or Cmd and never consume uppercase typing or other system chords',()=>{
 const edit=(key,extra={},editing=true)=>policy.matchEditor(actions,event(key,extra),{editing})?.title||null;
 for(const modifier of [{ctrlKey:true},{metaKey:true}]){
  assert.equal(edit('s',modifier),'Save note');assert.equal(edit('Enter',modifier),'Preview note');
  assert.equal(edit('s',modifier,false),null);
  for(const bad of [{shiftKey:true},{altKey:true},{isComposing:true},{keyCode:229},{defaultPrevented:true},{getModifierState:()=>true}])assert.equal(edit('s',{...modifier,...bad}),null);
  for(const key of ['p','P','t','n','w','r','Tab'])assert.equal(edit(key,modifier),null);
 }
 for(const key of ['s','S','p','P','Enter']){assert.equal(edit(key),null);assert.equal(edit(key,{shiftKey:true}),null);}
 assert.equal(edit('s',{ctrlKey:true,metaKey:true}),null);
});
