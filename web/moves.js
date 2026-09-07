'use strict';
// File organization is shared by drag-and-drop, row menus and the command palette.
window.NotrynFiles=(()=>{
 let dragged=null,context=null,moving=false,returnKey=null;
 const tree=$('#file-tree'),root=$('#brain-root'),menu=$('#item-dialog'),dialog=$('#move-dialog');
 function itemFor(key){
  if(key?.startsWith('folder:')){const path=key.slice(7);return state.data.folders.includes(path)?{kind:'folder',path,key,brain:state.brain}:null;}
  const note=state.data.nodes.find(n=>n.id===key?.slice(5));return note?{kind:'note',path:note.path,key:'note:'+note.id,brain:state.brain}:null;
 }
 function currentItem(){
  const row=document.activeElement.closest('.file-entry')?.querySelector('.tree-row');
  if(row)return itemFor(row.dataset.key);
  if(document.activeElement.closest('#document')&&state.note&&!state.newNote)return {kind:'note',path:state.note.path,key:'note:'+state.selected};
  return itemFor(state.libraryKey)||itemFor('note:'+state.selected);
 }
 function restoreFocus(key=returnKey){const row=$$('#file-tree .tree-row').find(b=>b.dataset.key===key);(row||root).focus({preventScroll:true});}
 function canOrganize(){
  if(moving)return false;
  if(!writable()){toast('This Brain is read-only.');return false;}
  if(state.selected&&!state.note){toast('Wait for the note to finish opening, or close it before moving files.');return false;}
  if(state.saving){toast('Wait for your note to finish saving.');return false;}
  if(state.dirty){toast('Save your draft before moving files. Your writing is still here.');return false;}
  return true;
 }
 function validDestination(item,path){return item&&!(item.kind==='folder'&&(path===item.path||path.startsWith(item.path+'/')));}
 function parentOf(path){return path.split('/').slice(0,-1).join('/');}
 function destinationHere(){const item=currentItem();return item?.kind==='folder'?item.path:item?parentOf(item.path):'';}
 function menuFor(item){
  if(state.remotePreview||moving)return;
  context=item;returnKey=item?.key||null;
  $('#item-title').textContent=item?item.path.split('/').pop():'Brain root';
  $('#item-location').textContent=item?.path||current()?.name||'';
  $('#item-move').hidden=!item||!writable();$('#item-new-note').hidden=!writable()||item?.kind==='note';$('#item-new-folder').hidden=!writable()||item?.kind==='note';$('#item-remove').hidden=!item;
  showDialog('#item-dialog');$('#item-dialog .item-action:not([hidden])')?.focus();
 }
 $('#item-move').onclick=()=>{const item=context;menu.close();openMove(item);};
 for(const kind of ['note','folder'])$('#item-new-'+kind).onclick=()=>{const path=context?.kind==='folder'?context.path:'';menu.close();openCreate(kind,'',path);};
 menu.addEventListener('close',()=>{if(!dialog.open&&!$('#create-dialog').open)restoreFocus();});
 menu.addEventListener('keydown',e=>{
  if(!NotrynKeyboard.available(e)||e.shiftKey||!['ArrowUp','ArrowDown','Home','End'].includes(e.key))return;
  const rows=[...menu.querySelectorAll('.item-action:not([hidden])')],index=rows.indexOf(document.activeElement);
  e.preventDefault();rows[e.key==='Home'?0:e.key==='End'?rows.length-1:Math.max(0,Math.min(rows.length-1,index+(e.key==='ArrowDown'?1:-1)))]?.focus();
 });
 function openMove(item=currentItem()){
  if(!canOrganize())return;
  if(!item)return toast('Choose a note or folder in the library first.');
  context=item;returnKey=item.key;$('#move-item-name').textContent=item.path;$('#move-filter').value='';$('#move-error').hidden=true;
  renderDestinations();showDialog('#move-dialog');$('#move-filter').focus();
 }
 let destinations=[],destinationIndex=0;
 function renderDestinations(){
  const q=clean($('#move-filter').value),parent=parentOf(context.path);
  destinations=['',...state.data.folders].filter(path=>validDestination(context,path)&&path!==parent&&clean(path||'Brain root').includes(q));
  destinationIndex=0;const list=$('#move-destinations');list.replaceChildren();
  destinations.forEach((path,i)=>{
   const button=el('button','move-destination');button.type='button';button.id='move-destination-'+i;button.setAttribute('role','option');button.tabIndex=-1;
   button.append(icon('folder'),el('span','',path||'Brain root'));button.onclick=()=>move(context,path);list.append(button);
  });
  if(!destinations.length)list.append(el('p','empty-list','No other folders. Create a folder in the library first.'));
  highlightDestination();
 }
 function highlightDestination(){
  const rows=$$('#move-destinations button');rows.forEach((b,i)=>b.setAttribute('aria-selected',String(i===destinationIndex)));
  const selected=rows[destinationIndex];if(selected){$('#move-filter').setAttribute('aria-activedescendant',selected.id);selected.scrollIntoView({block:'nearest'});}else $('#move-filter').removeAttribute('aria-activedescendant');
  $('#move-submit').disabled=moving||!selected;
 }
 $('#move-filter').oninput=renderDestinations;
 $('#move-filter').onkeydown=e=>{
  if(!NotrynKeyboard.available(e)||e.shiftKey||!['ArrowUp','ArrowDown','Enter'].includes(e.key))return;
  e.preventDefault();if(e.key==='Enter'){if(destinations.length)move(context,destinations[destinationIndex]);return;}
  destinationIndex=Math.max(0,Math.min(destinations.length-1,destinationIndex+(e.key==='ArrowDown'?1:-1)));highlightDestination();
 };
 $('#move-submit').onclick=()=>{if(destinations.length)move(context,destinations[destinationIndex]);};
 dialog.addEventListener('close',()=>restoreFocus());
 dialog.addEventListener('cancel',e=>{if(moving)e.preventDefault();});
 async function move(item,destination){
  if(!canOrganize())return false;
  if(item.brain&&item.brain!==state.brain)return false;
  if(!validDestination(item,destination)){toast('A folder cannot be moved inside itself.');return false;}
  if(parentOf(item.path)===destination){toast('This item is already in that folder.');return false;}
  const brain=state.brain,opened=state.note?{...state.note}:null,wasEditing=state.editing,selectedPath=state.data.nodes.find(n=>n.id===state.selected)?.path;
  const workspace=$('.workspace'),header=$('.topbar'),nav=$('.mobile-nav');
  const busy=showDialog('#move-progress');busy.oncancel=e=>e.preventDefault();
  moving=true;workspace.inert=true;header.inert=true;nav.inert=true;
  let result;
  try{
   result=await api('/api/move',{brain,source:item.path,destination,kind:item.kind,guard:opened&&!state.newNote?{path:opened.path,revision:opened.revision}:null});
   const relocate=path=>path===item.path||item.kind==='folder'&&path.startsWith(item.path+'/')?result.path+path.slice(item.path.length):path;
   state.closed=new Set([...state.closed].map(relocate));state.folderPath=relocate(state.folderPath);let parent=destination;while(parent){state.closed.delete(parent);parent=parentOf(parent);}
   state.query='';state.group=null;state.recent=false;$('#search').value='';
   returnKey=item.kind+':'+(item.kind==='note'?result.path.slice(0,-3):result.path);state.libraryKey=returnKey;
   if(selectedPath)state.selected=relocate(selectedPath).slice(0,-3);
   if(opened)state.note={...opened,path:relocate(opened.path)};
   await loadGraph();
   if(opened){
    const serial=++state.noteSerial;
    const note=await api(endpoint('/api/note',{brain,path:relocate(opened.path)}));
    if(serial===state.noteSerial){state.note=note;state.editing=wasEditing;resetEditorView();renderDocument();graph.select(state.selected);}
   }
   renderLegend();renderTree();dialog.close();
   toast('Moved to '+(destination||'Brain root')+'.'+(result.updatedLinks?' Links updated.':''));return true;
  }catch(error){
   // A completed move must never be reported as a failed filesystem operation.
   const message=result?'Moved successfully. Refresh the library to reopen the note.':error.message;
   if(result&&opened){state.editing=false;$('#document-read').hidden=false;$('#editor-wrap').hidden=true;rich.setVisible(false);$('#document-read').replaceChildren(el('p','empty-list',message));$('#doc-folder').textContent=state.note.path;}
   if(dialog.open){$('#move-error').textContent=message;$('#move-error').hidden=false;}else toast(message);
   return false;
  }finally{moving=false;workspace.inert=false;header.inert=false;nav.inert=false;busy.close();restoreFocus();}
 }
 function clearDrag(){
  dragged=null;
  tree.classList.remove('is-dragging');document.body.classList.remove('file-dragging');$$('.drop-target,.drag-source').forEach(e=>e.classList.remove('drop-target','drag-source'));
  $('#library-drop-hint').hidden=true;
 }
 function dropZone(element,destination){
  const accept=e=>{
   if(!dragged||!validDestination(dragged,destination)||parentOf(dragged.path)===destination)return;
   e.preventDefault();e.stopPropagation();e.dataTransfer.dropEffect='move';
   $$('.drop-target').forEach(b=>{if(b!==element)b.classList.remove('drop-target');});element.classList.add('drop-target');
   $('#library-drop-hint').textContent='Move into '+(destination||'Brain root');$('#library-drop-hint').hidden=false;
  };
  element.addEventListener('dragenter',accept);element.addEventListener('dragover',accept);
  element.addEventListener('dragleave',e=>{if(!element.contains(e.relatedTarget)){element.classList.remove('drop-target');}});
  element.addEventListener('drop',e=>{
   if(!dragged)return;e.preventDefault();e.stopPropagation();const item=dragged;clearDrag();move(item,destination);
  });
 }
 function decorate(row){
  if(state.remotePreview||!current())return;
  const item=itemFor(row.dataset.key);if(!item)return;
  const entry=el('div','file-entry');row.replaceWith(entry);entry.append(row);
  const more=el('button','file-options','⋯');more.setAttribute('aria-label','Actions for '+item.path);more.setAttribute('aria-haspopup','dialog');more.title='Actions for '+item.path;more.tabIndex=row.tabIndex===0?0:-1;
  more.onclick=()=>menuFor(item);entry.append(more);
  entry.oncontextmenu=e=>{e.preventDefault();menuFor(item);};
  entry.addEventListener('focusin',()=>{state.libraryKey=item.key;$$('#file-tree .file-options').forEach(b=>b.tabIndex=b===more?0:-1);});
  row.draggable=writable();
  row.addEventListener('dragstart',e=>{
   if(!canOrganize()){e.preventDefault();return;}
   dragged={...item,brain:state.brain};e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('application/x-notryn-item',item.key);
   row.classList.add('drag-source');tree.classList.add('is-dragging');document.body.classList.add('file-dragging');$('#library-drop-hint').textContent='Drop on a folder or Brain root';$('#library-drop-hint').hidden=false;
  });
  row.addEventListener('dragend',clearDrag);
  if(item.kind==='folder')dropZone(entry,item.path);
 }
 tree.addEventListener('dragover',e=>{if(!dragged)return;const rect=tree.getBoundingClientRect();if(e.clientY<rect.top+36)tree.scrollTop-=10;else if(e.clientY>rect.bottom-36)tree.scrollTop+=10;});
 root.onclick=()=>menuFor(null);root.oncontextmenu=e=>{e.preventDefault();menuFor(null);};dropZone(root,'');
 document.addEventListener('drop',clearDrag);document.addEventListener('dragend',clearDrag);
 return {decorate,openMove,openMenu:()=>menuFor(currentItem()),destinationHere,currentItem,contextItem:()=>context};
})();
