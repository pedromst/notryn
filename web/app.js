'use strict';
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const state={brains:[],brain:null,token:'',data:{nodes:[],edges:[],folders:[]},graphView:null,folderPath:'',selected:null,note:null,editing:false,dirty:false,newNote:false,query:'',group:null,recent:false,closed:new Set(),noteSerial:0,loadSerial:0};
state.saving=false;
let singleKeys=true;
try{singleKeys=localStorage.getItem('notryn-single-keys')!=='off';}catch{}
let interfaceHints=true;
try{interfaceHints=localStorage.getItem('notryn-interface-hints')!=='off';}catch{}
const clean=s=>String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
function icon(name){const svg=document.createElementNS('http://www.w3.org/2000/svg','svg'),use=document.createElementNS(svg.namespaceURI,'use');svg.classList.add('icon');use.setAttribute('href','/icons.svg#'+name);svg.append(use);return svg;}
function toast(text){$('#toast').textContent=text;$('#toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').hidden=true,3800);}
const graph=new NotrynGraph($('#graph'),id=>openGraphItem(id));
function endpoint(path,params){return path+'?'+new URLSearchParams(params);}
async function api(url,data){const opts=data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Notryn-Token':state.token},body:JSON.stringify(data)};const r=await fetch(url,opts);let body;try{body=await r.json();}catch{throw Error('The local app did not respond. Check that the server is running.');}if(!r.ok){const e=Error(body.error||'Could not complete the action.');e.status=r.status;throw e;}return body;}
function current(){return state.brains.find(b=>b.id===state.brain);}
function writable(){return !!current()&&!current().readOnly;}
function visible(n){return NotrynHierarchy.matchesNote(n,state.query);}
function neighbors(id){return state.data.edges.filter(e=>e.source===id||e.target===id).map(e=>state.data.nodes.find(n=>n.id===(e.source===id?e.target:e.source))).filter(Boolean);}
function renderGraphView(){
 state.graphView=NotrynHierarchy.view(state.data,state.folderPath,state.query,state.selected);graph.setData(state.graphView);graph.filter=()=>true;
 graph.select(graph.ids.has(state.selected)?state.selected:null);updateBrainScope();
}
function openGraphItem(id){return id.startsWith('@folder:')?navigateBrainFolder(id.slice(8)):openNote(id);}
function navigateBrainFolder(path,{focus=false}={}){
 path=NotrynHierarchy.normalize(path);if(path&&!state.data.folders.includes(path))return toast('That folder is no longer available.');
 state.folderPath=path;state.query='';state.group=null;state.recent=false;$('#search').value='';
 renderGraphView();renderLegend();renderTree();$('#file-tree').scrollTop=0;graph.fit();
 if(focus)$('#graph').focus({preventScroll:true});
}
function upBrainFolder({library=false}={}){if(!state.folderPath)return toast('You are already at the Brain root.');const previous=state.folderPath;navigateBrainFolder(NotrynHierarchy.parent(previous),{focus:!library});if(library)($$('#file-tree .tree-row').find(row=>row.dataset.key==='folder:'+previous)||$('#library-location-name')).focus({preventScroll:true});}
function showDialog(id){const d=$(id);if(!d.open)d.showModal();return d;}
$$('[data-close]').forEach(b=>b.onclick=()=>b.closest('dialog').close());
// Search inputs consume Escape in some browsers. Follow the dialog's normal
// cancellation route, including any guard against closing during an operation.
document.addEventListener('keydown',e=>{
 if(e.key!=='Escape'||e.shiftKey||!NotrynKeyboard.available(e)||!e.target.matches('dialog input[type="search"]'))return;
 const dialog=e.target.closest('dialog');if(!dialog.open)return;
 e.preventDefault();e.stopPropagation();if(dialog.dispatchEvent(new Event('cancel',{cancelable:true})))dialog.close();
},true);
// Include buttons in the normal Tab order even on mobile WebKit. Keep focus
// within modal dialogs; at workspace edges, leave browser navigation native.
document.addEventListener('keydown',e=>{
 if(e.key!=='Tab'||!NotrynKeyboard.available(e))return;
 const active=document.activeElement,dialog=active.closest('dialog[open]');
 if(!dialog&&$('dialog[open]'))return;
 const controls=[...(dialog||document.body).querySelectorAll('button,a[href],input,select,textarea,[tabindex],[contenteditable="true"]')].filter(node=>
  (node.tabIndex>=0||node.isContentEditable&&!node.hasAttribute('tabindex'))&&!node.matches(':disabled')&&!node.closest('[hidden],[inert]')&&node.getClientRects().length&&getComputedStyle(node).visibility!=='hidden');
 if(!controls.length)return;
 const index=controls.indexOf(active),next=index<0?(e.shiftKey?controls.length-1:0):index+(e.shiftKey?-1:1);
 if(!dialog&&(next<0||next>=controls.length))return;
 e.preventDefault();controls[(next+controls.length)%controls.length].focus();
});
// Keep required-field messages in English even when the browser uses another language.
$$('input[required],#brain-form-path').forEach(input=>{
 input.addEventListener('invalid',()=>{if(input.validity.valueMissing)input.setCustomValidity('Please complete this field.');});
 input.addEventListener('input',()=>input.setCustomValidity(''));
});
function canLeave(){if(state.saving){toast('Saving to disk. Please wait a moment.');return Promise.resolve(false);}if(!state.dirty)return Promise.resolve(true);return new Promise(resolve=>{const d=showDialog('#discard-dialog');$('#keep-editing').onclick=()=>{d.close();resolve(false);};$('#discard-editing').onclick=()=>{d.close();state.dirty=false;resolve(true);};d.oncancel=e=>{e.preventDefault();d.close();resolve(false);};});}
function closeDocumentUnsafe(){setNoteFocus(false);state.noteSerial++;state.selected=null;state.note=null;state.editing=false;state.dirty=false;$('#document').hidden=true;$('#document-error').hidden=true;graph.select(null);if(state.graphView?.connectionCount)renderGraphView();rich.setVisible(false);renderTree();}
async function closeDocument(){if(await canLeave())closeDocumentUnsafe();}
async function loadBrains(){const result=await api('/api/state');state.token=result.token;state.brains=result.brains;state.remotePreview=!!result.remotePreview;['#welcome-create','#welcome-open','#open-removed','#brains-removed'].forEach(id=>$(id).hidden=state.remotePreview);$('#brain-actions').hidden=false;['#add-new-brain','#add-existing-brain'].forEach(id=>$(id).disabled=state.remotePreview);$('#brains-preview-note').hidden=!state.remotePreview;$('#brain-count').textContent=state.brains.length+(state.brains.length===1?' Brain':' Brains');return result;}
function rememberBrain(brain){const existing=state.brains.find(item=>item.id===brain.id);state.brains=[...state.brains.filter(item=>item.id!==brain.id),{...existing,...brain}];$('#brain-count').textContent=state.brains.length+(state.brains.length===1?' Brain':' Brains');}
async function switchBrain(id,{brain=null,graphData=null}={}){if(!await canLeave())return;if(brain)rememberBrain(brain);closeDocumentUnsafe();state.brain=id;state.query='';state.group=null;state.folderPath='';state.closed.clear();$('#search').value='';localStorage.setItem('notryn-brain',id);await loadGraph(graphData);}
async function loadGraph(graphData=null){const serial=++state.loadSerial;const b=current();document.body.classList.toggle('no-brain',!b);$('#brain-name').textContent=b?.name||'Your Brains';$('#new-note').disabled=!b||b.readOnly;$('#new-folder').disabled=!b||b.readOnly;$('#new-note').title=b?.readOnly?'This Brain is read-only':'New note (N)';$('#access-state').replaceChildren(icon(b?.readOnly?'lock':'folder'),document.createTextNode(b?.readOnly?'Read-only':'Local files'));$('#welcome').hidden=!!b;$('#empty-brain').hidden=true;
 if(!b){state.data={nodes:[],edges:[],folders:[]};state.folderPath='';renderGraphView();renderTree();return;}
 $('#refresh').disabled=true;
 try{const data=graphData||await api(endpoint('/api/graph',{brain:b.id}));if(serial!==state.loadSerial)return;state.data=data;while(state.folderPath&&!data.folders.includes(state.folderPath))state.folderPath=NotrynHierarchy.parent(state.folderPath);if(state.folderPolicyBrain!==b.id){state.closed=new Set(data.folders.filter(f=>f.includes('/')||data.folders.length>60));state.folderPolicyBrain=b.id;}state.brains=state.brains.map(x=>x.id===b.id?data.brain:x);renderGraphView();$('#note-total').textContent=data.nodes.length;$('#empty-brain').hidden=data.nodes.length>0;$('#empty-create').disabled=!writable();$('#notebook-create').disabled=!writable();$('#empty-brain p').textContent=writable()?'Create your first note. Connections follow.':'This folder does not contain any Markdown notes yet.';renderTree();renderLegend();if(data.skipped)toast(data.skipped+' files were skipped (size, format or count limit).');}
 catch(e){$('#graph-summary').textContent='Brain unavailable';$('#file-tree').replaceChildren(el('p','empty-list',e.message));toast(e.message);}
 finally{$('#refresh').disabled=false;}}
function renderLegend(){
 const box=$('#legend');box.replaceChildren();
 if(state.folderPath){
  const back=el('button','legend-back folder-back');back.id='legend-back';back.append(icon('arrow'),el('span','','Back'),el('kbd','','U'));
  back.setAttribute('aria-label','Back to parent folder');back.setAttribute('aria-keyshortcuts','U');
  back.title='Back to '+(NotrynHierarchy.parent(state.folderPath)||'Brain root')+' (U)';
  back.onclick=upBrainFolder;box.append(back);
 }
 const all=el('button','legend-all','All');all.id='legend-all';
 all.title='Show the Brain root';all.classList.toggle('active',!state.folderPath&&!state.query);all.setAttribute('aria-pressed',String(!state.folderPath&&!state.query));all.onclick=()=>navigateBrainFolder('',{focus:true});box.append(all);
 for(const folder of NotrynHierarchy.navigation(state.data,state.folderPath)){
  const active=folder===state.folderPath,b=el('button',active?'legend-folder active':'legend-folder');
  b.append(el('span','',NotrynHierarchy.name(folder)));b.dataset.colorGroup=NotrynHierarchy.folderId(folder);
  b.style.setProperty('--color',graph.color(b.dataset.colorGroup));b.setAttribute('aria-pressed',String(active));
  b.title=active?folder:'Open '+folder;b.onclick=()=>navigateBrainFolder(folder,{focus:true});box.append(b);
 }
 box.scrollLeft=0;updateBrainScope();
}
function renderTree(){
 updateBrainScope();
 renderLibraryLocation();
 const box=$('#file-tree'),focused=box.contains(document.activeElement)?document.activeElement.dataset.key:null;
 const preferred=focused||state.libraryKey;box.replaceChildren();
 const markRow=(row,folder)=>{
  row.dataset.colorGroup=NotrynHierarchy.folderId(folder);
  row.style.setProperty('--color',graph.color(row.dataset.colorGroup));
  const marker=el('span','tree-marker');marker.setAttribute('aria-hidden','true');row.append(marker);
 };
 $('#all-notes').classList.toggle('active',!state.recent);$('#recent-notes').classList.toggle('active',state.recent);
 const nodes=state.data.nodes.filter(visible),noteRow=n=>{
  const b=el('button','tree-row'+(n.id===state.selected?' active':''));markRow(b,n.folder);b.append(el('span','',NotrynHierarchy.filename(n)));b.setAttribute('aria-label',NotrynHierarchy.filename(n)+', note');
  b.title=n.path+' · '+n.title;b.dataset.key='note:'+n.id;b.dataset.parent=n.folder;b.setAttribute('aria-current',String(n.id===state.selected));b.onclick=()=>openNote(n.id);return b;
 };
 if(state.recent||state.query){(state.query?NotrynHierarchy.searchNotes(state.data,state.query):nodes.sort((a,b)=>b.updatedAt.localeCompare(a.updatedAt))).forEach(n=>box.append(noteRow(n)));}
 else{
  for(const f of NotrynHierarchy.directFolders(state.data,state.folderPath)){
   const item=state.graphView?.nodes.find(node=>node.id===NotrynHierarchy.folderId(f)),b=el('button','tree-row folder-row');
   const count=item?.count||0;
   b.dataset.key='folder:'+f;b.dataset.parent=state.folderPath;b.title=f+' · '+count+(count===1?' item':' items');b.setAttribute('aria-label','Open folder '+f+', '+count+(count===1?' item':' items'));
   markRow(b,f);b.append(el('span','',NotrynHierarchy.name(f)));
   b.onclick=()=>navigateBrainFolder(f);box.append(b);
  }
  nodes.filter(n=>n.folder===state.folderPath).sort((a,b)=>a.path.localeCompare(b.path)).forEach(n=>box.append(noteRow(n)));
 }
 const rows=[...box.querySelectorAll('.tree-row')],entry=rows.find(b=>b.dataset.key===preferred)||rows.find(b=>b.getAttribute('aria-current')==='true')||rows[0];
 rows.forEach(b=>{b.tabIndex=b===entry?0:-1;window.NotrynFiles?.decorate(b);});
 if(focused&&entry)entry.focus({preventScroll:true});
 if(!box.children.length)box.append(el('div','empty-list',state.query?'No notes match your search.':state.recent?'No recent notes.':'This folder is empty.'));
}
function renderLibraryLocation(){
 const brain=current(),name=state.folderPath?NotrynHierarchy.name(state.folderPath):brain?.name||'Your Brains';
 $('#library-toolbar').hidden=!brain;
 const location=$('#library-location-name');location.textContent=name;location.title=state.folderPath||name;
 const back=$('#library-back');back.disabled=!state.folderPath;updateControlHint(back);
 for(const id of ['library-new-note','new-folder']){
  const button=$('#'+id);button.disabled=!writable();updateControlHint(button);
 }
}
$('#file-tree').onfocusin=e=>{const row=e.target.closest('.tree-row');if(!row)return;state.libraryKey=row.dataset.key;$$('#file-tree .tree-row').forEach(b=>b.tabIndex=b===row?0:-1);};
$('#file-tree').onkeydown=e=>{
 if(!NotrynKeyboard.available(e)||e.shiftKey||!['ArrowDown','ArrowUp','ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
 const rows=$$('#file-tree .tree-row'),row=e.target.closest('.tree-row'),i=rows.indexOf(row);if(i<0)return;e.preventDefault();
 let target;
 if(e.key==='ArrowDown')target=rows[Math.min(rows.length-1,i+1)];
 if(e.key==='ArrowUp')target=rows[Math.max(0,i-1)];
 if(e.key==='Home')target=rows[0];if(e.key==='End')target=rows.at(-1);
 if(e.key==='ArrowRight'&&row.dataset.key?.startsWith('folder:'))row.click();
 if(e.key==='ArrowLeft'&&state.folderPath){navigateBrainFolder(NotrynHierarchy.parent(state.folderPath));target=$('#file-tree .tree-row');}
 target?.focus();
};
$('#search').addEventListener('keydown',e=>{if(!NotrynKeyboard.available(e)||e.shiftKey||!['ArrowDown','Enter'].includes(e.key))return;const first=$('#file-tree .tree-row');if(first){e.preventDefault();first.focus();if(e.key==='Enter')first.click();}});
$('#library-back').onclick=()=>upBrainFolder({library:true});
$('#search').oninput=e=>{state.query=clean(e.target.value.trim());renderGraphView();renderLegend();renderTree();};$('#all-notes').onclick=clearBrainFilters;$('#recent-notes').onclick=()=>{state.recent=true;renderTree();};$('#refresh').onclick=()=>loadGraph();

function updateBrainScope(){
 const total=state.data.nodes.length,view=state.graphView||{nodes:[],folderCount:0,noteCount:0},limited=!!(state.query||state.folderPath||graph.selected);
 const all=$('#legend-all');if(all)all.disabled=!current()||!total;
 $('#full-brain').disabled=!current()||!total;
 $('#full-brain').classList.toggle('is-filtered',limited);
 if(!current())return;
 const parts=[];if(view.folderCount)parts.push(view.folderCount+(view.folderCount===1?' folder':' folders'));if(view.noteCount||!view.folderCount)parts.push(view.noteCount+(view.noteCount===1?' note':' notes'));
 $('#note-total').textContent=view.folderCount+view.noteCount;
 if(view.connectionCount)parts.push(view.connectionCount+(view.connectionCount===1?' linked note':' linked notes'));
 $('#graph-summary').textContent=state.query?view.nodes.length+(view.nodes.length===1?' result':' results')+' across Brain':parts.join(' · ')+' · '+(state.folderPath||'Brain root');
 $('#graph-summary').title=state.query?'Search across every folder':state.folderPath?'Contents of '+state.folderPath:'Direct contents of the Brain root';
}
function clearBrainFilters(){
 state.query='';state.group=null;state.folderPath='';state.recent=false;$('#search').value='';
 graph.select(null);graph.keyboardId=null;graph.hover=null;
 renderGraphView();renderLegend();renderTree();graph.dirty=true;
}
let fullBrainPending=false;
function updateBrainToggle(){
 const hidden=document.body.classList.contains('notes-only')||document.body.classList.contains('note-focus');
 const label=hidden?'Show brain':'Hide brain';
 $('#toggle-brain').setAttribute('aria-label',label);$('#toggle-brain').title=label+' (H)';
 $('#toggle-brain').setAttribute('aria-pressed',String(!hidden));$('#toggle-brain span').textContent=label;
}
function setNotebookView(enabled,{focus=true,remember=true}={}){
 setBrainFocus(false);setNoteFocus(false);
 document.body.classList.toggle('notes-only',enabled);
 if(enabled)document.body.classList.remove('library-hidden');
 const mobile=matchMedia('(max-width:900px)').matches;
 document.body.classList.toggle('brain-peek',mobile&&!enabled);
 if(mobile){
  document.body.dataset.mobile=enabled?'notes':'map';
  $$('button[data-mobile]').forEach(b=>b.classList.toggle('active',b.dataset.mobile===document.body.dataset.mobile));
 }
 updateBrainToggle();
 if(remember)try{localStorage.setItem('notryn-workspace',enabled?'notes':'brain');}catch{}
 if(focus){
  const target=enabled?(!$('#document').hidden?$('#doc-close'):$('#file-tree .tree-row')||$('#open-command')):$('#graph');
  target.focus({preventScroll:true});
 }
 graph.dirty=true;
}
function toggleBrainView(){
 if(!current())return toast('Create a Brain or open a folder first.');
 const hidden=document.body.classList.contains('notes-only')||document.body.classList.contains('note-focus');
 setNotebookView(!hidden);
 if(interfaceHints)toast(hidden?'Brain visible. H hides it.':'Notes workspace. H shows the brain.');
}
$('#toggle-brain').onclick=toggleBrainView;
$('#notebook-create').onclick=()=>openCreate('note');
$('#notebook-show-brain').onclick=()=>setNotebookView(false);
async function showFullBrain(){
 if(fullBrainPending||!current()||!state.data.nodes.length)return false;
 fullBrainPending=true;
 try{
  // Nothing changes until the user decides what to do with an unsaved draft.
  if(!await canLeave())return false;
  setNotebookView(false,{focus:false});closeDocumentUnsafe();clearBrainFilters();graph.fit();
  document.body.dataset.mobile='map';
  $$('button[data-mobile]').forEach(b=>b.classList.toggle('active',b.dataset.mobile==='map'));
  $('#graph').focus({preventScroll:true});graphStatus('Brain root · '+graph.nodes.length+' items');
  toast('Brain root restored.');return true;
 }finally{fullBrainPending=false;}
}
$('#full-brain').onclick=showFullBrain;

function resolveNote(link,kind='wiki'){
 if(current()?.scope==='wiki')link=link.replace(/^wiki\//,'');
 const path=NotrynLinks.resolve(link,state.note?.path||'',state.data.linkPaths||state.data.nodes.map(n=>n.path),kind);
 return state.data.nodes.find(n=>n.path===path);
}
function markdown(text,stripTitle=false){
 const root=NotrynRichText.render(text,stripTitle);
 root.querySelectorAll('[data-note-target],a').forEach(link=>{
  const target=link.dataset.noteTarget||link.getAttribute('href');if(!target)return;
  const note=resolveNote(target,link.dataset.noteTarget?'wiki':'markdown');
  if(note&&!/^(?:https?:|mailto:)/i.test(target)){link.setAttribute('role','button');link.tabIndex=0;link.onclick=e=>{e.preventDefault();openNote(note.id);};link.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openNote(note.id);}};}
 });return root;
}
let writingMode='visual';
try{writingMode=localStorage.getItem('notryn-writing-mode')==='source'?'source':'visual';}catch{}
const rich=NotrynRichText.create({mount:$('#rich-editor'),toolbar:$('#format-toolbar'),formatButton:$('#format-note'),linkDialog:$('#link-dialog'),getNotes:()=>state.data.nodes,onChange:value=>{$('#editor').value=value;updateEditor();},onRaw:()=>setWritingMode('source'),onLeave:leaveTextField});
function showEditorSurface(){
 const showing=state.editing&&!state.previewReading&&$('#editor-preview').hidden&&!$('#document').hidden;
 rich.setVisible(showing&&writingMode==='visual');$('#editor').hidden=!showing||writingMode==='visual';
 $('#format-note').hidden=!showing||writingMode!=='visual';
 $('#visual-mode').setAttribute('aria-pressed',String(writingMode==='visual'));$('#source-mode').setAttribute('aria-pressed',String(writingMode==='source'));
}
function focusEditor(end=false){if(writingMode==='visual'&&$('#editor-preview').hidden)rich.focus(end);else{$('#editor').focus();if(end)$('#editor').setSelectionRange($('#editor').value.length,$('#editor').value.length);}}
function setWritingMode(mode){
 if(mode===writingMode)return focusEditor();
 writingMode=mode;if(mode==='visual')rich.load($('#editor').value);
 $('#editor-preview').hidden=true;$('#preview-toggle').textContent='Preview';showEditorSurface();focusEditor();
 try{localStorage.setItem('notryn-writing-mode',mode);}catch{}
}
$('#visual-mode').onclick=()=>setWritingMode('visual');$('#source-mode').onclick=()=>setWritingMode('source');

async function openNote(id){document.body.classList.remove('brain-peek');if(id===state.selected&&!state.newNote){setBrainFocus(false);$('#document').hidden=false;return;}if(!await canLeave())return;const n=state.data.nodes.find(n=>n.id===id);if(!n)return;setBrainFocus(false);resetEditorView();state.query='';state.group=null;state.folderPath=n.folder;$('#search').value='';let folder=n.folder;while(folder){state.closed.delete(folder);folder=folder.split('/').slice(0,-1).join('/');}const serial=++state.noteSerial;state.selected=id;state.dirty=false;state.newNote=false;state.editing=false;state.note=null;renderGraphView();renderLegend();$('#document').hidden=false;$('#document-read').hidden=false;$('#editor-wrap').hidden=true;$('#document-read').replaceChildren(el('p','empty-list','Opening note…'));$('#document-error').hidden=true;graph.select(id);renderTree();try{const result=await api(endpoint('/api/note',{brain:state.brain,path:n.path}));if(serial!==state.noteSerial)return;state.note=result;renderDocument();}catch(e){if(serial===state.noteSerial)$('#document-read').replaceChildren(el('p','empty-list',e.message));}}
function renderDocument(){const note=state.note;if(!note)return;const n=state.data.nodes.find(n=>n.id===state.selected),title=(note.content.match(/^#\s+(.+)/m)||[])[1]||n?.title||note.path.split('/').pop().replace(/\.md$/,'');$('#doc-folder').textContent=note.path;$('#edit-toggle').hidden=!writable();$('#edit-toggle').replaceChildren(icon(state.editing?'note':'edit'),document.createTextNode(state.editing?'Read':'Edit'));$('#save-note').hidden=!state.editing;$('#document-read').hidden=state.editing;$('#editor-wrap').hidden=!state.editing;if(state.editing){$('#editor').value=note.content;rich.load(note.content);showEditorSurface();updateEditor();return;}rich.setVisible(false);const box=$('#document-read');box.replaceChildren(el('span','note-path',note.path),el('h1','',title),markdown(note.content,true));const related=el('div','related'),near=neighbors(state.selected);related.append(el('div','related-label',near.length+' '+(near.length===1?'connection':'connections')));for(const n of near){const b=el('button','',n.title);b.prepend(icon('note'));b.onclick=()=>openNote(n.id);related.append(b);}box.append(related);appendFileLocation(box);box.scrollTop=0;}
function finishEditing(){state.editing=false;resetEditorView();renderDocument();$('#edit-toggle').focus({preventScroll:true});}
async function toggleEdit(){if(!state.note||!writable()||state.saving)return;setBrainFocus(false);if(state.editing)return saveNote({finish:true});state.editing=true;resetEditorView();renderDocument();focusEditor();}
$('#edit-toggle').onclick=()=>{if(state.previewReading){state.previewReading=false;$('#editor-wrap').hidden=false;$('#document-read').hidden=true;$('#edit-toggle').replaceChildren(icon('note'),document.createTextNode('Read'));showEditorSurface();focusEditor();}else toggleEdit();};
function updateSaveState(){
 const button=$('#save-note');
 $('#edit-toggle').hidden=state.editing||!writable();
 button.disabled=state.saving;
 button.textContent=state.saving?'Saving…':state.dirty?'Save':'Done';
 button.title=state.saving?'Saving to disk':state.dirty?'Save changes and return to reading':'Return to reading';
 button.setAttribute('aria-busy',String(state.saving));button.classList.toggle('is-saved',!state.saving&&!state.dirty);
 $('#save-status').textContent=state.saving?'Saving to disk…':state.dirty?'Unsaved changes':'All changes saved';
 $('#save-status').classList.toggle('dirty',state.dirty&&!state.saving);
}
function updateEditor(){state.dirty=state.newNote||$('#editor').value!==state.note?.content;updateSaveState();const words=$('#editor').value.trim().split(/\s+/).filter(Boolean).length;$('#word-count').textContent=words+(words===1?' word':' words');if(!$('#editor-preview').hidden)$('#editor-preview').replaceChildren(markdown($('#editor').value));}
function appendFileLocation(container){
 if(state.remotePreview||!state.note||state.newNote)return;
 const brain=state.brain,path=state.note.path,footer=el('div','note-file-location'),button=el('button','note-folder-link','Show in folder');
 button.prepend(icon('folder'));button.title='Locate this Markdown file on this computer';
 button.onclick=async()=>{
  button.disabled=true;
  try{const result=await api('/api/notes/reveal',{brain,path});toast(result.mode==='folder'?'Opened the note’s folder.':'Requested the file in your file manager.');}
  catch(error){toast(error.message);}finally{button.disabled=false;}
 };
 footer.append(button);container.append(footer);
}
async function showNoteInFolder(){
 if(state.remotePreview)return toast('Open Notryn on the host computer to show local files.');
 if(!state.note||state.newNote)return toast('Open a saved note first.');
 try{const result=await api('/api/notes/reveal',{brain:state.brain,path:state.note.path});toast(result.mode==='folder'?'Opened the note’s folder.':'Requested the file in your file manager.');}
 catch(error){toast(error.message);}
}
function formatNote(action){
 if(!state.editing||writingMode!=='visual')return toast('Open a note in Write mode first.');
 $('#editor-preview').hidden=true;$('#preview-toggle').textContent='Preview';showEditorSurface();rich.format(action);
}
function chooseBrainFolder(){
 if(!current())return toast('Create a Brain or open a folder first.');
 if(document.body.classList.contains('notes-only')||document.body.classList.contains('note-focus')||matchMedia('(max-width:900px)').matches)setNotebookView(false,{focus:false});
 ($('#legend button[aria-pressed="true"]')||$('#legend button'))?.focus({preventScroll:true});
}
$('#legend').addEventListener('keydown',e=>{
 if(!NotrynKeyboard.available(e)||e.shiftKey||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(e.key))return;
 const rows=$$('#legend button:not([disabled])'),i=rows.indexOf(document.activeElement);if(i<0)return;
 e.preventDefault();e.stopPropagation();rows[e.key==='Home'?0:e.key==='End'?rows.length-1:(i+(['ArrowRight','ArrowDown'].includes(e.key)?1:-1)+rows.length)%rows.length]?.focus();
});
function setAllFolders(expanded){
 state.closed=expanded?new Set():new Set(state.data.folders);renderTree();filterNotes();
}
$('#editor').oninput=updateEditor; // Tab and Shift Tab keep their native focus behavior.
function togglePreviewNote(){
 if(!state.editing)return toast('Open a note in the editor first.');
 if(state.previewReading){$('#edit-toggle').click();return;}
 const p=$('#editor-preview'),show=p.hidden;p.hidden=!show;$('#editor').hidden=show;rich.setVisible(false);
 $('#preview-toggle').textContent=show?'Back to writing':'Preview';
 if(show){p.replaceChildren(markdown($('#editor').value));p.focus({preventScroll:true});}
 else{showEditorSurface();focusEditor();}
}
$('#preview-toggle').onclick=togglePreviewNote;
$('#preview-toggle').title='Toggle preview (Ctrl / Cmd + Enter)';
async function saveNote({finish=false}={}){
 if(!state.note||!writable()||!state.editing||state.saving)return;
 if(!state.dirty){if(finish)finishEditing();else toast('All changes are already saved to disk.');return;}
 state.saving=true;updateSaveState();$('#document-error').hidden=true;$('#toast').hidden=true;clearTimeout(toast.timer);
 const value=$('#editor').value;
 try{
  const result=await api('/api/notes',{brain:state.brain,path:state.note.path,content:value,revision:state.newNote?null:state.note.revision});
  state.note={...state.note,content:value,revision:result.revision};state.newNote=false;state.selected=state.note.path.slice(0,-3);
  updateEditor();await loadGraph();
  toast(state.dirty?'Saved to disk. Newer edits are still unsaved.':'Saved to disk successfully.');
  if(finish&&!state.dirty)finishEditing();
 }catch(e){$('#document-error').textContent=e.message;$('#document-error').hidden=false;}
 finally{state.saving=false;updateEditor();}
}
$('#save-note').onclick=()=>saveNote({finish:true});$('#doc-close').onclick=closeDocument;

function expandFolderPath(path){while(path){state.closed.delete(path);path=path.split('/').slice(0,-1).join('/');}}
let createKind='note';async function openCreate(kind,title='',destination=state.folderPath||''){if(!current())return openBrainForm('create');if(!writable())return toast('This Brain is read-only. Create or choose a writable Brain.');if(!await canLeave())return;setBrainFocus(false);document.body.classList.remove('brain-peek');createKind=kind;$('#create-title').textContent=kind==='folder'?'New folder':'New note';$('#create-name').value=title;$('#create-name').setCustomValidity('');$('#create-name').placeholder=kind==='folder'?'Projects':'The beginning of an idea';$('#create-submit').textContent=kind==='folder'?'Create folder':'Start writing';$('#create-folder').replaceChildren();const option=el('option','',current().name+' (root)');option.value='';$('#create-folder').append(option);for(const f of state.data.folders){const o=el('option','',f);o.value=f;$('#create-folder').append(o);}$('#create-folder').value=destination;$('#create-dialog .form-error').hidden=true;showDialog('#create-dialog');$('#create-name').focus();}
$('#create-form').onsubmit=async e=>{e.preventDefault();const name=$('#create-name').value.trim(),folder=$('#create-folder').value,error=$('#create-dialog .form-error');if(!name||/[\\/]/.test(name)||name.startsWith('.')){error.textContent='Use a name without slashes or a leading dot.';error.hidden=false;return;}const path=(folder?folder+'/':'')+name+(createKind==='note'&&!/\.md$/i.test(name)?'.md':'');$('#create-submit').disabled=true;try{if(createKind==='folder'){await api('/api/folders',{brain:state.brain,path});expandFolderPath(folder);await loadGraph();navigateBrainFolder(folder);$('#create-dialog').close();const row=$$('#file-tree .tree-row').find(row=>row.dataset.key==='folder:'+path);row?.focus({preventScroll:true});row?.scrollIntoView({block:'nearest'});toast('Folder created.');}else{if(state.data.nodes.some(n=>n.path===path))throw Error('A note with this name already exists.');closeDocumentUnsafe();state.newNote=true;state.editing=true;expandFolderPath(folder);state.note={path,content:'# '+name.replace(/\.md$/i,'')+'\n\n',revision:null};navigateBrainFolder(folder);$('#document').hidden=false;$('#create-dialog').close();resetEditorView();renderDocument();focusEditor(true);}}catch(e){error.textContent=e.message;error.hidden=false;}finally{$('#create-submit').disabled=false;}};
function resetEditorView(){state.previewReading=false;$('#editor-preview').hidden=true;$('#preview-toggle').textContent='Preview';showEditorSurface();}
$('#new-note').onclick=()=>openCreate('note');$('#empty-create').onclick=()=>openCreate('note');$('#library-new-note').onclick=()=>openCreate('note');$('#new-folder').onclick=()=>openCreate('folder');
let brainAction='create';
function brainDestination(parent,name){
 parent=parent.trim().replace(/[\\/]+$/,'');name=name.trim();if(!parent||!name)return '';
 return parent+(parent.includes('\\')&&!parent.includes('/')?'\\':'/')+name;
}
function updateBrainForm(){
 const creating=brainAction==='create',name=$('#brain-form-name').value.trim(),path=$('#brain-form-path').value.trim();
 const destination=brainDestination(path,name),summary=$('#brain-form-destination');
 summary.hidden=!creating||!destination;summary.querySelector('code').textContent=destination;summary.querySelector('code').title=destination;
 $('#brain-submit').disabled=!name||!path;
}
async function openBrainForm(action){if(state.remotePreview)return toast('This preview provides read-only access to connected Brains.');if(!await canLeave())return;$('#brains-dialog').close();brainAction=action;const creating=action==='create';$('#brain-form-title').textContent=creating?'Create a Brain':'Open a folder';$('#brain-form-path-label').textContent=creating?'Create inside':'Folder on this computer';$('#brain-form-path').placeholder=creating?'Choose where to save this Brain…':'Choose the folder to open…';$('#browse-folders').setAttribute('aria-label',creating?'Choose a location':'Choose a folder');$('#browse-folders').title=creating?'Choose a location':'Choose a folder';$('#connect-access').hidden=creating;$('#brain-submit').textContent=creating?'Create Brain':'Open folder';$('#brain-form-help').textContent=creating?'Choose where this folder will live. Your notes stay there.':'Connect an existing folder. Your files stay where they are.';$('#brain-form-name').value='';$('#brain-form-path').value='';$('#brain-form-name').setCustomValidity('');$('#brain-form-path').setCustomValidity('');$('#brain-form-access').value='read';$('#brain-form-dialog .form-error').hidden=true;updateBrainForm();showDialog('#brain-form-dialog');$('#brain-form-name').focus();}
$('#brain-form-name').addEventListener('input',updateBrainForm);$('#brain-form-path').addEventListener('input',updateBrainForm);
$('#brain-form').onsubmit=async e=>{e.preventDefault();$('#brain-submit').disabled=true;try{const {brain,graph:graphData}=await api('/api/brains',{action:brainAction,name:$('#brain-form-name').value,path:$('#brain-form-path').value,writable:$('#brain-form-access').value==='write'});$('#brain-form-dialog').close();await switchBrain(brain.id,{brain,graphData});toast(brainAction==='create'?'Brain created.':'Folder connected.');}catch(e){const p=$('#brain-form-dialog .form-error');p.textContent=e.message;p.hidden=false;}finally{$('#brain-submit').disabled=false;}};
let brainAccessId=null;
function updateBrainAccessCopy(){const writable=$('input[name="brain-access"]:checked')?.value==='write';$('#brain-access-submit').textContent=writable?'Allow writing':'Keep read-only';$('#brain-access-help').textContent=writable?'Notryn will be able to create, edit, move and remove Markdown files in this folder.':'Notryn will only read this folder. Files cannot be changed from the app.';}
async function openBrainAccess(id=state.brain){if(state.remotePreview)return toast('Brain access can only be changed in the local app.');const brain=state.brains.find(b=>b.id===id);if(!brain)return toast('Choose a Brain first.');if(!await canLeave())return;$('#brains-dialog').close();brainAccessId=id;$('#brain-access-name').textContent=brain.name;$('#brain-access-path').textContent=brain.root;const value=brain.readOnly?'read':'write';const option=$('input[name="brain-access"][value="'+value+'"]');option.checked=true;$('#brain-access-error').hidden=true;updateBrainAccessCopy();showDialog('#brain-access-dialog');option.focus();}
function closeBrainAccess(){brainAccessId=null;$('#brain-access-dialog').close();brainPicker();}
$$('input[name="brain-access"]').forEach(input=>input.onchange=updateBrainAccessCopy);
$('#brain-access-close').onclick=closeBrainAccess;$('#brain-access-cancel').onclick=closeBrainAccess;$('#brain-access-dialog').oncancel=e=>{e.preventDefault();closeBrainAccess();};
$('#brain-access-form').onsubmit=async e=>{e.preventDefault();const writable=$('input[name="brain-access"]:checked')?.value==='write',button=$('#brain-access-submit'),error=$('#brain-access-error'),id=brainAccessId;button.disabled=true;error.hidden=true;try{const {brain}=await api('/api/brains',{action:'access',brain:id,writable});await loadBrains();if(id===state.brain){if(brain.readOnly&&state.editing){state.editing=false;state.dirty=false;renderDocument();}await loadGraph();}brainAccessId=null;$('#brain-access-dialog').close();brainPicker();toast(brain.readOnly?'Brain is now read-only.':'Read and write access enabled.');}catch(e){error.textContent=e.message;error.hidden=false;}finally{button.disabled=false;}};
function brainPicker(){const list=$('#brain-list');list.replaceChildren();$('#brain-actions').hidden=false;['#add-new-brain','#add-existing-brain'].forEach(id=>$(id).disabled=state.remotePreview);$('#brains-preview-note').hidden=!state.remotePreview;$('#brain-count').textContent=state.brains.length+(state.brains.length===1?' Brain':' Brains');for(const b of state.brains){const button=el('button','brain-card'+(b.id===state.brain?' active':'')),info=el('div');info.append(el('strong','',b.name),el('small','',!b.available?'Folder unavailable':b.readOnly?'Read-only':'Read and write'));button.append(icon('brain'),info,icon(b.id===state.brain?'chevron':'folder'));button.onclick=async()=>{$('#brains-dialog').close();await switchBrain(b.id);};const row=el('div','brain-entry');row.append(button);if(!state.remotePreview){const manage=el('button','secondary brain-manage');manage.append(icon(b.readOnly?'lock':'edit'),document.createTextNode('Access'));manage.setAttribute('aria-label','Manage access for '+b.name);manage.title='Manage access';manage.onclick=()=>openBrainAccess(b.id);const remove=el('button','icon-button brain-remove');remove.append(icon('trash'));remove.setAttribute('aria-label','Remove '+b.name+' from Notryn');remove.title='Remove from Notryn';remove.onclick=()=>window.NotrynRemoval.openBrain(b.id);row.append(manage,remove);}list.append(row);}if(!state.brains.length)list.append(el('p','form-help','No Brains connected yet. Create one or open a folder to begin.'));showDialog('#brains-dialog');(state.remotePreview?($('#brain-list .brain-card.active')||$('#brain-list .brain-card')):$('#add-new-brain'))?.focus();}
$('#brain-picker').onclick=brainPicker;$('#home-button').onclick=brainPicker;$('#add-new-brain').onclick=()=>openBrainForm('create');$('#add-existing-brain').onclick=()=>openBrainForm('connect');$('#welcome-create').onclick=()=>openBrainForm('create');$('#welcome-open').onclick=()=>openBrainForm('connect');
$('#brains-dialog').addEventListener('keydown',e=>{if(state.remotePreview||!singleKeys||!NotrynKeyboard.available(e))return;const key=e.key.toLowerCase(),create=key==='b'&&e.shiftKey,connect=key==='o'&&!e.shiftKey;if(!create&&!connect)return;e.preventDefault();e.stopPropagation();openBrainForm(create?'create':'connect');});
$('#add-new-brain kbd').textContent='Shift B';

function toggleLibrary(){if(document.body.classList.contains('brain-focus')){setBrainFocus(false);setNoteFocus(false);document.body.classList.remove('library-hidden');return;}if(document.body.classList.contains('note-focus')){setNoteFocus(false);document.body.classList.remove('library-hidden');return;}document.body.classList.toggle('library-hidden');}$('#sidebar-close').onclick=toggleLibrary;$('#sidebar-open').onclick=toggleLibrary;
$('#fit').onclick=()=>graph.fit();$('#zoom-in').onclick=()=>graph.zoomBy(1.12);$('#zoom-out').onclick=()=>graph.zoomBy(1/1.12);function updateMotionButton(){$('#motion').replaceChildren(icon(graph.moving?'pause':'play'));$('#motion').setAttribute('aria-label',graph.moving?'Pause motion':'Resume motion');$('#motion').title=(graph.moving?'Pause motion':'Resume motion')+' (Space with brain focused)';}function motion(){graph.moving=!graph.moving;graph.dirty=true;try{localStorage.setItem('notryn-motion',graph.moving?'running':'paused');}catch{}updateMotionButton();}$('#motion').onclick=motion;document.addEventListener('notryn-motionchange',updateMotionButton);updateMotionButton();
async function mobileView(view,{focusInput=true}={}){
 if(!$('#document').hidden){if(!await canLeave())return false;closeDocumentUnsafe();}
 if(view==='map'||view==='notes')setNotebookView(view==='notes',{focus:false});
 document.body.classList.remove('brain-peek');
 document.body.dataset.mobile=view;
 $$('button[data-mobile]').forEach(b=>b.classList.toggle('active',b.dataset.mobile===view));
 // A tap changes panes without opening the keyboard or triggering iOS input zoom.
 // Keyboard navigation and explicit search commands still reach the input directly.
 if(focusInput&&view==='notes')$('#search').focus({preventScroll:true});return true;
}
$$('button[data-mobile]').forEach(b=>b.onclick=e=>mobileView(b.dataset.mobile,{focusInput:e.detail===0}));
$('#brain-picker').title='Switch Brain (B)';$('#new-folder').title='New folder (Shift N)';$('#add-new-brain').title='Create Brain (Shift B)';$('#add-existing-brain').title='Open folder (O)';

// Keep the editor node, content, selection and scroll position when swapping panes.
let noteSide='left';
try{noteSide=localStorage.getItem('notryn-note-side')==='right'?'right':'left';}catch{}
function applyNoteSide(){
 const doc=$('#document'),universe=$('.universe'),active=document.activeElement;
 const scrolls=[$('#editor'),$('#rich-editor'),$('#document-read'),$('#editor-preview')].map(e=>[e,e.scrollTop]);
 const visualSelection=$('#rich-editor').contains(active)?rich.bookmark():null;
 const selection=active===$('#editor')?[active.selectionStart,active.selectionEnd,active.selectionDirection]:null;
 if(noteSide==='left')doc.after(universe);else doc.before(universe);
 document.body.dataset.noteSide=noteSide;
 $('#swap-layout').title='Swap note and brain (Shift L)';
 $('#swap-layout').setAttribute('aria-label','Swap note and brain. Note on the '+(noteSide==='left'?'left':'right'));
 if(active&&active!==document.body){active.focus({preventScroll:true});if(selection)active.setSelectionRange(...selection);if(visualSelection)rich.restore(visualSelection);}
 scrolls.forEach(([e,top])=>e.scrollTop=top);
}
function swapLayout(){
 if(matchMedia('(max-width:900px)').matches)return toast('On this screen, the note uses the full width.');
 noteSide=noteSide==='left'?'right':'left';applyNoteSide();
 try{localStorage.setItem('notryn-note-side',noteSide);}catch{}
 toast('Note on the '+(noteSide==='left'?'left':'right')+'. Preference saved.');
}
function setNoteFocus(value){
 if(value)setBrainFocus(false);
 document.body.classList.toggle('note-focus',value);
 updateBrainToggle();
 $('#focus-note').setAttribute('aria-pressed',String(value));
 const label=value?'Exit note focus':'Focus note';
 $('#focus-note').setAttribute('aria-label',label);$('#focus-note').title=label+' (F)';
}
function toggleNoteFocus(){
 if($('#document').hidden)return toast('Open a note first.');
 if(matchMedia('(max-width:900px)').matches)return toast('On this screen, the note already uses the full width.');
 setNoteFocus(!document.body.classList.contains('note-focus'));
}
function filterNotes(){if(matchMedia('(max-width:900px)').matches)return mobileView('notes');setBrainFocus(false);setNoteFocus(false);document.body.classList.remove('library-hidden');$('#search').focus();}
function closePanel(){if(document.body.classList.contains('brain-focus'))setBrainFocus(false);else if(document.body.classList.contains('note-focus'))setNoteFocus(false);else if(!$('#document').hidden)closeDocument();}
$('#swap-layout').onclick=swapLayout;$('#focus-note').onclick=toggleNoteFocus;
applyNoteSide();setNoteFocus(false);

let brainFocusReturn=null;
function setBrainFocus(value){
 const active=document.body.classList.contains('brain-focus');if(value===active)return;
 if(value){
  brainFocusReturn={element:document.activeElement,noteFocus:document.body.classList.contains('note-focus')};
  setNoteFocus(false);document.body.classList.add('brain-focus');
 }else{
  const previous=brainFocusReturn;brainFocusReturn=null;document.body.classList.remove('brain-focus');
  if(previous?.noteFocus)setNoteFocus(true);
  if(previous?.element?.isConnected&&previous.element.getClientRects().length){if($('#rich-editor').contains(previous.element))rich.focus();else previous.element.focus({preventScroll:true});}
 }
 graph.dirty=true;
}
async function toggleBrainFocus(){
 if(matchMedia('(max-width:900px)').matches)return focusBrain();
 if(document.body.classList.contains('notes-only'))setNotebookView(false,{focus:false});
 const value=!document.body.classList.contains('brain-focus');setBrainFocus(value);
 if(value){$('#graph').focus({preventScroll:true});graphStatus('Immersive view'+(interfaceHints?' · Esc to return':''));}
}
async function focusBrain(){
 if(document.body.classList.contains('notes-only')||matchMedia('(max-width:900px)').matches)setNotebookView(false,{focus:false});
 setNoteFocus(false);
 $('#graph').focus({preventScroll:true});graph.dirty=true;return true;
}
function graphStatus(message){
 $('#graph-status').textContent=message;$('#graph-status').hidden=document.activeElement!==$('#graph');
}
function currentGraphStatus(){
 const nodes=[...graph.nodes].sort((a,b)=>a.title.localeCompare(b.title)),i=nodes.findIndex(n=>n.id===graph.keyboardId);
 return i>=0?nodes[i].title+' · '+(i+1)+'/'+nodes.length+(interfaceHints?' · Enter to open':''):'Zoom '+Math.round(graph.zoom*100)+'%'+(interfaceHints?(singleKeys?' · J / K to select an item':' · Tab to reach the controls'):'');
}
$('#graph').onfocus=()=>{graph.dirty=true;graphStatus(currentGraphStatus());$('#graph-hint').textContent=singleKeys?'Arrows: rotate · + / −: zoom · 0: center · Space: pause':'Arrows: rotate · Tab: brain controls';};
$('#graph').onblur=()=>{$('#graph-status').hidden=true;restGraphHint();graph.dirty=true;};
const graphViewport=matchMedia('(max-width:900px)');
function restGraphHint(){$('#graph-hint').textContent=graphViewport.matches?'Drag to rotate · Pinch to zoom':singleKeys?'H hide brain · Shift H full Brain · ? shortcuts':'Tab to explore · Use controls to navigate';}
graphViewport.addEventListener('change',restGraphHint);restGraphHint();
async function controlBrain(action,key){
 if(!await focusBrain())return;
 if(action==='zoom-in')graph.zoomBy(1.12);
 if(action==='zoom-out')graph.zoomBy(1/1.12);
 if(action==='fit')graph.fit();
 if(action==='rotate'){
  graph.rotateBy(key==='ArrowLeft'?-.07:key==='ArrowRight'?.07:0,key==='ArrowUp'?-.06:key==='ArrowDown'?.06:0);
 }
 if(action==='motion'){motion();graphStatus(graph.moving?'Motion enabled':'Motion paused');}
 else {const view=graph.cameraTarget||graph;graphStatus(action==='rotate'?'Rotation '+Math.round(view.rotation*180/Math.PI)+'° · Tilt '+Math.round(view.tilt*180/Math.PI)+'°':'Zoom '+Math.round(view.zoom*100)+'%');}
 graph.dirty=true;
}
async function stepGraphNote(direction){
 if(!await focusBrain())return;
 const nodes=[...graph.nodes].sort((a,b)=>a.title.localeCompare(b.title));if(!nodes.length)return graphStatus('This folder is empty.');
 const i=nodes.findIndex(n=>n.id===graph.keyboardId),next=i<0?(direction>0?0:nodes.length-1):(i+direction+nodes.length)%nodes.length;
 graph.keyboardId=nodes[next].id;graph.dirty=true;graphStatus(currentGraphStatus());
}
async function openGraphNote(){
 if(!graph.keyboardId){await stepGraphNote(1);if(!graph.keyboardId)return;}
 const id=graph.keyboardId;await openGraphItem(id);
 if(!id.startsWith('@folder:')&&state.selected===id&&state.note)$('#document-read').focus({preventScroll:true});
}
function cycleWorkspace(direction=1){
 const panels=$$('.library,#document,.universe').filter(p=>p.getClientRects().length);
 const index=panels.findIndex(p=>p.contains(document.activeElement)),panel=panels[(index+direction+panels.length)%panels.length];if(!panel)return;
 const target=panel.id==='library'?($('#file-tree .tree-row[tabindex="0"]')||$('#search')):panel.id==='document'?(!$('#editor-wrap').hidden?(!$('#rich-editor').hidden?rich.dom:!$('#editor').hidden?$('#editor'):$('#editor-preview')):$('#document-read')):$('#graph');
 target.focus({preventScroll:true});
}
// Arrow navigation supplements normal Tab/Shift Tab in dialog action lists.
for(const selector of ['#brain-list','#shortcut-catalog'])$(selector).addEventListener('keydown',e=>{
 if(!NotrynKeyboard.available(e)||e.shiftKey||!['ArrowDown','ArrowUp','Home','End'].includes(e.key))return;
 const rows=[...$(selector).querySelectorAll('button')],i=rows.indexOf(document.activeElement);if(!rows.length)return;e.preventDefault();
 if(selector==='#shortcut-catalog'&&i===0&&e.key==='ArrowUp'){ $('#shortcut-search').focus({preventScroll:true});return; }
 const next=e.key==='Home'?0:e.key==='End'?rows.length-1:Math.max(0,Math.min(rows.length-1,i+(e.key==='ArrowDown'?1:-1)));rows[next].focus();
});

// One catalog powers the palette, the reference sheet and keyboard bindings.
const actionItems=()=>[
 {title:'Show / hide brain',group:'Layout',key:'H',plain:'h',icon:'brain',run:toggleBrainView},
 {title:'Show full Brain',group:'Navigation',key:'Shift H',plain:'h',plainShift:true,icon:'brain',run:showFullBrain},
 {title:'Choose theme',group:'Appearance',key:'T',plain:'t',icon:'theme',run:()=>window.openThemes()},
 {title:interfaceHints?'Hide interface hints':'Show interface hints',group:'Appearance',key:'Shift T',plain:'t',plainShift:true,keywords:'clean minimal advanced tips help hints interface ajudas dicas limpo',icon:'keyboard',run:()=>setInterfaceHints(!interfaceHints)},
 {title:'Configure keyboard shortcuts',group:'Appearance',keywords:'enable disable single key preferences teclado ativar desativar',icon:'keyboard',run:()=>{openShortcuts();$('#single-key-toggle').focus();}},
 {title:'Notes and commands',group:'Navigation',key:'P',plain:'p',icon:'search',run:openCommand},
 {title:'Commands and shortcuts',group:'Navigation',key:'?',plain:'?',icon:'keyboard',run:openShortcuts},
 {title:'Filter notes',group:'Navigation',key:'Q',plain:'q',icon:'search',run:filterNotes},
 {title:'Toggle library',group:'Navigation',key:'L',plain:'l',icon:'sidebar',run:()=>matchMedia('(max-width:900px)').matches?mobileView('notes'):toggleLibrary()},
 {title:'Recent notes',group:'Navigation',key:'Shift R',plain:'r',plainShift:true,icon:'note',run:()=>{$('#recent-notes').click();filterNotes();}},
 {title:'Show Brain root',group:'Navigation',key:'Shift Q',plain:'q',plainShift:true,keywords:'all clear filters root full brain todas raiz',icon:'brain',run:()=>{clearBrainFilters();graph.fit();}},
 {title:'Choose a folder',group:'Navigation',key:'C',plain:'c',keywords:'folder projects knowledge system notes pasta projetos',icon:'folder',run:chooseBrainFolder},
 {title:'Back one folder',group:'Navigation',key:'U',plain:'u',keywords:'parent previous up back folder subir voltar atras anterior pasta',icon:'folder',run:upBrainFolder},
 {title:'Expand all folders',group:'Navigation',keywords:'expand library expandir pastas',icon:'folder',run:()=>setAllFolders(true)},
 {title:'Collapse all folders',group:'Navigation',keywords:'collapse library recolher pastas',icon:'folder',run:()=>setAllFolders(false)},
 {title:'Switch Brain',group:'Navigation',key:'B',plain:'b',icon:'brain',run:brainPicker},
 {title:'Refresh notes',group:'Navigation',key:'R',plain:'r',icon:'refresh',run:loadGraph},
 {title:'Close panel / leave focus',group:'Navigation',key:'Esc',plain:'Escape',icon:'close',run:closePanel},
 {title:'Switch pane',group:'Layout',key:'W / Shift W',plain:'w',anyShift:true,icon:'sidebar',run:e=>cycleWorkspace(e?.shiftKey?-1:1)},
 {title:'Swap note and brain',group:'Layout',key:'Shift L',plain:'l',plainShift:true,icon:'swap',run:swapLayout},
 {title:'Focus note / exit focus',group:'Layout',key:'F',plain:'f',icon:'expand',run:toggleNoteFocus},
 {title:'New note',group:'Writing',key:'N',plain:'n',icon:'plus',run:()=>openCreate('note')},
 {title:'New folder',group:'Writing',key:'Shift N',plain:'n',plainShift:true,icon:'folder',run:()=>openCreate('folder')},
 {title:'Edit or finish editing',group:'Writing',key:'E',plain:'e',icon:'edit',run:toggleEdit},
 {title:'Switch Write / Markdown',group:'Writing',key:'Shift E',plain:'e',plainShift:true,keywords:'source visual editor codigo escrita',icon:'edit',run:()=>{if(!state.editing)return toast('Edit a note first.');setWritingMode(writingMode==='visual'?'source':'visual');}},
 {title:'Format text',group:'Writing',key:'Shift F',plain:'f',plainShift:true,icon:'edit',run:()=>{if(!state.editing||writingMode!=='visual')return toast('Open a note in Write mode first.');$('#editor-preview').hidden=true;$('#preview-toggle').textContent='Preview';showEditorSurface();rich.showTools();}},
 ...[['Bold','strong','Ctrl / Cmd + B'],['Italic','em','Ctrl / Cmd + I'],['Strikethrough','strike','Ctrl / Cmd + Shift X'],['Insert or edit link','link','Ctrl / Cmd + K'],['Undo','undo','Ctrl / Cmd + Z'],['Redo','redo','Ctrl / Cmd + Shift Z'],['Paragraph','text'],['Heading 1','h1'],['Heading 2','h2'],['Heading 3','h3'],['Heading 4','h4'],['Heading 5','h5'],['Heading 6','h6'],['Bullet list','bullet'],['Numbered list','ordered'],['Blockquote','quote'],['Code block','code'],['Inline code','inline-code']].map(([title,format,key])=>({title,format,key,group:'Formatting',context:'visual',keywords:'text format formatting '+format,icon:'edit',run:()=>formatNote(format)})),
 {title:'Remove note or folder from Notryn',group:'Writing',key:'D',plain:'d',icon:'trash',run:()=>window.NotrynRemoval.openItem()},
 {title:'Removed items',group:'Navigation',key:'Shift D',plain:'d',plainShift:true,keywords:'restore forget remove from list recuperar lista',icon:'trash',run:()=>window.NotrynRemoval.openRemoved()},
 {title:'Remove this Brain from Notryn',group:'Brains',icon:'trash',run:()=>window.NotrynRemoval.openBrain()},
 {title:'Manage Brain access',group:'Brains',icon:'lock',run:()=>openBrainAccess()},
 {title:'Rename note or folder',group:'Writing',key:'F2',plain:'F2',keywords:'rename title filename folder name mudar nome renomear ficheiro pasta',icon:'edit',run:()=>window.NotrynFiles.openRename()},
 {title:'Move note or folder',group:'Writing',key:'M',plain:'m',icon:'swap',run:()=>window.NotrynFiles.openMove()},
 {title:'Note or folder actions',group:'Writing',key:'Shift M',plain:'m',plainShift:true,keywords:'context menu item options',icon:'folder',run:()=>window.NotrynFiles.openMenu()},
 {title:'Show note in folder',group:'Writing',key:'Shift O',plain:'o',plainShift:true,keywords:'reveal finder explorer file location localizar ficheiro pasta',icon:'folder',run:showNoteInFolder},
 {title:'Save note',group:'Writing',key:'Ctrl / Cmd + S',plain:'s',editorKey:'s',icon:'save',run:saveNote},
 {title:'Save and finish editing',group:'Writing',key:'Shift S',plain:'s',plainShift:true,keywords:'done read guardar terminar leitura',icon:'save',run:()=>saveNote({finish:true})},
 {title:'Preview note',group:'Writing',key:'Ctrl / Cmd + Enter',plain:'v',editorKey:'enter',icon:'note',run:togglePreviewNote},
 {title:'Create a Brain',group:'Brains',key:'Shift B',plain:'b',plainShift:true,icon:'plus',run:()=>openBrainForm('create')},
 {title:'Open a folder',group:'Brains',key:'O',plain:'o',icon:'folder',run:()=>openBrainForm('connect')},
 {title:'Focus brain',group:'Brain view',key:'G',plain:'g',icon:'brain',run:focusBrain},
 {title:'Immersive brain / return',group:'Brain view',key:'Shift G',plain:'g',plainShift:true,icon:'expand',run:toggleBrainFocus},
 {title:'Rotate brain',group:'Brain view',key:'↑ ↓ ← →',plain:['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'],context:'graph',repeat:true,icon:'refresh',run:e=>controlBrain('rotate',e?.key||'ArrowRight')},
 {title:'Center brain',group:'Brain view',key:'0',plain:'0',context:'graph',icon:'expand',run:()=>controlBrain('fit')},
 {title:'Zoom in',group:'Brain view',key:'+ / =',plain:['+','='],context:'graph',repeat:true,icon:'plus',run:()=>controlBrain('zoom-in')},
 {title:'Zoom out',group:'Brain view',key:'−',plain:'-',context:'graph',repeat:true,icon:'search',run:()=>controlBrain('zoom-out')},
 {title:'Pause / resume motion',group:'Brain view',key:'Space',plain:' ',context:'graph',icon:'pause',run:()=>controlBrain('motion')},
 {title:'Next note in brain',group:'Brain view',key:'J / Page Down',plain:['j','PageDown'],context:'graph',repeat:true,icon:'note',run:()=>stepGraphNote(1)},
 {title:'Previous note in brain',group:'Brain view',key:'K / Page Up',plain:['k','PageUp'],context:'graph',repeat:true,icon:'note',run:()=>stepGraphNote(-1)},
 {title:'Open highlighted item',group:'Brain view',key:'Enter',plain:'Enter',context:'graph',icon:'note',run:openGraphNote}
];
// Button hints use the same shortcuts as the palette and keyboard handler.
const controlActions={
 '#toggle-brain,#notebook-show-brain':'Show / hide brain',
 '#full-brain':'Show full Brain','#open-themes':'Choose theme',
 '#open-command':'Notes and commands','#open-shortcuts':'Commands and shortcuts',
 '#search':'Filter notes','#sidebar-open,#sidebar-close':'Toggle library',
 '#recent-notes':'Recent notes','#legend-all':'Show Brain root',
 '#library-back,.legend-back':'Back one folder','#brain-picker,#home-button':'Switch Brain',
 '#refresh':'Refresh notes','#swap-layout':'Swap note and brain',
 '#focus-note':'Focus note / exit focus',
 '#new-note,#library-new-note,#empty-create,#notebook-create,#item-new-note':'New note',
 '#new-folder,#item-new-folder':'New folder','#edit-toggle':'Edit or finish editing',
 '#format-note':'Format text','#visual-mode,#source-mode':'Switch Write / Markdown',
 '#item-rename':'Rename note or folder',
 '#item-move':'Move note or folder','#item-remove':'Remove note or folder from Notryn',
 '#open-removed':'Removed items','.file-options':'Note or folder actions',
 '.note-folder-link':'Show note in folder','#save-note':'Save and finish editing',
 '#preview-toggle':'Preview note','#add-new-brain,#welcome-create':'Create a Brain',
 '#add-existing-brain,#welcome-open':'Open a folder','#fit':'Center brain',
 '#zoom-in':'Zoom in','#zoom-out':'Zoom out','#motion':'Pause / resume motion'
};
function updateControlHint(button,actions=actionItems()){
 const title=Object.entries(controlActions).find(([selector])=>button.matches(selector))?.[1];
 const action=button.dataset.format?actions.find(a=>a.format===button.dataset.format):actions.find(a=>a.title===title);
 if(!action)return;
 let label=button.getAttribute('aria-label')||action.title;
 if(['library-new-note','new-folder','new-note'].includes(button.id))label=writable()?action.title+' in '+(NotrynHierarchy.name(state.folderPath)||current()?.name):'This Brain is read-only';
 if(button.id==='library-back')label=state.folderPath?'Back to '+(NotrynHierarchy.name(NotrynHierarchy.parent(state.folderPath))||current()?.name):'You are at the Brain root';
 if(button.id==='save-note')label=state.saving?'Saving to disk':state.dirty?'Save changes and return to reading':'Return to reading';
 if(['visual-mode','source-mode'].includes(button.id))label=button.textContent;
 const keys=Array.isArray(action.plain)?action.plain:[action.plain];
 const enabled=(singleKeys||action.editorKey||!action.plain||keys.every(key=>key.length>1))&&!(action.title==='Switch Write / Markdown'&&button.getAttribute('aria-pressed')==='true');
 if(['library-new-note','new-folder','library-back'].includes(button.id)){
  if(enabled&&!button.disabled)button.setAttribute('aria-keyshortcuts',(action.plainShift?'Shift+':'')+action.plain.toUpperCase());
  else button.removeAttribute('aria-keyshortcuts');
 }
 button.title=label+(interfaceHints&&enabled&&action.key&&!button.disabled?' ('+action.key+(action.context==='graph'?' with Brain focused':'')+')':'');
}
function refreshControlHints(){const actions=actionItems();$$(Object.keys(controlActions).join(',')+',[data-format]').forEach(button=>updateControlHint(button,actions));}
const commandSearchAliases={
 'Choose theme':'theme themes tema temas appearance colors colours cor cores glass matrix daylight omarchy',
 'Show / hide brain':'hide show brain notes workspace esconder mostrar cerebro notas',
 'Show full Brain':'reset restore all notes clear filters categories finance full brain completo repor tudo todas notas limpar filtros categorias',
 'Create a Brain':'new brain criar novo cerebro',
 'Open a folder':'connect directory vault abrir ligar pasta',
 'New note':'create criar nova nota',
 'New folder':'create directory criar nova pasta',
 'Manage Brain access':'permissions read only write edit permissoes leitura escrita acesso',
 'Swap note and brain':'left right sides trocar esquerda direita',
 'Remove note or folder from Notryn':'delete remove apagar remover nota pasta',
 'Removed items':'trash restore undo deleted lixo recuperar removidos',
 'Save note':'save guardar gravar',
 'Rename note or folder':'rename filename folder name mudar nome renomear ficheiro pasta',
 'Move note or folder':'move organize mover organizar arrastar',
 'Zoom in':'zoom enlarge bigger aumentar ampliar',
 'Zoom out':'zoom smaller diminuir reduzir',
 'Rotate brain':'rotate arrows rodar girar setas',
 'Commands and shortcuts':'help keys shortcuts commands ajuda atalhos comandos'
};
function matchesCommand(action,query){
 const q=clean(query).replace(/([a-z])\s*\+\s*(?=[a-z])/g,'$1 ').trim();
 const keys=(Array.isArray(action.plain)?action.plain:[action.plain]).filter(Boolean).map(clean);
 if(q.length===1)return !action.plainShift&&keys.includes(q==='−'?'-':q);
 const shifted=q.match(/^shift\s+([a-z0-9])$/);
 if(shifted)return keys.includes(shifted[1])&&!!(action.plainShift||action.anyShift);
 const haystack=clean([action.title,action.group,action.key||'',action.key?.replace(/↑/g,'arrowup').replace(/↓/g,'arrowdown').replace(/←/g,'arrowleft').replace(/→/g,'arrowright')||'',action.key==='−'?'-':'',action.context==='graph'?'while the brain is focused':'',action.key?'':'no shortcut',action.keywords||'',commandSearchAliases[action.title]||''].join(' '));
 return !q||q.split(/\s+/).every(word=>haystack.includes(word));
}
function renderShortcuts(){
 const catalog=$('#shortcut-catalog'),query=$('#shortcut-search').value.trim();catalog.replaceChildren();
 const actions=actionItems().filter(a=>matchesCommand(a,query));
 $('#shortcut-results-status').textContent=actions.length+' '+(actions.length===1?'command':'commands')+(singleKeys?'':' · Single-key shortcuts are off; choose a command to run it.');
 for(const group of ['Appearance','Layout','Navigation','Writing','Formatting','Brains','Brain view']){
  const grouped=actions.filter(a=>a.group===group);if(!grouped.length)continue;
  const section=el('section','shortcut-section');section.append(el('h3','',group));
  if(!query&&group==='Navigation')section.append(el('p','shortcut-context','Tab moves between controls; Shift Tab goes back. Arrows browse lists; Enter chooses; Esc returns. P → search an action → Enter works for every command. While writing, press Esc first.'));
  if(!query&&group==='Formatting')section.append(el('p','shortcut-context','Select text in Write mode first. Copy, cut, paste and select all use the usual Ctrl / Cmd + C, X, V and A. Shift Enter inserts a line break.'));
  for(const action of grouped){
   const button=el('button','shortcut-command'),label=el('span','shortcut-command-label'),name=el('span','',action.title);label.append(name);
   if(action.context==='visual')label.append(el('small','','In Write mode · keeps your text selection'));
   else if(action.editorKey)label.append(el('small','','While editing · '+action.plain.toUpperCase()+' also works outside text fields'));
   else if(action.context==='graph')label.append(el('small','','While the brain is focused'));
   else if(action.plain)label.append(el('small','','Outside text fields'));
   if(!action.key)label.append(el('small','','P → search this action → Enter'));
   button.append(label,el('kbd','',action.key||'P → Enter'));
   button.onclick=()=>{$('#shortcuts-dialog').close();action.run();};section.append(button);
  }catalog.append(section);
 }
 if(!actions.length)catalog.append(el('p','empty-list','No matching commands. Try “theme”, “note” or a key.'));
 catalog.scrollTop=0;
}
function openShortcuts(){
 const opened=$('dialog[open]');if(opened&&opened!==$('#command-dialog')&&opened!==$('#shortcuts-dialog'))return;
 $('#command-dialog').close();$('#shortcut-search').value='';renderShortcuts();
 showDialog('#shortcuts-dialog');$('#shortcut-search').focus({preventScroll:true});
}
$('#shortcut-search').oninput=renderShortcuts;
$('#shortcut-search').onkeydown=e=>{
 if(!NotrynKeyboard.available(e)||e.shiftKey)return;
 if(e.key==='Escape'){e.preventDefault();$('#shortcuts-dialog').close();return;}
 if(!['ArrowDown','ArrowUp','Enter'].includes(e.key))return;
 const rows=$$('#shortcut-catalog button');e.preventDefault();
 if(e.key==='Enter')rows[0]?.click();else rows[e.key==='ArrowDown'?0:rows.length-1]?.focus({preventScroll:true});
 if(e.key!=='Enter')document.activeElement.closest('.shortcut-command')?.scrollIntoView({block:'nearest'});
};
for(const event of ['mouseover','focusin'])document.addEventListener(event,e=>{const button=e.target.closest?.('button,input');if(button)updateControlHint(button);});
$('#open-shortcuts').onclick=openShortcuts;$('#open-shortcuts').title='Commands and shortcuts (?)';
let commandItems=[],commandIndex=0;
function renderCommands(){const q=clean($('#command-input').value.trim()),actions=actionItems().filter(a=>matchesCommand(a,q)),notes=(q?NotrynHierarchy.searchNotes(state.data,q):[...state.data.nodes].sort((a,b)=>b.updatedAt.localeCompare(a.updatedAt)).slice(0,5)).map(n=>({title:NotrynHierarchy.filename(n),detail:n.path+' · '+n.title,icon:'note',run:()=>openNote(n.id)}));const box=$('#commands');box.replaceChildren();commandItems=[];for(const[label,items]of[['Notes',notes],['Actions',actions]]){if(!items.length)continue;box.append(el('div','command-group-label',label));for(const item of items){const index=commandItems.length;commandItems.push(item);const b=el('button','command-row');b.setAttribute('role','option');b.dataset.index=index;b.append(icon(item.icon),el('span','',item.title));if(item.detail)b.append(el('small','',item.detail));if(item.key)b.append(el('kbd','',item.key));b.onclick=()=>runCommand(index);box.append(b);}}if(!commandItems.length)box.append(el('p','empty-list','No notes or actions match that name.'));commandIndex=0;highlightCommand();}
function highlightCommand(){const rows=$$('#commands .command-row');rows.forEach((b,i)=>b.setAttribute('aria-selected',String(i===commandIndex)));rows[commandIndex]?.scrollIntoView({block:'nearest'});}
function runCommand(i){const item=commandItems[i];if(!item)return;$('#command-dialog').close();item.run();}
function openCommand(){if($('dialog[open]')&& !$('#command-dialog').open)return;showDialog('#command-dialog');$('#command-input').value='';renderCommands();$('#command-input').focus();}
$('#open-command').onclick=openCommand;$('#command-input').oninput=renderCommands;$('#command-input').onkeydown=e=>{if(NotrynKeyboard.available(e)&&!e.shiftKey&&['ArrowDown','ArrowUp','Enter'].includes(e.key)){e.preventDefault();if(e.key==='Enter')runCommand(commandIndex);else{commandIndex=Math.max(0,Math.min(commandItems.length-1,commandIndex+(e.key==='ArrowDown'?1:-1)));highlightCommand();}}};$('.mod').textContent='P';
function updateKeyboardPreference(){
 $('#single-key-toggle').checked=singleKeys;
 $('#full-brain kbd').hidden=!singleKeys;
 document.documentElement.dataset.singleKeys=singleKeys?'on':'off';
 restGraphHint();
 $('.mod').textContent=singleKeys?'P':'Tab';
 $('#shortcut-mode-status').textContent=singleKeys?'Letters work outside text fields. While writing: Esc, then a command.':'Single-key shortcuts are off. Use Tab and Enter, the command palette or buttons.';
 refreshControlHints();
}
$('#single-key-toggle').onchange=e=>{singleKeys=e.target.checked;try{localStorage.setItem('notryn-single-keys',singleKeys?'on':'off');}catch{}updateKeyboardPreference();renderShortcuts();};
updateKeyboardPreference();
function updateInterfaceHints(){
 document.documentElement.dataset.interfaceHints=interfaceHints?'on':'off';
 $('#interface-hints-toggle').checked=interfaceHints;
 refreshControlHints();
}
function setInterfaceHints(enabled){
 interfaceHints=enabled;try{localStorage.setItem('notryn-interface-hints',enabled?'on':'off');}catch{}
 updateInterfaceHints();
 if($('#shortcuts-dialog').open)renderShortcuts();
}
$('#interface-hints-toggle').onchange=e=>setInterfaceHints(e.target.checked);
updateInterfaceHints();
function leaveTextField(){
 const active=document.activeElement;
 const target=active.closest('#document')?$(state.editing&&!state.saving?'#save-note':'#doc-close'):$('#open-command');
 target.focus({preventScroll:true});
 if($('#rich-editor').contains(active))window.getSelection()?.removeAllRanges();
 if(singleKeys&&interfaceHints)toast('H show/hide brain · Shift H full Brain · P commands · S save');
}
document.addEventListener('keydown',e=>{
 if(!NotrynKeyboard.available(e)||$('dialog[open]'))return;
 const active=document.activeElement,typing=['INPUT','TEXTAREA','SELECT'].includes(active.tagName)||active.isContentEditable;
 if(typing&&e.key==='Escape'&&!e.shiftKey){e.preventDefault();if(!e.repeat)leaveTextField();return;}
 const selected=!!window.getSelection()?.toString();
 const action=NotrynKeyboard.match(actionItems(),e,{typing,selected,graph:active===$('#graph'),enabled:singleKeys});
 if(!action)return;
 e.preventDefault();if(!e.repeat||action.repeat)action.run(e);
});
// Only the note pane claims these two editor commands. Other inputs, dialogs,
// browser shortcuts, uppercase letters and IME composition keep their behavior.
$('#document').addEventListener('keydown',e=>{
 if($('dialog[open]'))return;
 const action=NotrynKeyboard.matchEditor(actionItems(),e,{editing:state.editing&&writable()});
 if(!action)return;e.preventDefault();e.stopPropagation();if(!e.repeat)action.run();
},true);
window.addEventListener('beforeunload',e=>{if(state.dirty){e.preventDefault();e.returnValue='';}});

(async()=>{try{await loadBrains();const saved=localStorage.getItem('notryn-brain');state.brain=state.brains.some(b=>b.id===saved)?saved:state.brains[0]?.id||null;await loadGraph();if(current()&&localStorage.getItem('notryn-workspace')==='notes')setNotebookView(true,{focus:false,remember:false});}catch(e){toast(e.message);}})();
